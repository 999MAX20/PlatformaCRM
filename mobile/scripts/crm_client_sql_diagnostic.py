#!/usr/bin/env python3
"""Bounded test-only CRM diagnostics. Pure contracts are independently testable."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time

PROBES = ('plain-count', 'summary', 'annotated-distinct-count', 'vip-count')
CG_FILES = ('memory.current', 'memory.peak', 'memory.max', 'memory.events', 'cpu.stat')
STREAM_LIMIT = 2*1024*1024
PROTOCOL = 1

class DiagnosticError(RuntimeError):
    def __init__(self, code, message, **context):
        super().__init__(message)
        self.code, self.context = code, context

def error_record(error, phase):
    record = {'phase': phase, 'kind': type(error).__name__, 'code': getattr(error, 'code', 'UNEXPECTED'),
              'message': str(error)[:500], 'context': getattr(error, 'context', {})}
    record['sqlstate'] = getattr(error, 'sqlstate', None) or getattr(getattr(error, '__cause__', None), 'sqlstate', None)
    return record

class Budget:
    def __init__(self, seconds, clock=time.monotonic, end=None):
        self.clock = clock
        self.start = clock()
        self.end = min(self.start+seconds, end) if end is not None else self.start+seconds
    def remaining(self, maximum=None, reserve=0):
        value = self.end-self.clock()-reserve
        if value <= 0:
            raise DiagnosticError('DEADLINE', 'Shared diagnostic deadline exhausted')
        return min(maximum, value) if maximum is not None else value
    def millis(self, maximum):
        return max(1, int(self.remaining(maximum/1000, .1)*1000))

def admit(environ, project, source):
    run = environ.get('GITHUB_RUN_ID', '')
    if environ.get('GITHUB_ACTIONS') != 'true' or environ.get('GITHUB_REF') != 'refs/heads/codex/mobile-max':
        raise DiagnosticError('ADMISSION', 'Foreign CI branch or missing Actions admission')
    if not re.fullmatch('[0-9]+', run) or project != 'crm-test-'+run+'-queue-web':
        raise DiagnosticError('IDENTITY', 'Per-run project identity mismatch')
    if not re.fullmatch('[0-9a-f]{40}', source):
        raise DiagnosticError('IDENTITY', 'Missing immutable source SHA')
    return {'runId': run, 'project': project, 'sourceSha': source}

def integer(text, field):
    if not re.fullmatch('[0-9]+', text):
        raise DiagnosticError('CGROUP_VALUE', 'Expected unsigned ASCII integer', field=field, value=text[:120])
    return int(text)

def counters(text, field):
    result = {}
    for number, line in enumerate(text.splitlines(), 1):
        parts = line.split()
        if len(parts) != 2 or not re.fullmatch('[A-Za-z0-9_.-]+', parts[0]):
            raise DiagnosticError('CGROUP_ROW', 'Malformed counter row', field=field, line=number, value=line[:120])
        key, value = parts
        if key in result:
            raise DiagnosticError('CGROUP_DUPLICATE', 'Duplicate counter key', field=field, key=key)
        result[key] = integer(value, field+'.'+key)
    if not result:
        raise DiagnosticError('CGROUP_EMPTY', 'Empty counter file', field=field)
    return result

def parse_cgroup(stdout, stderr, code):
    if code or stderr.strip():
        raise DiagnosticError('CGROUP_TRANSPORT', 'Cgroup transport failed or emitted stderr', exitCode=code)
    if len(stdout.encode()) > 65536:
        raise DiagnosticError('OUTPUT_LIMIT', 'Cgroup frame oversized')
    lines = stdout.splitlines()
    if not lines or lines[0] != '__PROFILE__v2':
        raise DiagnosticError('CGROUP_PROFILE', 'Unsupported cgroup v1/hybrid/unknown profile; no v2 or OOM substitution')
    raw, index = {}, 1
    for name in CG_FILES:
        if index >= len(lines) or lines[index] != '__FILE__'+name:
            raise DiagnosticError('CGROUP_FRAME', 'Missing, duplicate or foreign file frame', field=name)
        index += 1
        body = []
        while index < len(lines) and not lines[index].startswith('__RC__'):
            body.append(lines[index]); index += 1
        if index >= len(lines) or lines[index] != '__RC__0':
            raise DiagnosticError('CGROUP_READ', 'File read failed or incomplete', field=name,
                                  result=lines[index] if index < len(lines) else 'MISSING_RC')
        index += 1
        value = '\n'.join(body).strip()
        if not value:
            raise DiagnosticError('CGROUP_EMPTY', 'Empty scalar/file', field=name)
        raw[name] = value
    if index != len(lines):
        raise DiagnosticError('CGROUP_FRAME', 'Unexpected cgroup output after final frame')
    values = {name: integer(raw[name], name) for name in ('memory.current', 'memory.peak')}
    values['memory.max'] = None if raw['memory.max'] == 'max' else integer(raw['memory.max'], 'memory.max')
    values['memory.events'] = counters(raw['memory.events'], 'memory.events')
    values['cpu.stat'] = counters(raw['cpu.stat'], 'cpu.stat')
    if not {'oom', 'oom_kill'} <= values['memory.events'].keys() or not {'usage_usec', 'user_usec', 'system_usec'} <= values['cpu.stat'].keys():
        raise DiagnosticError('CGROUP_REQUIRED', 'Required observation counters absent')
    return {'profile': 'v2', 'units': 'bytes and microseconds', 'values': values}

def verify_memory(snapshot, expected):
    if snapshot['values']['memory.max'] != expected:
        raise DiagnosticError('CGROUP_LIMIT', 'Effective container memory limit differs from unchanged Compose limit')

def memory_delta(before, after):
    result = {}
    for key, value in before['values']['memory.events'].items():
        current = after['values']['memory.events'].get(key)
        if current is None or current < value:
            raise DiagnosticError('CGROUP_RESET', 'Counter disappeared or reset; delta unknown', key=key)
        result[key] = current-value
    if result.get('oom_kill', 0) or result.get('oom', 0):
        raise DiagnosticError('CGROUP_OOM', 'New OOM event during diagnostic', events=result)
    return result

def validate_sql(data, identity, require_pass=False):
    if not isinstance(data, dict) or data.get('protocol') != PROTOCOL or data.get('identity') != identity:
        raise DiagnosticError('SQL_PROTOCOL', 'Foreign/missing SQL envelope identity')
    rows = data.get('probes', [])
    if len(rows) != 4 or [r.get('name') for r in rows] != list(PROBES):
        raise DiagnosticError('SQL_REGISTRY', 'Expected exact ordered four-probe registry')
    if data.get('readOnlyRequested') is not True or data.get('explainAnalyze') is not False:
        raise DiagnosticError('SQL_GUARD', 'SQL safety envelope mismatch')
    for row in rows:
        count = row.get('executionCount')
        if type(count) is not int or count not in (0, 1) or row.get('status') not in ('PASS','FAIL','BLOCKED','NOT_RUN'):
            raise DiagnosticError('SQL_EXECUTION', 'Invalid SQL status/execution count', probe=row.get('name'))
        if row['status'] == 'PASS':
            values = row.get('result')
            width = 4 if row['name'] == 'summary' else 1
            if count != 1 or row.get('readOnlyVerified') is not True or type(row.get('statementMs')) is not int or not 0<row['statementMs']<=5000 or type(row.get('lockMs')) is not int or not 0<row['lockMs']<=1000:
                raise DiagnosticError('SQL_GUARD', 'PASS without executed read-only bounded query', probe=row['name'])
            if not isinstance(values,list) or len(values)!=width or any(type(v) is not int or v<0 for v in values):
                raise DiagnosticError('SQL_VALUE', 'Invalid count/aggregate result', probe=row['name'])
            if not re.fullmatch('[0-9a-f]{64}',row.get('sqlSha256','')):
                raise DiagnosticError('SQL_HASH', 'Missing exact SQL fingerprint')
    passed = data.get('status') == 'PASS' and all(r['status']=='PASS' for r in rows) and not data.get('observationErrors') and data.get('observerStopped') is True
    if data.get('status') not in ('PASS','FAIL','BLOCKED','NOT_RUN'):
        raise DiagnosticError('SQL_PROTOCOL','Unknown SQL envelope status')
    if data.get('status')=='PASS' and not passed:
        raise DiagnosticError('SQL_FALSE_PASS', 'PASS envelope has incomplete mandatory evidence')
    if require_pass and not passed:
        raise DiagnosticError('SQL_BLOCKED', 'Required SQL probes/observation did not pass')
    return passed

def validate_host_report(data,identity):
    if not isinstance(data,dict) or data.get('protocol')!=PROTOCOL or data.get('identity')!=identity or data.get('status') not in ('PASS','FAIL','BLOCKED','NOT_RUN'):
        raise DiagnosticError('HOST_PROTOCOL','Foreign/malformed host result')
    if data['status']!='PASS':return False
    if not validate_sql(data.get('sql'),identity):raise DiagnosticError('HOST_FALSE_PASS','Host PASS without SQL PASS')
    cg=data.get('cgroup',{})
    for phase in ('before','after'):
        if set(cg.get(phase,{}))!={'web','db'}:raise DiagnosticError('HOST_CGROUP','Mandatory service snapshots absent')
        for service,limit in [('web',805306368),('db',536870912)]:
            record=cg[phase][service]
            if record.get('status')!='PASS':raise DiagnosticError('HOST_CGROUP','Incomplete snapshot')
            verify_memory(record['parsed'],limit)
    for service in ('web','db'):memory_delta(cg['before'][service]['parsed'],cg['after'][service]['parsed'])
    return True

def parse_sql_frame(stdout, stderr, code, identity):
    if len(stdout.encode())>STREAM_LIMIT or len(stderr.encode())>STREAM_LIMIT:
        raise DiagnosticError('OUTPUT_LIMIT','SQL output oversized')
    rows=[]
    for line in stdout.splitlines():
        if line.startswith('SQL_RESULT '): rows.append(line[len('SQL_RESULT '):])
        elif line.strip() and not re.fullmatch(r'[0-9]+ objects imported automatically.*',line):
            raise DiagnosticError('SQL_NOISE','Unknown stdout outside SQL frame', line=line[:120])
    if code or stderr.strip() or len(rows)!=1:
        raise DiagnosticError('SQL_FRAME','Nonzero exit,stderr,missing or duplicate SQL frame',exitCode=code,frames=len(rows))
    try:data=json.loads(rows[0])
    except (ValueError,TypeError) as e:raise DiagnosticError('SQL_JSON','Malformed SQL result') from e
    validate_sql(data,identity)
    return data

CG_SCRIPT = 'printf "__PROFILE__"; if test -f /sys/fs/cgroup/cgroup.controllers; then printf "v2\\n"; else printf "unsupported\\n"; fi; '+ '; '.join(
    'printf "__FILE__'+name+'\\n"; cat /sys/fs/cgroup/'+name+' 2>&1; rc=$?; printf "\\n__RC__%s\\n" "$rc"' for name in CG_FILES)

def stop_owned_group(process, end, clock=time.monotonic):
    """Only for a child created with start_new_session=True, including its descendants."""
    def send(sig):
        try:os.killpg(process.pid,sig);return True
        except ProcessLookupError:return False
    # A reaped parent alone does not prove npm/preview descendants stopped.
    if send(signal.SIGTERM):
        while clock()<end-.25:
            process.poll()
            if not send(0):break
            time.sleep(min(.02,max(.001,end-.25-clock())))
        else:send(signal.SIGKILL)
    process.wait(timeout=max(.01,min(.2,end-clock())))
    if send(0):
        send(signal.SIGKILL)
        raise DiagnosticError('CHILD_GROUP','Owned process group shutdown remains unconfirmed')

def capture_process(args, env, cwd, directory, label, budget, maximum):
    """Bound both streams on owned disk; stop/wait only this child group."""
    end=min(budget.end, budget.clock()+maximum)
    work_end=end-1
    paths=[directory/(label+'.stdout'),directory/(label+'.stderr')]
    process=None
    reason=None
    with paths[0].open('wb') as out, paths[1].open('wb') as err:
        try:
            process=subprocess.Popen(args,cwd=cwd,env=env,stdout=out,stderr=err,start_new_session=True)
            while process.poll() is None:
                if any(p.stat().st_size>STREAM_LIMIT for p in paths):
                    raise DiagnosticError('OUTPUT_LIMIT','Child stream limit reached',phase=label)
                if budget.clock()>=work_end:raise DiagnosticError('DEADLINE','Child or parent deadline',phase=label)
                time.sleep(min(.02,max(.001,work_end-budget.clock())))
        except BaseException as e:
            reason=e
        finally:
            if process:
                try:stop_owned_group(process,end,budget.clock)
                except Exception as e:reason=e
    if budget.clock()>end:reason=DiagnosticError('DEADLINE','Child startup/completion exceeded phase allocation',phase=label)
    record={'exitCode':None if process is None else process.returncode,'streams':{}}
    for name,path in zip(('stdout','stderr'),paths):
        raw=path.read_bytes()
        record['streams'][name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        if len(raw)>STREAM_LIMIT:reason=DiagnosticError('OUTPUT_LIMIT','Child stream oversized',phase=label)
        try:record[name]=raw[:STREAM_LIMIT].decode('utf-8','strict')
        except UnicodeError:record[name]='';reason=DiagnosticError('ENCODING','Invalid UTF8 in child stream',phase=label)
    if reason:record['error']=error_record(reason,label)
    return record

class DjangoAdapter:
    """The actual existing ORM path; imports never occur during pure self-checks."""
    def __init__(self):
        from django.db import connection,transaction
        self.connection,self.transaction=connection,transaction
        self.stop=threading.Event();self.ready=threading.Event();self.lock=threading.Lock()
        self.errors=[];self.samples=[];self.active=None;self.thread=None
    def readonly(self,cursor,budget,maximum):
        cursor.execute('SET TRANSACTION READ ONLY')
        limits=(budget.millis(maximum),budget.millis(1000))
        cursor.execute("SELECT set_config('statement_timeout',%s,true),set_config('lock_timeout',%s,true)",[str(v) for v in limits])
        cursor.execute('SHOW transaction_read_only')
        if cursor.fetchone()[0]!='on':raise DiagnosticError('READ_ONLY','Read-only transaction not confirmed')
        return limits
    def prepare(self,budget):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIRequestFactory,force_authenticate
        from apps.clients.views import ClientViewSet
        from apps.clients.selectors import build_client_summary
        from apps.core.viewsets import TenantModelViewSet
        self.connection.settings_dict['OPTIONS']={**self.connection.settings_dict.get('OPTIONS',{}),'connect_timeout':2}
        with self.transaction.atomic():
            with self.connection.cursor() as c:
                self.readonly(c,budget,2000)
                c.execute("SELECT current_setting('jit'),current_setting('jit_above_cost'),current_setting('jit_inline_above_cost'),current_setting('jit_optimize_above_cost')")
                self.settings=list(c.fetchone())
            owner=get_user_model().objects.get(email='business_owner@example.com')
            raw=APIRequestFactory().get('/api/clients/');force_authenticate(raw,user=owner)
            view=ClientViewSet();view.args,view.kwargs,view.action_map=(),{},{'get':'list'}
            view.request=view.initialize_request(raw);view.format_kwarg=None;view.check_permissions(view.request)
            plain=view.filter_queryset(TenantModelViewSet.get_queryset(view))
            annotated=view.filter_queryset(view.get_queryset(apply_quick_filter=False))
        self.operations=dict(zip(PROBES,[lambda:plain.all().count(),lambda:build_client_summary(annotated.all()),lambda:annotated.all().count(),lambda:annotated.filter(is_vip=True).count()]))
        self.thread=threading.Thread(target=self.observe,args=(budget,),daemon=True);self.thread.start()
        if not self.ready.wait(timeout=budget.remaining(1)) or self.errors:raise DiagnosticError('OBSERVER_START','Observer admission unavailable')
    def observe(self,budget):
        db=None;seen=set()
        try:
            from django.db.backends.postgresql.base import DatabaseWrapper
            db=DatabaseWrapper(self.connection.settings_dict.copy(),alias='bounded-sql-observer')
            with db.cursor() as c:
                c.execute('SET default_transaction_read_only=on');c.execute("SET statement_timeout='500ms'");c.execute("SET lock_timeout='500ms'");self.ready.set()
                while not self.stop.is_set() and budget.clock()<budget.end:
                    with self.lock:active=self.active
                    if active:
                        name,pid,started=active
                        slots=[s for s in (0,1,3) if budget.clock()-started>=s and (name,s) not in seen]
                        if slots:
                            slot=slots[-1];seen.update((name,s) for s in slots)
                            c.execute('SELECT state,wait_event_type,wait_event,pg_blocking_pids(pid),EXTRACT(EPOCH FROM clock_timestamp()-query_start) FROM pg_stat_activity WHERE pid=%s',[pid]);row=c.fetchone()
                            c.execute('SELECT locktype,mode,granted FROM pg_locks WHERE pid=%s ORDER BY locktype,mode,granted LIMIT 100',[pid]);locks=c.fetchall()
                            with self.lock:completed=self.active!=active
                            self.samples.append({'probe':name,'pid':pid,'scheduledSeconds':slot,'observedAt':budget.clock(),'observedAfterProbeCompleted':completed,'state':None if row is None else row[0],'waitType':None if row is None else row[1],'waitEvent':None if row is None else row[2],'blockingPids':None if row is None else row[3],'queryAgeSeconds':None if row is None else str(row[4]),'locks':[list(value) for value in locks]})
                    self.stop.wait(.05)
        except Exception as e:self.errors.append(error_record(e,'observer'))
        finally:
            self.ready.set()
            if db:
                try:db.close()
                except Exception as e:self.errors.append(error_record(e,'observer-close'))
    def capture(self,name):
        class Captured(Exception):pass
        result=[]
        def wrapper(execute,sql,params,many,context):
            if many or not sql.lstrip().upper().startswith('SELECT '):raise DiagnosticError('SQL_CAPTURE','Only one SELECT accepted')
            result.append((sql,params));raise Captured()
        try:
            with self.connection.execute_wrapper(wrapper):self.operations[name]()
        except Captured:pass
        if len(result)!=1:raise DiagnosticError('SQL_CAPTURE','No uncached SQL captured')
        return result[0]
    def probe(self,name,sql,params,budget,row):
        with self.transaction.atomic():
            row['transactionEntered']=True
            try:
                with self.connection.cursor() as c:
                    self.readonly(c,budget,2000)
                    c.execute('EXPLAIN (FORMAT JSON) '+sql,params);plan=c.fetchone()[0]
                    if len(json.dumps(plan).encode())>524288:raise DiagnosticError('OUTPUT_LIMIT','Plan evidence limit')
                    row['plan']=plan
                    statement,lock=self.readonly_limits(c,budget)
                    c.execute('SELECT pg_backend_pid()');pid=c.fetchone()[0]
                    row.update(readOnlyVerified=True,statementMs=statement,lockMs=lock,pid=pid,executionCount=1)
                    with self.lock:self.active=(name,pid,budget.clock())
                    try:
                        started=budget.clock();c.execute(sql,params);values=c.fetchall()
                        if len(values)!=1:raise DiagnosticError('SQL_VALUE','Expected single count row')
                        row['result']=list(values[0]);row['executionSeconds']=budget.clock()-started
                    finally:
                        with self.lock:self.active=None
            except BaseException:
                row['rollbackRequired']=True
                raise
        row['transactionCompleted']=True
    def readonly_limits(self,c,budget):
        statement,lock=budget.millis(5000),budget.millis(1000)
        c.execute("SELECT set_config('statement_timeout',%s,true),set_config('lock_timeout',%s,true)",[str(statement),str(lock)])
        return statement,lock
    def close(self,budget):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=budget.remaining(.8))
            if self.thread.is_alive():self.errors.append({'code':'OBSERVER_STOP','phase':'observer-close'})
        return self.errors,self.samples

def sql_sequence(identity,budget,adapter_factory=DjangoAdapter):
    report={'protocol':PROTOCOL,'identity':identity,'status':'BLOCKED','readOnlyRequested':True,'explainAnalyze':False,
            'probes':[{'name':name,'status':'NOT_RUN','executionCount':0} for name in PROBES],
            'observationErrors':[],'observerStopped':False}
    adapter=None
    try:
        adapter=adapter_factory();adapter.prepare(budget)
        for row in report['probes']:
            try:
                budget.remaining(1,reserve=1)
                sql,params=adapter.capture(row['name']);row['sqlSha256']=hashlib.sha256(sql.encode()).hexdigest()
                row['status']='FAIL';adapter.probe(row['name'],sql,params,budget,row);row['status']='PASS'
                # Validate typed probe before allowing a claimed PASS to survive.
                check={**report,'status':'FAIL','observerStopped':True}
                validate_sql(check,identity)
            except Exception as e:
                row['status']='NOT_RUN' if row['executionCount']==0 and getattr(e,'code',None)=='DEADLINE' else 'FAIL'
                row['error']=error_record(e,'probe-'+row['name'])
        report['status']='PASS' if all(r['status']=='PASS' for r in report['probes']) else 'FAIL'
    except Exception as e:report['error']=error_record(e,'sql-startup')
    finally:
        if adapter:
            try:
                report['observationErrors'],report['activitySamples']=adapter.close(budget)
                report['observerStopped']=not report['observationErrors']
                report['observationCoverage']=[{'probe':row['name'],'samples':sum(sample.get('probe')==row['name'] for sample in report['activitySamples']),
                    'status':'SAMPLED' if any(sample.get('probe')==row['name'] for sample in report['activitySamples']) else 'NO_SAMPLE_NOT_PROOF_OF_NO_WAIT'} for row in report['probes'] if row['executionCount']==1]
            except Exception as e:report['observationErrors'].append(error_record(e,'sql-close'))
        if report['status']=='PASS' and (not report['observerStopped'] or report['observationErrors']):report['status']='BLOCKED'
        try:budget.remaining()
        except DiagnosticError:report['status']='BLOCKED'
        report['elapsedSeconds']=budget.clock()-budget.start
    try:validate_sql(report,identity)
    except DiagnosticError as e:report['status']='BLOCKED';report['protocolError']=error_record(e,'sql-final')
    return report

def inside(identity,seconds):
    report=sql_sequence(identity,Budget(min(seconds,36)))
    print('SQL_RESULT '+json.dumps(report,default=str),flush=True)


def host(project,source,output):
    budget=Budget(55);identity={'runId':os.environ.get('GITHUB_RUN_ID',''),'project':project,'sourceSha':source}
    report={'protocol':PROTOCOL,'identity':identity,'status':'BLOCKED','cgroup':{},'sql':None}
    output.parent.mkdir(parents=True,exist_ok=True)
    evidence=output.parent/'sql-io';evidence.mkdir(exist_ok=False)
    compose=['docker','compose','--project-name',project,'-f','docker-compose.yml','-f','mobile/ci/crm-test-stack.compose.yml','--env-file',str(Path.cwd()/'.env')]
    def invoke(args,label,maximum):
        record=capture_process(args,dict(os.environ),Path.cwd(),evidence,label,budget,maximum)
        report.setdefault('io',{})[label]=record
        if record.get('error'):raise DiagnosticError('CHILD_IO','Child transport incomplete',phase=label,error=record['error'])
        return record
    def memory(label):
        report['cgroup'][label]={}
        for service,limit in [('web',805306368),('db',536870912)]:
            raw=invoke(compose+['exec','-T',service,'sh','-c',CG_SCRIPT],label+'-'+service,3)
            record={'raw':raw,'status':'BLOCKED'};report['cgroup'][label][service]=record
            parsed=parse_cgroup(raw['stdout'],raw['stderr'],raw['exitCode']);record['parsed']=parsed;verify_memory(parsed,limit);record['status']='PASS'
    try:
        identity=admit(os.environ,project,source);report['identity']=identity
        memory('before')
        seconds=min(36,budget.remaining(40,reserve=8)-2)
        if seconds<=0:raise DiagnosticError('DEADLINE','No SQL allocation remains')
        code="import json,runpy;runpy.run_path('mobile/scripts/crm_client_sql_diagnostic.py')['inside'](json.loads("+repr(json.dumps(identity))+"),"+repr(seconds)+")"
        raw=invoke(compose+['exec','-T','web','python','manage.py','shell','-c',code],'sql-inner',min(40,budget.remaining(reserve=7)))
        report['sql']=parse_sql_frame(raw['stdout'],raw['stderr'],raw['exitCode'],identity)
        memory('after')
        for service in ('web','db'):
            report['cgroup']['after'][service]['eventsDelta']=memory_delta(report['cgroup']['before'][service]['parsed'],report['cgroup']['after'][service]['parsed'])
        report['status']='PASS' if validate_sql(report['sql'],identity) else 'FAIL'
    except Exception as e:report['error']=error_record(e,'host')
    finally:
        report['elapsedSeconds']=budget.clock()-budget.start
        if report['elapsedSeconds']>55:report['status']='BLOCKED';report['error']={'code':'DEADLINE','phase':'host'}
        output.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps(report,default=str),flush=True)
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--project',required=True);parser.add_argument('--source-sha',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();raise SystemExit(host(args.project,args.source_sha,args.output))
