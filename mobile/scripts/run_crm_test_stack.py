#!/usr/bin/env python3
"""One disposable CI diagnostic of existing CRM services, never production/native."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time

from run_android_jvm_checks import Packet, Blocked, CAP, RESERVE


class DockerConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


def docker_json(path):
    connection = DockerConnection('localhost', timeout=5)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(10*1024*1024+1)
        if response.status != 200 or len(raw)>10*1024*1024:
            raise Blocked('Docker accounting API unavailable or oversized')
        return json.loads(raw)
    finally:
        connection.close()


def docker_sizes(data):
    def size(value):
        if type(value) is not int or value<0:
            raise Blocked('Unknown Docker resource size; never substitute zero')
        return value
    for key in ('Containers','Volumes','BuildCache'):
        if key not in data or (data[key] is not None and not isinstance(data[key],list)):
            raise Blocked('Missing or invalid Docker resource collection: '+key)
    # Deliberately conservative: charge cache bytes even when shared with an
    # image. This is a declared upper bound, not a claim of physical disk use.
    return {'layers':size(data.get('LayersSize')),
            'containers':sum(size(x.get('SizeRw')) for x in (data.get('Containers') or [])),
            'volumes':sum(size((x.get('UsageData') or {}).get('Size')) for x in (data.get('Volumes') or [])),
            'buildCache':sum(size(x.get('Size')) for x in (data.get('BuildCache') or []))}


class StackPacket(Packet):
    def __init__(self, repo, output):
        super().__init__(repo, output)
        self.roots=[output,repo/'frontend/node_modules',repo/'frontend/dist',repo/'frontend/widget/dist',repo/'frontend/test-results']
        self.docker_baseline=None
        self.docker_growth=0
        self.api_version=None
        self.environment={}
        self.secret_values=[]
        self.preview=None
        self.compose=[]
        self.report={'status':'NOT_RUN','sourceSha':os.environ.get('GITHUB_SHA'),
                     'scope':'Existing stack stages1-7+9, synthetic data, real PostgreSQL/Redis/Celery; native/API composition and external providers excluded NOT_RUN',
                     'limits':{'jobSeconds':1200,'packetSeconds':1020,'lanes':1,
                               'capBytes':CAP,'reserveBytes':RESERVE},'phases':[],
                     'junit':{'status':'NOT_APPLICABLE'},'outsideScope':{'nativeDevice':'NOT_RUN','nativeRealAPI':'BLOCKED','externalProviders':'NOT_LIVE_VERIFIED'},
                     'accounting':'Owned files + new Docker layers/containers/volumes/cache upper bound; max with whole-volume allocation delta. Shared Docker cache may be conservatively counted twice; unknown sizes block.'}

    def capacity(self):
        version=self.api_version
        if version is None:
            version=docker_json('/version').get('ApiVersion','')
            if not re.fullmatch(r'1\.\d{2,3}',version):
                raise Blocked('Unsupported Docker accounting API version')
            self.api_version=version
        current=docker_sizes(docker_json('/v'+version+'/system/df'))
        if self.docker_baseline is None:
            self.docker_baseline=current
        self.docker_growth=max(self.docker_growth,sum(max(0,current[k]-self.docker_baseline[k]) for k in current))
        state=super().capacity()
        charged=max(self.charged_high_water,state['ownedBytes']+self.docker_growth)
        self.charged_high_water=charged
        state.update(chargedBytes=charged,capHeadroomBytes=CAP-charged,dockerGrowthUpperBoundBytes=self.docker_growth)
        if charged>CAP:
            raise Blocked('Conservative stack artifact budget exceeds unchanged2GiB cap')
        return state

    def do(self, label, command, seconds, ready=True):
        if not ready:
            self.report['phases'].append({'name':label,'status':'BLOCKED','reason':'Required earlier prerequisite did not pass'})
            self.emit('PHASE_BLOCKED',phase=label)
            return False
        try:
            return self.run(label,command,self.environment,seconds)==0
        except Blocked as error:
            if str(error)==label+' wall-clock deadline reached' and self.deadline-time.monotonic()>30:
                self.report['phases'][-1]['status']='TIMEOUT'
                return False
            raise

    def execute(self):
        if platform.system()!='Linux' or os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REF')!='refs/heads/codex/mobile-max':
            raise Blocked('Only authorized isolated Linux CI/mobile branch may run')
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=self.repo,text=True).strip()
        if head!=self.report['sourceSha'] or subprocess.check_output(['git','status','--porcelain'],cwd=self.repo,text=True):
            raise Blocked('Immutable clean checkout required')
        if not shutil.which('docker') or not shutil.which('node') or not shutil.which('npm'):
            raise Blocked('Preinstalled Docker/Node/npm required; no host installation')
        memory=dict(re.findall(r'^(MemTotal|MemAvailable):\s+(\d+) kB',Path('/proc/meminfo').read_text(),re.M))
        if int(memory.get('MemAvailable','0'))*1024<4*1024**3:
            raise Blocked('Less than4GiB available RAM for existing service topology')
        state=self.capacity()
        if state['freeBytes']-1932735283<RESERVE:
            raise Blocked('Conservative1.8GiB initial projection would breach free reserve')
        self.report.update(initialCapacity=state,memoryBytes={k:int(v)*1024 for k,v in memory.items()})
        self.environment={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}
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
                'CORS_ALLOWED_ORIGINS':'http://127.0.0.1:4173','CSRF_TRUSTED_ORIGINS':'http://127.0.0.1:4173',
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
        self.compose=['docker','compose','--project-name','crm-test-'+run_id,'-f','docker-compose.yml',
                      '-f','mobile/ci/crm-test-stack.compose.yml','--env-file',str(env_file)]
        if not self.do('compose-preflight',self.compose+['config','--quiet'],20):raise Blocked('Compose config invalid; no build attempted')
        self.emit('PREFLIGHT_PASS',sha=head,**state)
        built=self.do('image-build',self.compose+['build','web'],300)
        db=self.do('db-redis-up',self.compose+['up','-d','--wait','--wait-timeout','90','db','redis'],100,ready=built)
        manage=self.compose+['run','--no-deps','-T','web','python','manage.py']
        self.do('migration-drift',manage+['makemigrations','--check','--dry-run'],45,ready=db)
        self.do('django-check',manage+['check'],45,ready=db)
        migrated=self.do('migrate',manage+['migrate','--noinput'],90,ready=db)
        self.do('backend-tests',manage+['test','-v','2'],360,ready=migrated)
        runtime=self.do('runtime-up',self.compose+['up','-d','--no-build','--wait','--wait-timeout','60','web','celery'],70,ready=migrated)
        exec_web=self.compose+['exec','-T','web','python','manage.py']
        seeded=self.do('synthetic-seed',exec_web+['prepare_e2e_smoke_data','--password',password],60,ready=runtime)
        identity=self.do('synthetic-business-id',exec_web+['shell','-c',"from apps.businesses.models import Business; print('__BUSINESS_ID__='+str(Business.objects.get(slug='zani-e2e-demo').id))"],30,ready=seeded)
        matches=re.findall(r'__BUSINESS_ID__=(\d+)',(self.output/'synthetic-business-id.log').read_text()) if identity else []
        if identity and len(matches)!=1:raise Blocked('Ambiguous synthetic Business ID')
        self.do('real-queue-smoke',exec_web+['queue_runtime_smoke','--business-id',matches[0] if matches else '0','--timeout','45'],60,ready=bool(matches))
        installed=self.do('frontend-npm-ci',['npm','--prefix','frontend','ci','--no-audit','--no-fund'],180)
        frontend=self.do('frontend-build',['npm','--prefix','frontend','run','build'],180,ready=installed)
        if frontend:
            self.preview=subprocess.Popen(['npm','--prefix','frontend','run','preview','--','--host','127.0.0.1','--port','4173'],cwd=self.repo,env=self.environment,stdout=(self.output/'frontend-preview.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
            time.sleep(2)
        # Existing smoke temp files are retained inside disposable CI instead of
        # running its deletion trap. Its HTTP/auth/CORS assertions remain exact.
        smoke=(self.repo/'scripts/staging_smoke.sh').read_text()
        trap='trap \'rm -rf "$tmp_dir"\' EXIT'
        if smoke.count(trap)!=1:raise Blocked('Unexpected smoke cleanup shape')
        smoke=smoke.replace(trap,'# Preserve disposable smoke evidence; no deletion',1)
        (self.output/'staging-smoke-retain.sh').write_text(smoke)
        self.environment.update(API_BASE_URL='http://127.0.0.1:8000',FRONTEND_URL='http://127.0.0.1:4173',
                                PLATFORM_ADMIN_EMAIL='platform_admin@example.com',PLATFORM_ADMIN_PASSWORD=password,
                                MERCHANT_OWNER_EMAIL='business_owner@example.com',MERCHANT_OWNER_PASSWORD=password,
                                E2E_PASSWORD=password,E2E_PLATFORM_EMAIL='platform_admin@example.com',
                                E2E_OWNER_EMAIL='business_owner@example.com',E2E_OPERATOR_EMAIL='business_operator@example.com')
        self.do('internal-http-smoke',['bash',str(self.output/'staging-smoke-retain.sh')],60,ready=frontend and seeded)
        chrome=shutil.which('google-chrome')
        config=self.repo/'frontend/playwright.ci-stack.config.ts'
        if config.exists():raise Blocked('Refuse existing generated test config')
        config.write_text("import {defineConfig} from '@playwright/test';\nimport base from './playwright.staging.config';\nexport default defineConfig(base,{retries:0,workers:1,use:{...base.use,channel:'chrome',trace:'off',screenshot:'off',video:'off'},reporter:[['list'],['json',{outputFile:process.env.CRM_E2E_REPORT}]]});\n")
        self.environment['CRM_E2E_REPORT']=str(self.output/'browser-results.json')
        browser_seconds=min(300,max(0,int(self.deadline-time.monotonic()-30)))
        self.do('browser-tests',['npm','--prefix','frontend','exec','--','playwright','test','--config=frontend/playwright.ci-stack.config.ts','--workers=1','--retries=0','--global-timeout='+str(browser_seconds*1000)],browser_seconds+5,ready=frontend and seeded and bool(chrome) and browser_seconds>0)
        self.capacity()
        self.report['status']='PASS' if all(x['status']=='PASS' for x in self.report['phases']) else 'FAIL'

    def main(self):
        self.output.mkdir(parents=True,exist_ok=False)
        public=self.output/'public';public.mkdir()
        try:
            self.execute()
        except Blocked as error:self.report.update(status='BLOCKED',reason=str(error))
        except Exception as error:self.report.update(status='FAIL',reason=type(error).__name__+': '+str(error))
        finally:
            # Stop only this per-run test project; retain containers/volumes and
            # evidence. No global Docker cleanup or deletion, no new test runs.
            if self.compose:
                try:
                    with (self.output/'container-tail.log').open('w') as log:
                        subprocess.run(self.compose+['logs','--no-color','--tail','200'],cwd=self.repo,env=self.environment,stdout=log,stderr=subprocess.STDOUT,timeout=10)
                    subprocess.run(self.compose+['stop','--timeout','5'],cwd=self.repo,env=self.environment,capture_output=True,timeout=15)
                except Exception:self.report['stopNote']='Own test-project stop/log collection not confirmed; hosted runner teardown remains responsible'
            if self.preview and self.preview.poll() is None:
                self.preview.terminate()
                try:self.preview.wait(timeout=5)
                except subprocess.TimeoutExpired:self.preview.kill()
            self.report['elapsedSeconds']=round(time.monotonic()-self.start,3)
            def sanitize(text):
                for value in self.secret_values:text=text.replace(value,'[REDACTED_TEST_SECRET]')
                return re.sub(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b','[REDACTED_TEST_JWT]',text)
            for path in self.output.glob('*.log'):(public/path.name).write_text(sanitize(path.read_text(errors='replace')))
            for name in ('browser-results.json',):
                path=self.output/name
                if path.exists():(public/name).write_text(sanitize(path.read_text(errors='replace')))
            (public/'report.json').write_text(sanitize(json.dumps(self.report,indent=2)+'\n'))
            self.emit('FINAL',status=self.report['status'],reason=self.report.get('reason'))
        return 0 if self.report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(StackPacket(Path.cwd().resolve(),Path(sys.argv[1]).resolve()).main())
