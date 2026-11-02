"""Offline contract checks: real Docker/DB/browser/network dispatch is forbidden."""
import ast
import base64
import copy
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
REPO_ROOT=Path(os.environ.get('CRM_HARNESS_SOURCE_ROOT',str(HERE.parents[1])))
sys.path[:0]=[str(HERE),str(REPO_ROOT/'mobile/scripts')]
import crm_client_sql_diagnostic as q
import run_crm_followup_diagnostic as r
TEST_SPEC=HERE/'auth-leads-diagnostic.spec.ts'
if not TEST_SPEC.exists():TEST_SPEC=REPO_ROOT/'frontend/e2e/auth-leads-diagnostic.spec.ts'

IDENTITY={'sourceSha':'a'*40,'runId':'123','project':'crm-test-123-queue-web'}
ENV={'GITHUB_ACTIONS':'true','GITHUB_REF':'refs/heads/codex/mobile-max','GITHUB_RUN_ID':'123'}
NAMES=('plain-count','summary','annotated-distinct-count','vip-count')
TITLES=('API cookie baseline: rotate refresh, me and seeded leads','Product UI login preserves session across hard navigation and reload','Existing smoke helper preserves session across hard navigation and reload','Seed to owner API to lead DOM visibility')
VALUES={'memory.current':'1024','memory.peak':'2048','memory.max':'805306368','memory.events':'low 0\nhigh 0\nmax 0\noom 0\noom_kill 0','cpu.stat':'usage_usec 10\nuser_usec 6\nsystem_usec 4'}

def cg(values=None,profile='v2',order=None):
    v={**VALUES,**(values or {})};lines=['__PROFILE__'+profile]
    for name in order or tuple(VALUES):lines+=['__FILE__'+name,v[name],'__RC__0']
    return '\n'.join(lines)+'\n'

def sql_report():
    return {'protocol':1,'identity':IDENTITY.copy(),'status':'PASS','readOnlyRequested':True,'explainAnalyze':False,'observerStopped':True,'observationErrors':[],
      'probes':[{'name':name,'status':'PASS','executionCount':1,'readOnlyVerified':True,'statementMs':5000,'lockMs':1000,'result':[2,1,0,0] if name=='summary' else [2],'sqlSha256':'b'*64} for name in NAMES]}

def browser(collection=False):
    config={'projects':[{'name':'bounded-desktop-diagnostic','testMatch':['auth-leads-diagnostic.spec.ts'],'repeatEach':1,'retries':0,'timeout':45000}],'workers':1,'fullyParallel':False,'forbidOnly':True,'globalTimeout':300000,'maxFailures':0,'shard':None}
    return {'config':config,'errors':[],'suites':[{'specs':[{'title':name,'file':'auth-leads-diagnostic.spec.ts','tests':[{'projectName':'bounded-desktop-diagnostic','expectedStatus':'passed','annotations':[],'results':[] if collection else [{'status':'passed'}]}]} for name in TITLES]}]}

class Clock:
    def __init__(self):self.now=0.
    def __call__(self):return self.now
    def advance(self,amount):self.now+=amount

class FakeAdapter:
    def __init__(self,fail=None,clock=None):self.fail=fail;self.calls=[];self.clock=clock;self.closed=False
    def prepare(self,budget):
        if self.fail=='startup':raise q.DiagnosticError('IMPORT','synthetic startup')
    def capture(self,name):
        self.calls.append(('capture',name))
        if self.fail=='capture':raise q.DiagnosticError('SQL_CAPTURE','no capture')
        return 'SELECT COUNT(*) FROM synthetic_scope',()
    def probe(self,name,sql,params,budget,row):
        self.calls.append(('execute',name));row.update(executionCount=1,readOnlyVerified=True,statementMs=budget.millis(5000),lockMs=budget.millis(1000))
        if self.fail==name:
            row['rollbackRequired']=True
            e=RuntimeError('synthetic cancel');e.sqlstate='57014';raise e
        row['result']=[2,1,0,0] if name=='summary' else [2]
        if self.clock:self.clock.advance(.1)
    def close(self,budget):
        self.closed=True
        if self.fail=='close':raise q.DiagnosticError('OBSERVER_CLOSE','synthetic close')
        return [],[{'probe':'plain-count','pid':11,'waitType':None,'observedAt':0.}]

class FakeCursor:
    def __init__(self,readonly='on'):self.commands=[];self.readonly=readonly
    def execute(self,sql,params=None):self.commands.append((sql,params))
    def fetchone(self):return [self.readonly]

class FakeDatabase:
    def __init__(self,fail=None):self.fail=fail;self.commands=[];self.transactions=[];self.wrapper=None
    @contextmanager
    def atomic(self):
        self.transactions.append('begin')
        try:yield
        except BaseException:self.transactions.append('rollback');raise
        else:self.transactions.append('commit')
    @contextmanager
    def cursor(self):
        database=self
        class Cursor:
            def execute(self,sql,params=None):
                self.last=sql;database.commands.append((sql,params))
                if database.fail and sql.startswith(database.fail):
                    error=RuntimeError('synthetic database timeout');error.sqlstate='57014';raise error
            def fetchone(self):
                if self.last.startswith('SHOW'):return ['on']
                if self.last.startswith('EXPLAIN'):return [[{'Plan':{'Node Type':'Aggregate'}}]]
                if self.last.startswith('SELECT pg_backend_pid'):return [77]
                if 'pg_stat_activity' in self.last:return ['active','Lock','relation',[78],1]
                return [2]
            def fetchall(self):return [('relation','AccessShareLock',True)] if 'pg_locks' in self.last else [(2,)]
        yield Cursor()
    @contextmanager
    def execute_wrapper(self,wrapper):
        self.wrapper=wrapper
        try:yield
        finally:self.wrapper=None
    def close(self):pass

def real_adapter(fail=None):
    database=FakeDatabase(fail);adapter=q.DjangoAdapter.__new__(q.DjangoAdapter)
    adapter.connection=database;adapter.transaction=SimpleNamespace(atomic=database.atomic)
    adapter.lock=threading.Lock();adapter.active=None
    return adapter,database

class HarnessChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='crm-harness-offline-')
        self.directory=Path(self.temp.name)
        self.blockers=[patch('subprocess.Popen',side_effect=AssertionError('REAL PROCESS DISPATCH FORBIDDEN')),
          patch('subprocess.run',side_effect=AssertionError('REAL COMMAND FORBIDDEN')),
          patch('socket.create_connection',side_effect=AssertionError('REAL NETWORK FORBIDDEN'))]
        for p in self.blockers:p.start()
    def tearDown(self):
        for p in reversed(self.blockers):p.stop()
        self.temp.cleanup()
    def bad(self,fn,*args,**kwargs):
        with self.assertRaises((q.DiagnosticError,r.Blocked,ValueError,TypeError,KeyError)):fn(*args,**kwargs)
    def capture(self,content=b'hello',running=False,ignore_term=False,maximum=3):
        clock=Clock();events=[];alive=[running]
        class Process:
            pid=876543
            def __init__(self,*args,**kw):self.returncode=None if running else 0;kw['stdout'].write(content);kw['stdout'].flush()
            def poll(self):return self.returncode
            def wait(self,timeout):
                if self.returncode is None:raise subprocess.TimeoutExpired('fake',timeout)
                return self.returncode
        box=[]
        def factory(*a,**k):p=Process(*a,**k);box.append(p);return p
        def kill(pid,sig):
            self.assertEqual(pid,876543)
            if not alive[0]:raise ProcessLookupError()
            if sig==0:return
            events.append(sig)
            if not ignore_term or sig==q.signal.SIGKILL:box[0].returncode=-sig;alive[0]=False
        with patch.object(q.subprocess,'Popen',side_effect=factory),patch.object(q.time,'sleep',side_effect=clock.advance),patch.object(q.os,'killpg',side_effect=kill):
            value=q.capture_process(['FAKE'],{},self.directory,self.directory,'child',q.Budget(maximum,clock),maximum)
        return value,events,clock.now
    def resource(self,responses,free=None,cap=2048):
        clock=Clock();obj=r.StackBudget.__new__(r.StackBudget)
        obj.output=self.directory;obj.roots=[self.directory];obj.deadline=10;obj.storage_baseline=None;obj.charged_high_water=0;obj.artifact_cap=cap;obj.report={};obj.emit=lambda *a,**k:None
        with patch.object(r.time,'monotonic',clock),patch.object(r.time,'sleep',side_effect=clock.advance),patch.object(r.subprocess,'run',side_effect=responses) as command,patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=r.RESERVE+4096 if free is None else free)):
            result=obj.capacity()
        return result,command.call_count,clock.now
    def du(self,code=0,error='',size='1'):
        return SimpleNamespace(returncode=code,stderr=error,stdout=size+'\t'+str(self.directory)+'\n')
    def family(self,group,index):
        if group=='admission_environment':
            if index==1:self.assertEqual(q.admit(ENV,IDENTITY['project'],IDENTITY['sourceSha']),IDENTITY)
            elif index==2:
                for key in ENV:self.bad(q.admit,{k:v for k,v in ENV.items() if k!=key},IDENTITY['project'],IDENTITY['sourceSha'])
            elif index==3:self.bad(q.admit,{**ENV,'GITHUB_REF':'refs/heads/main'},IDENTITY['project'],IDENTITY['sourceSha'])
            elif index==4:
                for value in ('','bad','١٢٣'):self.bad(q.admit,{**ENV,'GITHUB_RUN_ID':value},IDENTITY['project'],IDENTITY['sourceSha'])
            elif index==5:self.bad(q.admit,ENV,'crm-test-999-queue-web',IDENTITY['sourceSha'])
            elif index==6:
                for sha in ('','a'*39,'z'*40):self.bad(q.admit,ENV,IDENTITY['project'],sha)
                self.assertIn('Immutable clean checkout required',(HERE/'run_crm_followup_diagnostic.py').read_text())
            elif index==7:
                fields=r.public_ci_environment({**ENV,'GITHUB_TOKEN':'SECRET','ACTIONS_RUNTIME_TOKEN':'SECRET'},'queue-web')
                self.assertEqual(set(fields),set(ENV));self.assertNotIn('SECRET',json.dumps(fields))
            elif index==8:self.bad(r.public_ci_environment,ENV,'backend-targeted');self.bad(q.admit,{**ENV,'GITHUB_ACTIONS':'false'},IDENTITY['project'],IDENTITY['sourceSha'])
            else:self.fail('unimplemented')
        elif group=='cgroup_transport_and_schema':
            if index==1:self.assertEqual(q.parse_cgroup(cg(),' ',0)['values']['memory.current'],1024)
            elif index==2:
                data=q.parse_cgroup(cg({'cpu.stat':'system_usec 4\ncore_sched.force_idle_usec 0\nuser_usec 6\nusage_usec 10'}),'',0);self.assertEqual(data['values']['cpu.stat']['core_sched.force_idle_usec'],0)
            elif index==3:
                for value in ('','abc','-1','1.5'):self.bad(q.parse_cgroup,cg({'memory.current':value}),'',0)
            elif index==4:
                self.assertIsNone(q.parse_cgroup(cg({'memory.max':'max'}),'',0)['values']['memory.max'])
                self.bad(q.parse_cgroup,cg({'memory.events':'oom max\noom_kill 0'}),'',0)
                self.assertEqual(q.parse_cgroup(cg(),' ',0)['values']['memory.events']['max'],0)
            elif index==5:self.bad(q.parse_cgroup,cg().replace('__FILE__memory.peak','__FILE__missing.peak'),'',0)
            elif index==6:
                self.bad(q.parse_cgroup,cg().replace('__RC__0','__RC__13',1),'',0);self.bad(q.parse_cgroup,cg(),'permission denied',1)
            elif index==7:self.bad(q.parse_cgroup,cg({'cpu.stat':VALUES['cpu.stat']+'\nusage_usec 12'}),'',0)
            elif index==8:
                self.bad(q.parse_cgroup,'noise\n'+cg(),'',0);self.bad(q.parse_cgroup,cg()+'trailer\n','',0)
            elif index==9:
                self.bad(q.parse_cgroup,cg()[:-10],'',0);self.bad(q.parse_cgroup,cg()+'x'*65536,'',0)
            elif index==10:
                for profile in ('v1','hybrid','unsupported'):self.bad(q.parse_cgroup,cg(profile=profile),'',0)
            elif index==11:
                before=q.parse_cgroup(cg(),' ',0);after=q.parse_cgroup(cg({'memory.events':'oom 1\noom_kill 1'}),'',0);self.bad(q.memory_delta,before,after)
                before['values']['memory.events']['oom_kill']=2;self.bad(q.memory_delta,before,q.parse_cgroup(cg(),' ',0))
            elif index==12:
                self.bad(q.verify_memory,q.parse_cgroup(cg({'memory.max':'max'}),'',0),805306368)
                self.bad(r.owned_container_states,[{'Id':'a'*64,'Config':{'Labels':{'com.docker.compose.project':'foreign'}},'State':{'Running':True}}],IDENTITY['project'])
            else:self.fail('unimplemented')
        elif group=='sql_orchestration_observer':
            if index==1:
                result=q.sql_sequence(IDENTITY,q.Budget(36),lambda:FakeAdapter('startup'));self.assertEqual(result['status'],'BLOCKED');self.assertTrue(all(p['executionCount']==0 for p in result['probes']))
            elif index==2:
                text=(HERE/'crm_client_sql_diagnostic.py').read_text();self.assertIn('TenantModelViewSet.get_queryset(view)',text);self.assertIn('view.check_permissions(view.request)',text)
            elif index==3:
                f=FakeAdapter('capture');result=q.sql_sequence(IDENTITY,q.Budget(36),lambda:f);self.assertFalse(any(x[0]=='execute' for x in f.calls));self.assertEqual(result['status'],'FAIL')
                adapter,db=real_adapter();adapter.operations={'plain-count':lambda:db.wrapper(None,'SELECT synthetic',(),False,{})}
                self.assertEqual(adapter.capture('plain-count'),('SELECT synthetic',()));self.assertEqual(db.commands,[])
                adapter.operations={'plain-count':lambda:None};self.bad(adapter.capture,'plain-count')
                adapter.operations={'plain-count':lambda:db.wrapper(None,'DELETE synthetic',(),False,{})};self.bad(adapter.capture,'plain-count')
            elif index==4:
                cursor=FakeCursor('off');adapter=q.DjangoAdapter.__new__(q.DjangoAdapter);self.bad(adapter.readonly,cursor,q.Budget(1),2000)
                self.assertEqual(cursor.commands[0][0],'SET TRANSACTION READ ONLY')
            elif index==5:
                adapter,db=real_adapter('EXPLAIN');row={}
                with self.assertRaises(RuntimeError):adapter.probe('plain-count','SELECT synthetic',(),q.Budget(5),row)
                self.assertEqual(db.transactions,['begin','rollback']);self.assertNotIn(('SELECT synthetic',()),db.commands);self.assertNotIn('executionCount',row)
            elif index==6:self.assertTrue(q.validate_sql(q.sql_sequence(IDENTITY,q.Budget(36),FakeAdapter),IDENTITY))
            elif index==7:
                f=FakeAdapter('summary');result=q.sql_sequence(IDENTITY,q.Budget(36),lambda:f);self.assertEqual([p['executionCount'] for p in result['probes']],[1,1,1,1]);self.assertEqual(f.calls.count(('execute','summary')),1);self.assertTrue(result['probes'][1]['rollbackRequired']);self.assertEqual(result['status'],'FAIL')
                adapter,db=real_adapter('SELECT synthetic');row={}
                with self.assertRaises(RuntimeError):adapter.probe('plain-count','SELECT synthetic',(),q.Budget(5),row)
                self.assertEqual(db.transactions,['begin','rollback']);self.assertEqual(row['executionCount'],1);self.assertTrue(row['rollbackRequired']);self.assertIsNone(adapter.active)
                self.assertEqual(sum(sql=='SELECT synthetic' for sql,_ in db.commands),1)
            elif index==8:
                clock=Clock();budget=q.Budget(.05,clock);f=FakeAdapter(clock=clock);result=q.sql_sequence(IDENTITY,budget,lambda:f);self.assertNotEqual(result['status'],'PASS');self.assertLessEqual(sum(p['executionCount'] for p in result['probes']),1)
            elif index==9:
                result=q.sql_sequence(IDENTITY,q.Budget(36),lambda:FakeAdapter('close'));self.assertNotEqual(result['status'],'PASS');self.assertTrue(result['observationErrors'])
            elif index==10:
                data=sql_report();data['observerStopped']=False;self.bad(q.validate_sql,data,IDENTITY)
                adapter,db=real_adapter();adapter.samples=[];adapter.errors=[];adapter.ready=threading.Event();clock=Clock()
                adapter.active=('plain-count',77,0)
                adapter.stop=SimpleNamespace(is_set=lambda:clock.now>0,wait=lambda seconds:clock.advance(seconds))
                with patch.dict(sys.modules,{'django.db.backends.postgresql.base':SimpleNamespace(DatabaseWrapper=lambda *a,**k:db)}):
                    adapter.connection.settings_dict={};adapter.observe(q.Budget(1,clock))
                self.assertFalse(adapter.errors);self.assertEqual(adapter.samples[0]['pid'],77);self.assertEqual(adapter.samples[0]['blockingPids'],[78]);self.assertTrue(adapter.samples[0]['locks']);self.assertFalse(adapter.samples[0]['observedAfterProbeCompleted'])
            else:self.fail('unimplemented')
        elif group=='result_protocol':
            frame=lambda d:'SQL_RESULT '+json.dumps(d)+'\n'
            if index==1:self.assertEqual(q.parse_sql_frame(frame(sql_report()),'',0,IDENTITY)['status'],'PASS')
            elif index==2:
                self.bad(q.parse_sql_frame,'','',0,IDENTITY);self.bad(q.parse_sql_frame,frame(sql_report())*2,'',0,IDENTITY)
            elif index==3:
                for field,value in [('protocol',2),('identity',{})]:
                    d=sql_report();d[field]=value;self.bad(q.validate_sql,d,IDENTITY)
            elif index==4:
                for names in (['plain-count']*4,list(NAMES)[:3],list(NAMES)+['extra']):
                    d=sql_report();d['probes']=[{**d['probes'][0],'name':x} for x in names];self.bad(q.validate_sql,d,IDENTITY)
            elif index==5:
                for key,value in [('executionCount',0),('executionCount',2),('readOnlyVerified',False),('statementMs',6000),('result',[True]),('result',[None]),('result',[1.2])]:
                    d=sql_report();d['probes'][0][key]=value;self.bad(q.validate_sql,d,IDENTITY)
            elif index==6:
                self.bad(q.parse_sql_frame,'SQL_RESULT {','',0,IDENTITY);self.bad(q.parse_sql_frame,'x'*(q.STREAM_LIMIT+1),'',0,IDENTITY)
            elif index==7:
                self.bad(q.parse_sql_frame,frame(sql_report()),'',1,IDENTITY);self.bad(q.parse_sql_frame,'noise\n'+frame(sql_report()),'',0,IDENTITY);self.bad(q.parse_sql_frame,frame(sql_report()),'Traceback',0,IDENTITY)
            elif index==8:
                self.bad(r.padded_report,self.directory/'report.json',{'a':'x'*(r.REPORT_LIMIT+1)})
                with patch.object(Path,'write_bytes',side_effect=OSError('synthetic I/O')):
                    with self.assertRaises(OSError):r.padded_report(self.directory/'report.json',{})
            else:self.fail('unimplemented')
        elif group=='browser_collection_gating':
            if index==1:self.assertEqual(r.validate_browser_collection(browser(True))['caseCount'],4)
            elif index==2:
                d=browser(True);d['config']['projects']*=3;self.bad(r.validate_browser_collection,d)
            elif index==3:
                d=browser(True);d['suites'][0]['specs'][1]['title']=TITLES[0];self.bad(r.validate_browser_collection,d)
                d=browser();d['suites'][0]['specs'][0]['file']='foreign.ts';self.bad(r.validate_browser_result,d,TITLES)
            elif index==4:
                for key,val in [('retries',1),('repeatEach',2)]:
                    d=browser(True);d['config']['projects'][0][key]=val;self.bad(r.validate_browser_collection,d)
                d=browser(True);d['suites'][0]['specs'][0]['tests'][0]['annotations']=[{'type':'skip'}];self.bad(r.validate_browser_collection,d)
            elif index==5:
                obj=r.StackPacket.__new__(r.StackPacket);obj.report={'phases':[]};obj.emit=lambda *a,**k:None;obj.run=lambda *a:(_ for _ in ()).throw(AssertionError('child invoked'))
                self.assertFalse(obj.do('browser',[],300,ready=False));self.assertEqual(obj.report['phases'][0]['status'],'BLOCKED')
                envelope={'protocol':1,'identity':IDENTITY,'status':'PASS','sql':sql_report(),'cgroup':{}}
                self.bad(q.validate_host_report,envelope,IDENTITY)
            elif index==6:self.assertEqual(len(r.validate_browser_result(browser(),TITLES)),4)
            elif index==7:
                for results in ([],[{'status':'timedOut'}],[{'status':'passed'}]*2):
                    d=browser();d['suites'][0]['specs'][0]['tests'][0]['results']=results;self.bad(r.validate_browser_result,d,TITLES)
            elif index==8:
                text=TEST_SPEC.read_text();self.assertIn('state.pending.length>=600',text);self.assertIn('page.context().close()',text);self.assertIn("route.abort('blockedbyclient')",text);self.assertIn("expect(state.telemetryErrors",text)
            else:self.fail('unimplemented')
        elif group=='deadlines_processes':
            if index==1:
                clock=Clock();budget=q.Budget(3,clock);clock.advance(2);self.assertEqual(budget.remaining(),1);clock.advance(1);self.bad(budget.remaining)
            elif index==2:
                clock=Clock();b=q.Budget(60,clock);clock.advance(59);self.assertLessEqual(b.millis(5000),900)
            elif index==3:
                f=SimpleNamespace(deadline=1,settimeout=lambda value:None)
                with patch.object(r.time,'monotonic',return_value=2):self.bad(r.DeadlineSocket.remaining,f)
            elif index==4:
                value,events,elapsed=self.capture(running=True,maximum=2);self.assertEqual(value['error']['code'],'DEADLINE');self.assertLessEqual(elapsed,2)
                clock=Clock();obj=r.StackPacket(Path('/fake'),self.directory,'queue-web');obj.work_deadline=20;obj.capacity=lambda:None
                class SlowStartup:
                    returncode=0;pid=876543
                    def __init__(self,*a,**k):clock.advance(25)
                    def poll(self):return 0
                    def wait(self,timeout):return 0
                with patch.object(r.time,'monotonic',clock),patch.object(r.subprocess,'Popen',SlowStartup),patch.object(q.os,'killpg',side_effect=ProcessLookupError):
                    self.bad(obj.run,'slow-start',['FAKE'],{},3)
                self.assertEqual(obj.report['phases'][0]['status'],'TIMEOUT')
            elif index==5:
                value,events,_=self.capture(running=True);self.assertTrue(events);self.assertIn('error',value)
            elif index==6:
                _,events,_=self.capture(running=True,ignore_term=True);self.assertEqual(events,[q.signal.SIGTERM,q.signal.SIGKILL])
            elif index==7:
                clock=Clock();signals=[];alive=[True]
                process=SimpleNamespace(pid=876543,poll=lambda:0,wait=lambda timeout:0)
                def signal(pid,sig):
                    self.assertEqual(pid,876543)
                    if not alive[0]:raise ProcessLookupError()
                    if sig:signals.append(sig);alive[0]=False
                with patch.object(q.os,'killpg',side_effect=signal):q.stop_owned_group(process,1,clock)
                self.assertEqual(signals,[q.signal.SIGTERM])
            elif index==8:
                self.assertEqual(r.CLEANUP_SECONDS,180);obj=r.StackPacket(Path('/fake'),self.directory,'queue-web');self.assertEqual(round(obj.deadline-obj.work_deadline),180)
            else:self.fail('unimplemented')
        elif group=='accounting_cleanup_publication':
            if index==1:
                raw={'LayersSize':1,'Containers':[],'Volumes':[],'BuildCache':[]};self.assertEqual(r.docker_sizes(raw)['layers'],1)
                self.assertEqual(r.RESERVE,2147483648)
                result,_,_=self.resource([self.du()],cap=1024);self.assertTrue(result['completeMeasurement']);self.assertEqual(result['ownedBytes'],1024)
                self.bad(self.resource,[self.du()],cap=1023);self.bad(self.resource,[self.du()],free=r.RESERVE-1)
            elif index==2:
                for bad in (None,True,-1,'0'):
                    d={'LayersSize':bad,'Containers':[],'Volumes':[],'BuildCache':[]};self.bad(r.docker_sizes,d)
                self.bad(self.resource,[self.du(size='unknown')]);self.bad(self.resource,[self.du(1,'du: permission denied')]);self.bad(self.resource,[subprocess.TimeoutExpired('FAKE',10)])
            elif index==3:
                error="du: cannot access '"+str(self.directory/'transient')+"': No such file or directory"
                result,calls,elapsed=self.resource([self.du(1,error),self.du(1,error),self.du()]);self.assertEqual(calls,3);self.assertEqual(elapsed,.75);self.assertEqual(result['measurementAttempts'],3)
                self.bad(self.resource,[self.du(1,error)]*3)
                self.bad(self.resource,[self.du(1,"du: cannot access '/foreign/transient': No such file or directory")])
            elif index==4:
                raw={'LayersSize':1,'Containers':[{}],'Volumes':[],'BuildCache':[]};self.bad(r.docker_sizes,raw);self.assertEqual(r.docker_sizes(raw,True)['containers'],0)
            elif index==5:
                p=self.directory/'result.json';n=r.padded_report(p,{'final':None});r.padded_report(p,{'final':{'bytes':12}},n);self.assertEqual(p.stat().st_size,n);self.assertEqual(json.loads(p.read_text())['final']['bytes'],12)
            elif index==6:
                item={'Id':'a'*64,'Config':{'Labels':{'com.docker.compose.project':'foreign'}},'State':{'Running':True}};self.bad(r.owned_container_states,[item],IDENTITY['project'])
            elif index==7:self.bad(r.owned_container_states,[],IDENTITY['project'],['a'*64])
            elif index==8:
                item={'Id':'a'*64,'Config':{'Labels':{'com.docker.compose.project':IDENTITY['project']}},'State':{}};self.bad(r.owned_container_states,[item],IDENTITY['project'])
                value,_,_=self.capture(b'\xff');self.assertEqual(value['error']['code'],'ENCODING')
            elif index==9:
                text=r.redact_export('password=SENTINEL Authorization: Bearer OPAQUE postgresql://user:pw@db',['SENTINEL']);self.assertNotIn('SENTINEL',text);self.assertNotIn('OPAQUE',text);self.assertNotIn('user:pw',text)
                body=base64.b64encode(b'{"password":"SENTINEL"}').decode();value=r.sanitize_attachments({'body':body,'contentType':'application/json'},['SENTINEL']);self.assertNotIn(b'SENTINEL',base64.b64decode(value['body']))
                self.bad(r.sanitize_attachments,{'body':'xxx','contentType':'image/png'})
            elif index==10:
                text=(REPO_ROOT/'.github/workflows/crm-queue-web.yml').read_text();self.assertIn('workflow_dispatch:',text);self.assertNotIn('  push:',text);self.assertIn('persist-credentials: false',text)
                self.assertEqual(r.mandatory_result([{'status':'PASS'}]),'PASS')
                for status in ('FAIL','BLOCKED','NOT_RUN','TIMEOUT','CRASH'):
                    self.assertEqual(r.mandatory_result([{'status':'PASS'},{'status':status}]),'FAIL')
                self.assertEqual(r.mandatory_result([]),'FAIL');self.assertEqual(r.mandatory_result([{'status':'PASS'}],['mandatory']),'FAIL')
            else:self.fail('unimplemented')
        else:self.fail('unknown family '+group)

FIXTURES=HERE/'tests/fixtures/audit-families.json'
if not FIXTURES.exists():FIXTURES=REPO_ROOT/'mobile/ci/diagnostic-fixtures/audit-families.json'
AUDIT=json.loads(FIXTURES.read_text())
GROUP_INDEX={}
for family in AUDIT['fixtureFamilies']:
    group=family['id'].rsplit('-',1)[0];index=int(family['id'].rsplit('-',1)[1]);GROUP_INDEX[family['id']]=(group,index)
    def make(g,n):
        def test(self):self.family(g,n)
        return test
    method=make(group,index);method.__doc__=family['purpose_and_expected']
    setattr(HarnessChecks,'test_'+family['id'].replace('-','_')+'_'+family['family'],method)
assert len(GROUP_INDEX)==64

def negative_controls():
    controls=[
     ('extra-project-accepted',r,'validate_browser_collection',lambda *_:{'caseCount':4},'browser_collection_gating_02'),
     ('credentials-forwarded',r,'public_ci_environment',lambda env,*_:dict(env),'admission_environment_07'),
     ('cgroup-malformed-accepted',q,'parse_cgroup',lambda *_:{'values':{}},'cgroup_transport_and_schema_03'),
     ('bad-sql-pass-accepted',q,'validate_sql',lambda *_:True,'result_protocol_05'),
     ('mandatory-red-masked',r,'mandatory_result',lambda *_:'PASS','accounting_cleanup_publication_10'),
     ('foreign-owner-accepted',r,'owned_container_states',lambda *_:[],'accounting_cleanup_publication_06'),
    ]
    rows=[]
    for name,target,attribute,mutation,prefix in controls:
     method=next(n for n in unittest.defaultTestLoader.getTestCaseNames(HarnessChecks) if n.startswith('test_'+prefix))
     result=unittest.TestResult()
     with patch.object(target,attribute,mutation):HarnessChecks(method).run(result)
     detected=bool(result.failures or result.errors)
     rows.append({'mutation':name,'test':method,'status':'DETECTED' if detected else 'MISSED','failures':len(result.failures),'errors':len(result.errors)})
    report={'status':'PASS' if all(x['status']=='DETECTED' for x in rows) else 'FAIL','controls':rows,'realDispatches':0}
    return report


class ShortPhaseTimingChecks(unittest.TestCase):
    def test_all_fourteen_actual_short_paths(self):
        source=ast.parse((HERE/'run_crm_followup_diagnostic.py').read_text());phases=[]
        for node in ast.walk(source):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='do' and len(node.args)>2 and isinstance(node.args[0],ast.Constant) and isinstance(node.args[2],ast.Constant) and node.args[2].value<=20 and node.args[0].value!='postgres-vendor':phases.append((node.args[0].value,node.args[2].value))
        self.assertEqual(len(phases),14)
        for label,nominal in phases:
            with self.subTest(phase=label),tempfile.TemporaryDirectory(prefix='crm-phase-fake-') as directory:
                clock=Clock();samples=[];box=[]
                class Process:
                    pid=876543;returncode=None
                    def __init__(self,*a,**k):self.due=clock()+.1;box.append(self)
                    def poll(self):
                        if clock()>=self.due:self.returncode=0
                        return self.returncode
                with patch.object(r.time,'monotonic',clock),patch.object(r.time,'sleep',side_effect=clock.advance),patch.object(r.subprocess,'Popen',Process),patch.object(r,'stop_owned_group',lambda *a:None):
                    packet=r.StackPacket(Path('/fake'),Path(directory),'queue-web')
                    def capacity():
                        samples.append(clock());clock.advance(9.5)
                        if clock()>=packet.active_deadline:raise r.Blocked('Synthetic accounting deadline')
                    packet.capacity=capacity
                    self.assertEqual(packet.run(label,['FAKE'],{},nominal),0)
                    phase=packet.report['phases'][0];self.assertEqual(phase['status'],'PASS');self.assertEqual(phase['limitSeconds'],45);self.assertGreaterEqual(len(samples),3);self.assertLess(phase['elapsedSeconds'],45)
        self.assertEqual(r.PACKET_SECONDS,5400);self.assertEqual(r.CLEANUP_SECONDS,180)
    def test_unknown_accounting_stays_red_without_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            packet=r.StackPacket(Path('/fake'),Path(directory),'queue-web');packet.capacity=lambda:(_ for _ in ()).throw(r.Blocked('unknown'))
            with patch.object(r.subprocess,'Popen',side_effect=AssertionError('dispatch forbidden')):
                with self.assertRaises(r.Blocked):packet.run('owned-container-ids',['FAKE'],{},10)
            self.assertEqual(packet.report['phases'][0]['status'],'BLOCKED')

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--negative-controls':
        report=negative_controls();Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(report['status']!='PASS')
    unittest.main(verbosity=2)
