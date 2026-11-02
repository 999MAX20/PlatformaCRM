#!/usr/bin/env python3
"""One disposable CI diagnostic of existing CRM services, never production/native."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import argparse
import re
import secrets
import shutil
import socket
import subprocess
import sys
import signal
from crm_client_sql_diagnostic import Budget, DiagnosticError, capture_process, stop_owned_group, validate_sql, validate_host_report, STREAM_LIMIT
import time

from run_android_jvm_checks import Packet, Blocked, CAP as ANDROID_CAP, RESERVE

assert ANDROID_CAP == RESERVE == 2147483648


EXPECTED_BROWSER_CASES=(
    'API cookie baseline: rotate refresh, me and seeded leads',
    'Product UI login preserves session across hard navigation and reload',
    'Existing smoke helper preserves session across hard navigation and reload',
    'Seed to owner API to lead DOM visibility',
)

def public_ci_environment(environ, mode):
    expected_ref='refs/heads/codex/crm-postgres-compat-review' if mode=='backend-targeted' else 'refs/heads/codex/mobile-max'
    fields={key:environ.get(key,'') for key in ('GITHUB_ACTIONS','GITHUB_REF','GITHUB_RUN_ID')}
    if fields['GITHUB_ACTIONS']!='true' or fields['GITHUB_REF']!=expected_ref or not re.fullmatch('[0-9]+',fields['GITHUB_RUN_ID']):
        raise Blocked('Missing or foreign public CI identity; do not forward arbitrary environment')
    return fields


def validate_browser_collection(listing):
    config=listing.get('config',{})
    projects=config.get('projects',[])
    if listing.get('errors') or len(projects)!=1 or projects[0].get('name')!='bounded-desktop-diagnostic':
        raise Blocked('Collection requires exactly one explicit desktop project and no errors')
    project=projects[0]
    if any(project.get(k)!=v for k,v in {'repeatEach':1,'retries':0,'timeout':45000}.items()) or project.get('testMatch')!=['auth-leads-diagnostic.spec.ts']:
        raise Blocked('Collection project limits/testMatch mismatch')
    if any(config.get(k)!=v for k,v in {'workers':1,'fullyParallel':False,'forbidOnly':True,'globalTimeout':300000,'maxFailures':0}.items()) or config.get('shard') is not None:
        raise Blocked('Collection global limits/selection mismatch')
    cases=[]
    def visit(suite):
        for spec in suite.get('specs',[]):
            for test in spec.get('tests',[]):
                cases.append({'name':spec.get('title'),'file':Path(spec.get('file','')).name,
                    'project':test.get('projectName'),'expectedStatus':test.get('expectedStatus'),
                    'annotations':test.get('annotations',[]),'executions':len(test.get('results',[]))})
        for child in suite.get('suites',[]):visit(child)
    for suite in listing.get('suites',[]):visit(suite)
    if len(cases)!=4 or len({x['name'] for x in cases})!=4 or set(x['name'] for x in cases)!=set(EXPECTED_BROWSER_CASES):
        raise Blocked('Collection must contain exactly the four expected unique cases')
    if any(x['file']!='auth-leads-diagnostic.spec.ts' or x['project']!='bounded-desktop-diagnostic' or x['expectedStatus']!='passed' or x['executions'] or any(a.get('type') in ('skip','fixme','fail','only') for a in x['annotations']) for x in cases):
        raise Blocked('Foreign spec, skip/only/expected-failure or prior execution in collection')
    return {'status':'PASS','projects':1,'specs':1,'cases':cases,'caseCount':4,'retries':0,'repeatEach':1,'browserExecutionsDuringList':0}


PACKET_SECONDS = 5400
CLEANUP_SECONDS = 180
REPORT_LIMIT = 8*1024*1024

def mandatory_result(phases, not_run=()):
    return 'PASS' if phases and not not_run and all(row.get('status')=='PASS' for row in phases) else 'FAIL'

def validate_browser_result(report, expected, identity=None):
    if not isinstance(report,dict) or report.get('errors'):raise Blocked('Browser result missing or contains global errors')
    config=report.get('config',{});projects=config.get('projects',[])
    if len(projects)!=1 or projects[0].get('name')!='bounded-desktop-diagnostic' or config.get('workers')!=1 or not 0<config.get('globalTimeout',300001)<=300000 or projects[0].get('retries')!=0 or projects[0].get('repeatEach')!=1 or projects[0].get('timeout')!=45000:
        raise Blocked('Browser final project/budget mismatch')
    cases=[]
    def visit(suite):
        for spec in suite.get('specs',[]):
            for case in spec.get('tests',[]):
                results=case.get('results',[])
                cases.append({'name':spec.get('title'),'file':Path(spec.get('file','')).name,'project':case.get('projectName'),
                    'status':results[0].get('status') if len(results)==1 else 'NOT_RUN','executionCount':len(results),'expectedStatus':case.get('expectedStatus')})
        for child in suite.get('suites',[]):visit(child)
    for suite in report.get('suites',[]):visit(suite)
    if len(cases)!=4 or set(c['name'] for c in cases)!=set(expected) or len({c['name'] for c in cases})!=4:
        raise Blocked('Browser final registry mismatch')
    if any(c['file']!='auth-leads-diagnostic.spec.ts' or c['project']!='bounded-desktop-diagnostic' or c['executionCount']!=1 or c['status']!='passed' or c['expectedStatus']!='passed' for c in cases):
        raise Blocked('Browser final mandatory case incomplete')
    return cases

def owned_container_states(items, project, expected=()):
    if not isinstance(items,list) or (expected and not items):raise Blocked('Expected owned containers missing')
    rows=[]
    for item in items:
        if not re.fullmatch('[0-9a-f]{12,64}',item.get('Id','')) or (item.get('Config',{}).get('Labels') or {}).get('com.docker.compose.project')!=project:
            raise Blocked('Foreign or invalid container identity; never stop it')
        state=item.get('State',{})
        if type(state.get('Running')) is not bool:raise Blocked('Unknown owned container state')
        rows.append({'id':item['Id'],'running':state['Running'],'status':state.get('Status'),'oomKilled':state.get('OOMKilled')})
    if expected and not set(expected)<={x['id'] for x in rows}:raise Blocked('Recorded owned IDs absent from inspect')
    return rows

def redact_export(text, secrets=()):
    for secret in secrets:
        if secret:text=text.replace(secret,'[REDACTED_TEST_SECRET]')
    text=re.sub(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b','[REDACTED_TEST_JWT]',text)
    text=re.sub(r'(?i)(authorization\s*[:=]\s*bearer\s+)[^\s"\\]+',r'\1[REDACTED]',text)
    text=re.sub(r'(postgres(?:ql)?://)[^@\s]+@',r'\1[REDACTED]@',text)
    return text

def sanitize_attachments(value,secrets=()):
    import base64
    if isinstance(value,list):return [sanitize_attachments(x,secrets) for x in value]
    if not isinstance(value,dict):return value
    result={k:sanitize_attachments(v,secrets) for k,v in value.items()}
    if 'body' in result and 'contentType' in result:
        if result['contentType']!='application/json':raise Blocked('Unknown opaque attachment cannot be safely exported')
        try:
            raw=base64.b64decode(result['body'],validate=True)
            if len(raw)>STREAM_LIMIT:raise Blocked('Attachment output limit')
            text=redact_export(raw.decode('utf-8'),secrets)
            json.loads(text);result['body']=base64.b64encode(text.encode()).decode()
        except (ValueError,UnicodeError) as error:raise Blocked('Malformed attachment') from error
    return result

def padded_report(path, data, allocation=None):
    raw=(json.dumps(data,indent=2,default=str)+'\n').encode()
    if len(raw)>REPORT_LIMIT:raise Blocked('Report output bound exceeded')
    size=allocation or ((len(raw)+8192+4095)//4096)*4096
    if len(raw)>size:raise Blocked('Final report exceeded reserved allocation')
    path.write_bytes(raw+b' '*(size-len(raw)))
    return size

class DeadlineSocket(socket.socket):
    def __init__(self, deadline):
        super().__init__(socket.AF_UNIX,socket.SOCK_STREAM);self.deadline=deadline
    def remaining(self):
        value=self.deadline-time.monotonic()
        if value<=0:raise Blocked('Resource sampling total deadline reached')
        self.settimeout(value)
    def connect(self,*args):self.remaining();return super().connect(*args)
    def recv_into(self,*args):self.remaining();return super().recv_into(*args)
    def sendall(self,*args):self.remaining();return super().sendall(*args)


class DockerConnection(http.client.HTTPConnection):
    def __init__(self, host, timeout, deadline):
        super().__init__(host,timeout=timeout);self.deadline=deadline
    def connect(self):
        self.sock = DeadlineSocket(self.deadline)
        self.sock.connect('/var/run/docker.sock')


def docker_json(path, deadline):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise Blocked('Resource sample total10second deadline reached')
    connection = DockerConnection('localhost', timeout=min(10,remaining),deadline=deadline)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(10*1024*1024+1)
        if response.status != 200 or len(raw)>10*1024*1024:
            raise Blocked('Docker accounting API unavailable or oversized')
        if time.monotonic()>=deadline:raise Blocked('Resource sample total10second deadline reached')
        return json.loads(raw)
    except (OSError, ValueError, http.client.HTTPException) as error:
        raise Blocked('Docker accounting I/O unknown: '+type(error).__name__) from error
    finally:
        connection.close()


def docker_sizes(data, known_omitted_container_zero=False):
    def size(value, field):
        if type(value) is not int or value<0:
            raise Blocked('Unknown Docker resource size at '+field+'; never substitute zero')
        return value
    for key in ('Containers','Volumes','BuildCache'):
        if key not in data or (data[key] is not None and not isinstance(data[key],list)):
            raise Blocked('Missing or invalid Docker resource collection: '+key)
    # Deliberately conservative: charge cache bytes even when shared with an
    # image. This is a declared upper bound, not a claim of physical disk use.
    # Docker28.0.4 Summary.SizeRw is int64 with json omitempty, and
    # /system/df explicitly computes container sizes. Only that verified
    # protocol omission means zero; explicit null or any unknown version does not.
    return {'layers':size(data.get('LayersSize'),'LayersSize'),
            'containers':sum(size(x.get('SizeRw',0) if known_omitted_container_zero else x.get('SizeRw'),
                                  'Containers['+str(i)+'].SizeRw') for i,x in enumerate(data.get('Containers') or [])),
            'volumes':sum(size((x.get('UsageData') or {}).get('Size'),'Volumes['+str(i)+'].UsageData.Size')
                          for i,x in enumerate(data.get('Volumes') or [])),
            'buildCache':sum(size(x.get('Size'),'BuildCache['+str(i)+'].Size') for i,x in enumerate(data.get('BuildCache') or []))}


class StackBudget(Packet):
    def capacity(self, sample_deadline=None):
        sample_deadline = min(self.deadline, sample_deadline or time.monotonic()+10)

        def check_budget(measured=None):
            free = shutil.disk_usage(self.output).free
            delta_charge = 0 if self.storage_baseline is None else (
                self.storage_baseline[0]+max(0, self.storage_baseline[1]-free))
            self.charged_high_water = max(self.charged_high_water, delta_charge,
                                          measured if measured is not None else 0)
            if free < RESERVE or self.charged_high_water > self.artifact_cap:
                raise Blocked("Artifact cap or free-space reserve reached")
            if time.monotonic() >= sample_deadline:
                raise Blocked("Resource sampling or packet deadline reached")
            return free

        # Gradle atomically moves transient cache entries. A failed traversal is
        # never an owned-size sample: remeasure only confirmed descendant ENOENT,
        # at most three reads inside the original ten-second measurement budget.
        known_roots=set(getattr(self,'known_roots',()))|{p for p in self.roots if p.is_dir()}
        self.known_roots=known_roots
        for attempt in range(3):
            if not self.output.is_dir() or any(not p.is_dir() for p in known_roots):
                raise Blocked("Required owned artifact root disappeared")
            check_budget()
            roots = [p for p in self.roots if p.exists()]
            known_roots.update(roots)
            try:
                sample = subprocess.run(["du", "-sk", *(str(p) for p in roots)], text=True,
                                        capture_output=True, timeout=sample_deadline-time.monotonic(),
                                        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"})
            except subprocess.TimeoutExpired as error:
                raise Blocked("Resource sampling exceeded its ten-second budget") from error
            check_budget()
            if any(not p.is_dir() for p in known_roots):raise Blocked('Owned root disappeared during sample')
            if sample.returncode != 0 or sample.stderr.strip():
                errors = sample.stderr.strip().splitlines()
                matches = [re.fullmatch(r"du: (?:cannot access '([^']+)'|(/.+)): No such file or directory", line)
                           for line in errors]
                transient = sample.returncode == 1 and bool(matches) and all(
                    match is not None and any(
                        Path(match[1] or match[2]) != root and
                        Path(match[1] or match[2]).is_relative_to(root) and root.is_dir()
                        for root in roots) for match in matches)
                if not transient:
                    raise Blocked("Resource measurement failed: "+sample.stderr.strip())
                self.emit("RESOURCE_REMEASURE", sample=attempt+1, reason="Owned transient descendant ENOENT")
                if attempt<2:
                    delay=(.25,.5)[attempt]
                    if sample_deadline-time.monotonic()<=delay:raise Blocked('No remaining sample allocation')
                    time.sleep(delay);check_budget()
                continue
            rows = [line.split("\t", 1) for line in sample.stdout.splitlines()]
            if len(rows) != len(roots) or any(
                len(row) != 2 or not row[0].isdigit() or row[1] != str(root)
                for row, root in zip(rows, roots)):
                raise Blocked("Incomplete or malformed resource measurement")
            owned = sum(int(row[0])*1024 for row in rows)
            free = check_budget(owned)
            if self.storage_baseline is None:
                self.storage_baseline = (owned, free)
            state = {"ownedBytes": owned, "chargedBytes": self.charged_high_water,
                     "freeBytes": free, "capHeadroomBytes": self.artifact_cap-self.charged_high_water,
                     "reserveHeadroomBytes": free-RESERVE,
                     "measurementAttempts": attempt+1, "completeMeasurement": True}
            self.report["lastCapacity"] = state
            return state
        raise Blocked("No complete resource measurement after three bounded reads")


class StackPacket(StackBudget):
    def __init__(self, repo, output, mode):
        super().__init__(repo, output)
        self.roots=[output,repo/'frontend/node_modules',repo/'frontend/dist',repo/'frontend/widget/dist',repo/'frontend/test-results']
        self.docker_baseline=None
        self.docker_growth=0
        self.api_version=None
        self.engine_version=None
        self.environment={}
        self.secret_values=[]
        self.preview=None
        self.compose=[]
        self.mode=mode
        self.deadline=self.start+PACKET_SECONDS
        self.work_deadline=self.deadline-CLEANUP_SECONDS
        self.active_deadline=self.work_deadline
        self.known_container_ids=[]
        self.artifact_cap=2147483648 if mode=='backend-targeted' else 3221225472
        self.project_name=None
        self.report={'status':'NOT_RUN','sourceSha':os.environ.get('GITHUB_SHA'),
                     'scope':mode+'; exact4 browser plus4 read-only SQL probes, no prior independent suites repeated; real PostgreSQL/Redis/Celery, synthetic data',
                     'limits':{'jobSeconds':10800,'packetSeconds':PACKET_SECONDS,'cleanupSeconds':CLEANUP_SECONDS,'lanes':1,
                               'capBytes':self.artifact_cap,'reserveBytes':RESERVE},'phases':[],
                     'junit':{'status':'NOT_APPLICABLE'},'outsideScope':{'nativeDevice':'NOT_RUN','nativeRealAPI':'BLOCKED','externalProviders':'NOT_LIVE_VERIFIED'},
                     'accounting':'Owned files + new Docker layers/containers/volumes/cache upper bound; max with whole-volume allocation delta. Shared Docker cache may be conservatively counted twice; unknown sizes block.'}

    def capacity(self):
        sample_deadline=min(self.deadline,self.active_deadline,time.monotonic()+10)
        version=self.api_version
        if version is None:
            metadata=docker_json('/version',sample_deadline)
            version=metadata.get('ApiVersion','')
            if not re.fullmatch(r'1\.\d{2,3}',version):
                raise Blocked('Unsupported Docker accounting API version')
            self.api_version=version
            self.engine_version=metadata.get('Version')
        endpoint='/v'+version+'/system/df';sample_started=time.monotonic()
        evidence={'phase':getattr(self,'current_phase','preflight'),'endpoint':endpoint,'startedElapsedSeconds':sample_started-self.start,'remainingSampleSeconds':sample_deadline-sample_started,'status':'RUNNING'}
        try:
            raw=docker_json(endpoint,sample_deadline);evidence['status']='PASS'
        except Exception as error:
            evidence.update(status='BLOCKED',error=type(error).__name__+': '+str(error));raise
        finally:
            evidence['elapsedSeconds']=time.monotonic()-sample_started
            self.report.setdefault('accountingCalls',[]).append(evidence)
            summary=self.report.setdefault('accountingSummary',{}).setdefault(evidence['phase'],{'calls':0,'elapsedSeconds':0.,'maxSeconds':0.,'blocked':0})
            summary['calls']+=1;summary['elapsedSeconds']+=evidence['elapsedSeconds'];summary['maxSeconds']=max(summary['maxSeconds'],evidence['elapsedSeconds']);summary['blocked']+=evidence['status']!='PASS'
            if len(self.report['accountingCalls'])>64:
                self.report['accountingCalls'].pop(0);self.report['accountingRecentOnly']=True
        self.report['lastResourceFieldShape']={'engineVersion':self.engine_version,'apiVersion':version,
            'containerSizeRw':[x.get('SizeRw','OMITTED') for x in (raw.get('Containers') or [])],
            'volumeSize':[(x.get('UsageData') or {}).get('Size','OMITTED') for x in (raw.get('Volumes') or [])],
            'buildCacheSize':[x.get('Size','OMITTED') for x in (raw.get('BuildCache') or [])]}
        current=docker_sizes(raw,known_omitted_container_zero=self.engine_version=='28.0.4' and version=='1.48')
        if self.docker_baseline is None:
            self.docker_baseline=current
        self.docker_growth=max(self.docker_growth,sum(max(0,current[k]-self.docker_baseline[k]) for k in current))
        state=super().capacity(sample_deadline)
        charged=max(self.charged_high_water,state['ownedBytes']+self.docker_growth)
        self.charged_high_water=charged
        state.update(chargedBytes=charged,capHeadroomBytes=self.artifact_cap-charged,dockerGrowthUpperBoundBytes=self.docker_growth)
        if charged>self.artifact_cap:
            raise Blocked('Conservative stack artifact budget exceeds explicit mode-specific artifact cap')
        return state

    def run(self,label,args,env,seconds):
        started=time.monotonic();requested=seconds
        seconds=45 if seconds<=20 else seconds
        end=min(self.work_deadline,started+seconds)
        self.current_phase=label
        entry={'name':label,'status':'NOT_RUN','limitSeconds':max(0,end-started),'requestedSeconds':requested};self.report['phases'].append(entry)
        child=None;failure=None;self.active_deadline=end-2
        try:
            if end-started<=2:raise Blocked('No phase allocation remains')
            self.capacity()
            with (self.output/(label+'.log')).open('w') as log:
                child=subprocess.Popen(args,cwd=self.repo,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                entry['childStarted']=True
                while child.poll() is None:
                    self.capacity()
                    if time.monotonic()>=end-2:raise Blocked(label+' absolute phase deadline')
                    if (self.output/(label+'.log')).stat().st_size>STREAM_LIMIT:raise Blocked('Phase output limit')
                    time.sleep(min(.1,max(.001,end-2-time.monotonic())))
            if time.monotonic()>end:raise Blocked(label+' completion beyond absolute phase deadline')
            if (self.output/(label+'.log')).stat().st_size>STREAM_LIMIT:raise Blocked('Phase output limit')
            self.capacity()
            entry.update(status='PASS' if child.returncode==0 else 'FAIL',exitCode=child.returncode)
        except BaseException as e:
            entry.update(status='TIMEOUT' if 'deadline' in str(e).lower() else 'BLOCKED',reason=type(e).__name__+': '+str(e));failure=e
        finally:
            if child:
                try:stop_owned_group(child,end)
                except Exception as error:
                    entry.update(status='BLOCKED',reason='Owned child shutdown unknown: '+str(error));failure=Blocked(entry['reason'])
            if child:entry['observedChildReturncode']=child.poll()
            self.current_phase='between-phases';self.active_deadline=self.work_deadline;entry['elapsedSeconds']=time.monotonic()-started
        if failure:raise failure
        return child.returncode

    def do(self, label, command, seconds, ready=True):
        if not ready:
            self.report['phases'].append({'name':label,'status':'BLOCKED','reason':'Required earlier prerequisite did not pass'})
            self.emit('PHASE_BLOCKED',phase=label)
            return False
        try:
            return self.run(label,command,self.environment,seconds)==0
        except Blocked as error:
            if self.report['phases'] and self.report['phases'][-1]['name']==label:
                self.report['phases'][-1].update(status='TIMEOUT' if 'deadline' in str(error) else 'BLOCKED',reason=str(error))
            # A killed Docker CLI does not prove its container stopped. Stop
            # dependent work; finally confirms only our own project shutdown.
            raise

    def execute(self):
        if platform.system()!='Linux' or os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REF')!=('refs/heads/codex/crm-postgres-compat-review' if self.mode=='backend-targeted' else 'refs/heads/codex/mobile-max'):
            raise Blocked('Only authorized isolated Linux CI and mode-specific branch may run')
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=self.repo,text=True).strip()
        if head!=self.report['sourceSha'] or subprocess.check_output(['git','status','--porcelain'],cwd=self.repo,text=True):
            raise Blocked('Immutable clean checkout required')
        if not shutil.which('docker') or not shutil.which('node') or not shutil.which('npm'):
            raise Blocked('Preinstalled Docker/Node/npm required; no host installation')
        memory=dict(re.findall(r'^(MemTotal|MemAvailable):\s+(\d+) kB',Path('/proc/meminfo').read_text(),re.M))
        if int(memory.get('MemAvailable','0'))*1024<4*1024**3:
            raise Blocked('Less than4GiB available RAM for existing service topology')
        state=self.capacity()
        projected=1932735283 if self.mode=='backend-targeted' else 3029600690
        self.report['projection']={'bytes':projected,'estimateIsNotMeasuredPeak':True}
        if state['chargedBytes']+projected>self.artifact_cap or state['freeBytes']-projected<RESERVE:
            raise Blocked('Declared projection would breach explicit cap/free reserve')
        self.report.update(initialCapacity=state,memoryBytes={k:int(v)*1024 for k,v in memory.items()})
        self.environment={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}
        self.environment.update(public_ci_environment(os.environ,self.mode))
        self.report['publicCIIdentity']={key:self.environment[key] for key in ('GITHUB_ACTIONS','GITHUB_REF','GITHUB_RUN_ID')}
        self.environment.update(CI='true',LC_ALL='C',npm_config_cache=str(self.output/'npm-cache'),
                                PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD='1',DOCKER_CONFIG=str(self.output/'docker-config'),
                                VITE_API_URL='http://127.0.0.1:8000',E2E_BASE_URL='http://127.0.0.1:4173',
                                E2E_API_BASE_URL='http://127.0.0.1:8000',E2E_SKIP_LOCAL_SETUP='true')
        for name in ('npm-cache','docker-config'):(self.output/name).mkdir()
        self.do('docker-version',['docker','version','--format','{{.Server.Version}}'],15)
        compose_version=subprocess.check_output(['docker','compose','version','--short'],env=self.environment,text=True,timeout=10).strip()
        numbers=tuple(int(x) for x in re.findall(r'\d+',compose_version)[:3])
        if numbers<(2,24,4):raise Blocked('Compose>=2.24.4 required for explicit port overrides')
        node=subprocess.check_output(['node','--version'],env=self.environment,text=True,timeout=10).strip()
        if not re.fullmatch(r'v(?:22|24)\.\d+\.\d+',node):raise Blocked('Existing Node22/24 required')
        self.report.update(toolchain={'node':node,'compose':compose_version,'dockerApi':self.api_version})
        run_id=os.environ.get('GITHUB_RUN_ID','')
        if not run_id.isdigit():raise Blocked('Missing per-run isolation ID')
        values={'SECRET_KEY':secrets.token_urlsafe(48),'POSTGRES_PASSWORD':secrets.token_urlsafe(24),
                'DEBUG':'False','ENVIRONMENT':'development','ALLOWED_HOSTS':'localhost,127.0.0.1,web',
                'POSTGRES_DB':'crm_ci','POSTGRES_USER':'crm_ci','REDIS_URL':'redis://redis:6379/0',
                'CELERY_TASK_ALWAYS_EAGER':'False','AUTOMATIONS_RUN_INLINE':'False','CELERY_TASK_STORE_EAGER_RESULT':'False',
                'WEB_CONCURRENCY':'1','CELERY_WORKER_CONCURRENCY':'1','SUPPORT_REQUIRES_GRANT':'True',
                'SECURE_SSL_REDIRECT':'False','SESSION_COOKIE_SECURE':'False','CSRF_COOKIE_SECURE':'False',
                'CORS_ALLOW_CREDENTIALS':'True','CORS_ALLOWED_ORIGINS':'http://127.0.0.1:4173','CSRF_TRUSTED_ORIGINS':'http://127.0.0.1:4173',
                'TELEGRAM_ENABLED':'False','WHATSAPP_ENABLED':'False','INSTAGRAM_ENABLED':'False',
                'MOBILE_PUSH_DELIVERY_ENABLED':'False','MOBILE_PUSH_QUEUE_ENABLED':'False',
                'AI_ENABLED':'False','AI_PROVIDER':'mock','OPENAI_API_KEY':'','OPENROUTER_API_KEY':'','KIMI_API_KEY':'',
                'EMAIL_BACKEND':'django.core.mail.backends.locmem.EmailBackend','SENTRY_DSN':'','USE_S3':'False',
                'AUTH_LOGIN_RATE':'1000/min','AUTH_REFRESH_RATE':'1000/min','CRM_TEST_RUN':run_id}
        password=secrets.token_urlsafe(24)
        self.secret_values=[values['SECRET_KEY'],values['POSTGRES_PASSWORD'],password]
        for secret in self.secret_values:print('::add-mask::'+secret,flush=True)
        values['DATABASE_URL']='postgresql://crm_ci:'+values['POSTGRES_PASSWORD']+'@db:5432/crm_ci'
        env_file=self.repo/'.env'
        if env_file.exists():raise Blocked('Refuse existing env file')
        env_file.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));env_file.chmod(0o600)
        self.report['envKeys']=sorted(values)
        self.project_name='crm-test-'+run_id+'-'+self.mode
        self.compose=['docker','compose','--project-name',self.project_name,'-f','docker-compose.yml',
                      '-f','mobile/ci/crm-test-stack.compose.yml','--env-file',str(env_file)]
        if not self.do('compose-preflight',self.compose+['config','--quiet'],20):raise Blocked('Compose config invalid; no build attempted')
        if self.mode=='queue-web':
            if not self.do('compose-effective-config',self.compose+['config','--format','json'],20):raise Blocked('Merged test topology not available')
            effective=json.loads((self.output/'compose-effective-config.log').read_text())
            services=effective['services'];proxy=services['ci-loopback']
            expected=[{'target':8080,'published':'8000','host_ip':'127.0.0.1','protocol':'tcp'}]
            actual=[{k:str(p[k]) if k=='published' else p.get(k) for k in ('target','published','host_ip','protocol')} for p in proxy.get('ports',[])]
            if actual!=expected:raise Blocked('Declared test port must be exactly127.0.0.1:8000->8080/tcp')
            if effective['networks']['default'].get('internal') is not True:raise Blocked('Application network isolation changed')
            for service in ('web','db','redis','celery'):
                if services[service].get('ports') or set(services[service]['networks'])!={'default'}:raise Blocked('Application service exposed or non-internal: '+service)
            if set(proxy['networks'])!={'default','ci-loopback'} or proxy['image']!='docker.io/library/nginx@sha256:84ed8c0dd296c188bfc24ed506f46589e9285fb0b11cf3a04d91d524d3067e11':raise Blocked('Ingress topology/image drift')
            self.report['topologyPreflight']={'status':'PASS','published':expected,'applicationServicesInternalOnly':True}
        self.emit('PREFLIGHT_PASS',sha=head,**state)
        built=self.do('image-build',self.compose+['build','web'],600)
        db=self.do('db-redis-up',self.compose+['up','-d','--wait','--wait-timeout','90','db','redis'],120,ready=built)
        manage=self.compose+['run','--no-deps','-T','web','python','manage.py']
        self.do('migration-drift',manage+['makemigrations','--check','--dry-run'],45,ready=db)
        self.do('django-check',manage+['check'],45,ready=db)
        migrated=self.do('migrate',manage+['migrate','--noinput'],180,ready=db)
        if self.mode=='backend-targeted':
            self.do('postgres-vendor',manage+['shell','-c',"from django.db import connection; assert connection.vendor=='postgresql',connection.vendor; print('POSTGRESQL_CONFIRMED')"],20,ready=migrated)
            selection=['apps.activities.tests_segments.TagsAndSegmentsTests.test_tags_are_tenant_safe_and_filter_clients', 'apps.ai_core.tests.AICoreFoundationTests.test_generate_text_can_return_controlled_error_without_key', 'apps.analytics.tests.OwnerDashboardAnalyticsTests.test_owner_dashboard_returns_real_metrics', 'apps.bots.tests.BotsFoundationTests.test_auto_booking_runs_appointment_message_delivery_and_confirmation_reply', 'apps.bots.tests.BotsFoundationTests.test_auto_pipeline_books_appointment_when_client_selects_offered_slot', 'apps.bots.tests.BotsFoundationTests.test_auto_pipeline_respects_agent_allowed_tools_for_deals', 'apps.bots.tests.BotsFoundationTests.test_auto_sales_reply_receives_playbook_prices_resources_and_slots', 'apps.bots.tests.BotsFoundationTests.test_crm_pipeline_runtime_check_command_passes_in_safe_mode', 'apps.bots.tests.BotsFoundationTests.test_public_website_chat_auto_pipeline_can_sell_and_create_draft_deal', 'apps.bots.tests.BotsFoundationTests.test_public_website_chat_auto_pipeline_lead_task_mode_is_guarded_and_idempotent', 'apps.bots.tests.InboxBackendTests.test_inbox_can_create_and_link_deal_from_conversation', 'apps.bots.tests.InboxBackendTests.test_inbox_can_create_task_and_lead_from_conversation', 'apps.bots.tests.InboxBackendTests.test_inbox_run_pipeline_creates_idempotent_crm_chain', 'apps.core.tests.PlatformDashboardTests.test_platform_users_can_open_overview_and_merchants', 'apps.activities.tests_postgres_tags', 'apps.conversations.tests_postgres_pipeline']
            tested=self.do('backend-targeted',manage+['test',*selection,'-v','2','--noinput'],360,ready=migrated)
            log=(self.output/'backend-targeted.log').read_text(errors='replace') if migrated else ''
            self.report['testSelection']=selection
            self.report['testSummary']={key:re.findall(pattern,log) for key,pattern in {
                'ran':r'Ran (\d+) tests? in ([0-9.]+)s','result':r'^(OK|FAILED[^\n]*)$',
                'skipped':r'^.*skipped [^\n]*$'}.items()}
            if tested and ('Ran 20 tests' not in log or re.search(r'\bskipped[= ]',log)):
                raise Blocked('Expected all14 known cases plus6 regressions without skip')
            self.report['status']='PASS' if all(x['status']=='PASS' for x in self.report['phases']) else 'FAIL'
            return
        runtime=self.do('runtime-up',self.compose+['up','-d','--no-build','--wait','--wait-timeout','60','web','celery'],120,ready=migrated)
        ingress=self.do('loopback-ingress-up',self.compose+['up','-d','--no-build','--wait','--wait-timeout','60','ci-loopback'],120,ready=runtime)
        exec_web=self.compose+['exec','-T','web','python','manage.py']
        seeded=self.do('synthetic-seed',exec_web+['prepare_e2e_smoke_data','--password',password],60,ready=runtime)
        identity=self.do('synthetic-business-id',exec_web+['shell','-c',"from apps.businesses.models import Business; print('__BUSINESS_ID__='+str(Business.objects.get(slug='zani-e2e-demo').id))"],30,ready=seeded)
        matches=re.findall(r'__BUSINESS_ID__=(\d+)',(self.output/'synthetic-business-id.log').read_text()) if identity else []
        if identity and len(matches)!=1:raise Blocked('Ambiguous synthetic Business ID')
        if self.mode=='queue-web':
            seed_probe = "from apps.businesses.models import Business; from apps.leads.models import Lead; import json; b=Business.objects.get(slug='zani-e2e-demo'); q=Lead.objects.filter(business=b); print('__DIAGNOSTIC_SEED__='+json.dumps({'businessId':b.id,'leadCount':q.count(),'leadIds':list(q.values_list('id',flat=True)[:100])}))"
            if not self.do('diagnostic-seed-read',exec_web+['shell','-c',seed_probe],20,ready=bool(matches)):
                raise Blocked('Synthetic seed identity/count unavailable')
            seed_lines=re.findall(r'__DIAGNOSTIC_SEED__=(.+)',(self.output/'diagnostic-seed-read.log').read_text())
            if len(seed_lines)!=1:raise Blocked('Ambiguous diagnostic seed evidence')
            seed=json.loads(seed_lines[0])
            if type(seed.get('businessId')) is not int or type(seed.get('leadCount')) is not int or seed['businessId']<=0 or seed['leadCount']<=0:
                raise Blocked('Expected seeded Business and nonempty lead set not confirmed')
            self.report['diagnosticSeed']=seed
            self.environment.update(CRM_DIAGNOSTIC_BUSINESS_ID=str(seed['businessId']),CRM_DIAGNOSTIC_LEAD_COUNT=str(seed['leadCount']))
            self.report['outsideScope']['realQueueSmoke']='PREVIOUS_PASS_NOT_RERUN'
        mapped=self.do('effective-port-bindings',self.compose+['port','ci-loopback','8080'],15,ready=ingress)
        self.do('effective-web-state',self.compose+['ps','web','ci-loopback','--format','json'],15,ready=runtime)
        internal=self.do('internal-health',self.compose+['exec','-T','web','python','-c',"import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/',timeout=5); assert r.status==200; print('INTERNAL_HEALTH200')"],15,ready=runtime)
        if mapped:
            binding=(self.output/'effective-port-bindings.log').read_text().strip()
            self.report['effectiveHostBinding']=binding
            if binding!='127.0.0.1:8000':raise Blocked('Loopback-only declared host binding not confirmed')
        actual_bindings=False
        if self.do('ingress-container-id',self.compose+['ps','--quiet','ci-loopback'],15,ready=ingress):
            cid=(self.output/'ingress-container-id.log').read_text().strip()
            if not re.fullmatch(r'[0-9a-f]{12,64}',cid):raise Blocked('Ambiguous own ingress ID')
            template='{{json .HostConfig.PortBindings}}\n{{json .NetworkSettings.Ports}}'
            if self.do('ingress-actual-bindings',['docker','inspect','--format',template,cid],15):
                values=[json.loads(line) for line in (self.output/'ingress-actual-bindings.log').read_text().splitlines() if line.strip()]
                wanted={'8080/tcp':[{'HostIp':'127.0.0.1','HostPort':'8000'}]}
                if len(values)!=2 or any({k:v for k,v in value.items() if v}!=wanted for value in values):raise Blocked('Actual ingress binding is missing or not exclusive loopback')
                actual_bindings=True
                self.report['actualBindings']={'status':'PASS','HostConfig':values[0],'NetworkSettings':values[1]}
        ledger_ready=self.do('owned-container-ids',self.compose+['ps','--all','--quiet'],10,ready=runtime)
        if ledger_ready:
            ledger_ids=(self.output/'owned-container-ids.log').read_text().split()
            if not ledger_ids or any(not re.fullmatch('[0-9a-f]{12,64}',x) for x in ledger_ids):raise Blocked('Invalid pre-SQL owned container ledger')
            ledger_ready=self.do('owned-container-inspect',['docker','inspect',*ledger_ids],10)
            if ledger_ready:
                self.known_container_ids=[x['id'] for x in owned_container_states(json.loads((self.output/'owned-container-inspect.log').read_text()),self.project_name)]
                self.report['ownedContainerIds']=self.known_container_ids
        host=self.do('api-health',['curl','--fail','--silent','--show-error','--max-time','15','http://127.0.0.1:8000/health/'],20,ready=mapped and internal and actual_bindings)
        ready=self.do('api-ready',['curl','--fail','--silent','--show-error','--max-time','15','http://127.0.0.1:8000/ready/'],20,ready=host)
        installed=self.do('frontend-npm-ci',['npm','--prefix','frontend','ci','--no-audit','--no-fund'],600)
        frontend=self.do('frontend-build',['npm','--prefix','frontend','run','build'],600,ready=installed)
        if frontend:
            self.preview=subprocess.Popen(['npm','--prefix','frontend','run','preview','--','--host','127.0.0.1','--port','4173'],cwd=self.repo,env=self.environment,stdout=(self.output/'frontend-preview.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
            time.sleep(2)
        self.environment.update(API_BASE_URL='http://127.0.0.1:8000',FRONTEND_URL='http://127.0.0.1:4173',
                                PLATFORM_ADMIN_EMAIL='platform_admin@example.com',PLATFORM_ADMIN_PASSWORD=password,
                                MERCHANT_OWNER_EMAIL='business_owner@example.com',MERCHANT_OWNER_PASSWORD=password,
                                E2E_PASSWORD=password,E2E_PLATFORM_EMAIL='platform_admin@example.com',
                                E2E_OWNER_EMAIL='business_owner@example.com',E2E_OPERATOR_EMAIL='business_operator@example.com')
        self.report['outsideScope']['priorBroadHttpSmoke']='NOT_RERUN; current API/UI cases are separate'
        chrome=shutil.which('google-chrome')
        config=self.repo/'frontend/playwright.ci-stack.config.ts'
        if config.exists():raise Blocked('Refuse existing generated test config')
        config.write_text("import {defineConfig,devices} from '@playwright/test';\nexport default defineConfig({testDir:'./e2e',testMatch:'auth-leads-diagnostic.spec.ts',timeout:45000,expect:{timeout:5000},forbidOnly:true,fullyParallel:false,retries:0,repeatEach:1,maxFailures:0,workers:1,globalTimeout:300000,projects:[{name:'bounded-desktop-diagnostic',use:{...devices['Desktop Chrome']}}],use:{baseURL:'http://127.0.0.1:4173',channel:'chrome',serviceWorkers:'block',actionTimeout:10000,navigationTimeout:10000,trace:'off',screenshot:'off',video:'off'},reporter:[['list'],['json',{outputFile:process.env.CRM_E2E_REPORT}]]});\n")
        self.environment['CRM_E2E_REPORT']=str(self.output/'browser-results.json')
        playwright=str(self.repo/'frontend/node_modules/.bin/playwright')
        collected=self.do('browser-collection',[playwright,'test','--config=frontend/playwright.ci-stack.config.ts','--list','--reporter=json'],15,ready=installed and seeded)
        if not collected:raise Blocked('Collection did not pass; no SQL or browser launch')
        listing=json.loads((self.output/'browser-collection.log').read_text())
        collection=validate_browser_collection(listing)
        collection.update(configSha256=hashlib.sha256(config.read_bytes()).hexdigest(),
                          testSha256=hashlib.sha256((self.repo/'frontend/e2e/auth-leads-diagnostic.spec.ts').read_bytes()).hexdigest())
        self.report['browserCollection']=collection
        self.emit('EXACT_FOUR_COLLECTION_PASS',**collection)
        sql_ready=self.do('client-sql-diagnostic',['python3','mobile/scripts/crm_client_sql_diagnostic.py',
            '--project',self.project_name,'--source-sha',head,'--output',str(self.output/'sql-diagnostic.json')],60,ready=bool(matches) and host and ready and ledger_ready)
        sql_file=self.output/'sql-diagnostic.json'
        if sql_file.exists():
            self.report['sqlDiagnostic']=json.loads(sql_file.read_text())
            sql_report=self.report['sqlDiagnostic']
            expected_identity={'sourceSha':head,'runId':run_id,'project':self.project_name}
            try:
                valid=validate_host_report(sql_report,expected_identity)
                sql_ready=sql_ready and sql_report.get('status')=='PASS' and valid
            except DiagnosticError as error:
                sql_ready=False;self.report['sqlProtocolError']=str(error)
        else:
            sql_ready=False
        browser_ready=frontend and seeded and host and ready and bool(chrome) and sql_ready
        if self.work_deadline-time.monotonic()<300:
            browser_ready=False
            self.report['browserBlocker']='Insufficient shared budget for full300s browser and shutdown reserve'
        if not sql_ready:self.report['browserBlocker']='Required bounded SQL diagnostic did not pass; no repeated dependent UI queries'
        self.report['browserDiagnostic']={'status':'NOT_RUN','cases':[{'name':name,'status':'NOT_RUN','executionCount':0} for name in EXPECTED_BROWSER_CASES],
                                         'old34ScenarioSuite':'NOT_RERUN_NOT_CERTIFIED','newRuntimeFixes':False}
        self.do('browser-tests',[playwright,'test','--config=frontend/playwright.ci-stack.config.ts','--workers=1','--retries=0','--global-timeout=295000'],300,ready=browser_ready)
        if not browser_ready:
            self.report['browserDiagnostic'].update(status='BLOCKED',reason=self.report.get('browserBlocker','Browser prerequisite unavailable'))
            for case in self.report['browserDiagnostic']['cases']:case['status']='BLOCKED'
        result_file=self.output/'browser-results.json'
        if result_file.exists():
            browser_report=json.loads(result_file.read_text())
            try:
                cases=validate_browser_result(browser_report,EXPECTED_BROWSER_CASES)
                if hashlib.sha256(config.read_bytes()).hexdigest()!=collection['configSha256'] or hashlib.sha256((self.repo/'frontend/e2e/auth-leads-diagnostic.spec.ts').read_bytes()).hexdigest()!=collection['testSha256']:
                    raise Blocked('Browser inputs changed after collection')
                self.report['browserDiagnostic']={'status':'PASS','cases':cases,'old34ScenarioSuite':'NOT_RERUN_NOT_CERTIFIED'}
            except Blocked as error:
                self.report['browserDiagnostic']['status']='FAIL';self.report['browserDiagnostic']['reason']=str(error)
                self.report['phases'].append({'name':'browser-diagnostic-completeness','status':'FAIL','reason':str(error)})
        elif browser_ready:
            self.report['phases'].append({'name':'browser-diagnostic-completeness','status':'BLOCKED','reason':'Required diagnostic result unavailable'})
        self.capacity()
        self.report['status']=mandatory_result(self.report['phases'])

    def main(self):
        self.output.mkdir(parents=True,exist_ok=False)
        public=self.output/'public';public.mkdir()
        # Allocate the final failure receipt before work: cap failure must not
        # require unaccounted emergency file growth merely to report BLOCKED.
        if shutil.disk_usage(self.output).free-REPORT_LIMIT<RESERVE:
            raise Blocked('Cannot reserve final receipt while preserving free-space reserve')
        target=public/'report.json';padded_report(target,{'status':'NOT_RUN'},REPORT_LIMIT)
        def safe_report(value):return json.loads(redact_export(json.dumps(value,default=str),self.secret_values))
        try:
            self.execute()
        except Blocked as error:self.report.update(status='BLOCKED',reason=str(error))
        except Exception as error:self.report.update(status='FAIL',reason=type(error).__name__+': '+str(error))
        finally:
            self.active_deadline=self.deadline
            def command(label,args,seconds):
                data=capture_process(args,self.environment,self.repo,self.output,'cleanup-'+label,Budget(seconds,end=self.deadline),seconds)
                if data.get('error') or data['exitCode']!=0:raise Blocked('Cleanup '+label+' unknown: '+str(data.get('error') or data['stderr'][:300]))
                return data['stdout']
            try:
                if self.compose:
                    ids=command('ids',self.compose+['ps','--all','--quiet'],5).split()
                    if not ids or any(not re.fullmatch('[0-9a-f]{12,64}',x) for x in ids):raise Blocked('Expected owned container list unavailable')
                    before=owned_container_states(json.loads(command('inspect-before',['docker','inspect',*ids],5)),self.project_name,self.known_container_ids)
                    self.known_container_ids=[x['id'] for x in before]
                    command('stop',['docker','stop','--time','5',*self.known_container_ids],15)
                    after=owned_container_states(json.loads(command('inspect-after',['docker','inspect',*self.known_container_ids],5)),self.project_name,self.known_container_ids)
                    if any(x['running'] for x in after):raise Blocked('Owned container remains running')
                    self.report['shutdown']={'status':'PASS','containers':after}
                    command('logs',self.compose+['logs','--no-color','--tail','200'],5)
            except Exception as error:self.report.update(status='BLOCKED',shutdown={'status':'BLOCKED','reason':type(error).__name__+': '+str(error)})
            try:
                if self.preview:
                    # The process was started in its own session; no global process listing.
                    stop_owned_group(self.preview,min(self.deadline,time.monotonic()+3))
                    self.report['previewShutdown']={'status':'PASS','exitCode':self.preview.returncode}
            except Exception as error:self.report.update(status='BLOCKED',previewShutdown={'status':'BLOCKED','reason':str(error)})
            planned=['docker-version','compose-preflight','image-build','db-redis-up','migration-drift','django-check','migrate']+(['postgres-vendor','backend-targeted'] if self.mode=='backend-targeted' else ['compose-effective-config','runtime-up','loopback-ingress-up','synthetic-seed','synthetic-business-id','diagnostic-seed-read','effective-port-bindings','effective-web-state','internal-health','ingress-container-id','ingress-actual-bindings','owned-container-ids','owned-container-inspect','api-health','api-ready','frontend-npm-ci','frontend-build','browser-collection','client-sql-diagnostic','browser-tests'])
            self.report['notRun']=[name for name in planned if name not in {x['name'] for x in self.report['phases']}]
            if self.report['notRun'] and self.report['status']=='PASS':self.report['status']='BLOCKED'
            try:
                payloads=[]
                for path in list(self.output.glob('*.log'))+[self.output/'browser-results.json']:
                    if path.exists():
                        if path.stat().st_size>STREAM_LIMIT:raise Blocked('Retained evidence output bound')
                        value=redact_export(path.read_text(errors='strict'),self.secret_values)
                        if path.name=='browser-results.json':
                            value=json.dumps(sanitize_attachments(json.loads(value),self.secret_values))
                        payloads.append((path.name,value))
                self.capacity()
                projected=sum(len(v.encode())+4096 for _,v in payloads)
                state=self.report['lastCapacity']
                if state['chargedBytes']+projected>self.artifact_cap or state['freeBytes']-projected<RESERVE:raise Blocked('Evidence export cannot fit existing cap/reserve')
                for name,value in payloads:(public/name).write_text(value)
                self.report['elapsedSeconds']=time.monotonic()-self.start
                allocation=padded_report(target,safe_report(self.report),REPORT_LIMIT)
                self.report['finalCapacity']=self.capacity()
                padded_report(target,safe_report(self.report),allocation)
                # Fixed allocation prevents the measurement metadata itself adding uncharged file growth.
                measured=self.capacity();self.report['finalCapacity']=measured
                padded_report(target,safe_report(self.report),allocation)
            except Exception as error:
                self.report.update(status='BLOCKED',finalAccounting={'status':'BLOCKED','reason':type(error).__name__+': '+str(error)})
                minimal={k:self.report.get(k) for k in ('status','sourceSha','shutdown','previewShutdown','finalAccounting','notRun')}
                try:padded_report(target,safe_report(minimal),REPORT_LIMIT)
                except Exception:pass
            self.emit('FINAL',status=self.report['status'],reason=self.report.get('reason'))
        return 0 if self.report['status']=='PASS' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('output')
    parser.add_argument('--mode',choices=['backend-targeted','queue-web'],required=True)
    args=parser.parse_args()
    raise SystemExit(StackPacket(Path.cwd().resolve(),Path(args.output).resolve(),args.mode).main())
