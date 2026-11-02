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


class StackPacket(Packet):
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
        self.project_name=None
        self.report={'status':'NOT_RUN','sourceSha':os.environ.get('GITHUB_SHA'),
                     'scope':mode+'; separate bounded diagnostic, no whole backend suite; real PostgreSQL/Redis/Celery, synthetic data',
                     'limits':{'jobSeconds':1200,'packetSeconds':1020,'lanes':1,
                               'capBytes':CAP,'reserveBytes':RESERVE},'phases':[],
                     'junit':{'status':'NOT_APPLICABLE'},'outsideScope':{'nativeDevice':'NOT_RUN','nativeRealAPI':'BLOCKED','externalProviders':'NOT_LIVE_VERIFIED'},
                     'accounting':'Owned files + new Docker layers/containers/volumes/cache upper bound; max with whole-volume allocation delta. Shared Docker cache may be conservatively counted twice; unknown sizes block.'}

    def capacity(self):
        version=self.api_version
        if version is None:
            metadata=docker_json('/version')
            version=metadata.get('ApiVersion','')
            if not re.fullmatch(r'1\.\d{2,3}',version):
                raise Blocked('Unsupported Docker accounting API version')
            self.api_version=version
            self.engine_version=metadata.get('Version')
        raw=docker_json('/v'+version+'/system/df')
        self.report['lastResourceFieldShape']={'engineVersion':self.engine_version,'apiVersion':version,
            'containerSizeRw':[x.get('SizeRw','OMITTED') for x in (raw.get('Containers') or [])],
            'volumeSize':[(x.get('UsageData') or {}).get('Size','OMITTED') for x in (raw.get('Volumes') or [])],
            'buildCacheSize':[x.get('Size','OMITTED') for x in (raw.get('BuildCache') or [])]}
        current=docker_sizes(raw,known_omitted_container_zero=self.engine_version=='28.0.4' and version=='1.48')
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
        self.emit('PREFLIGHT_PASS',sha=head,**state)
        built=self.do('image-build',self.compose+['build','web'],300)
        db=self.do('db-redis-up',self.compose+['up','-d','--wait','--wait-timeout','90','db','redis'],100,ready=built)
        manage=self.compose+['run','--no-deps','-T','web','python','manage.py']
        self.do('migration-drift',manage+['makemigrations','--check','--dry-run'],45,ready=db)
        self.do('django-check',manage+['check'],45,ready=db)
        migrated=self.do('migrate',manage+['migrate','--noinput'],90,ready=db)
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
        runtime=self.do('runtime-up',self.compose+['up','-d','--no-build','--wait','--wait-timeout','60','web','celery'],70,ready=migrated)
        exec_web=self.compose+['exec','-T','web','python','manage.py']
        seeded=self.do('synthetic-seed',exec_web+['prepare_e2e_smoke_data','--password',password],60,ready=runtime)
        identity=self.do('synthetic-business-id',exec_web+['shell','-c',"from apps.businesses.models import Business; print('__BUSINESS_ID__='+str(Business.objects.get(slug='zani-e2e-demo').id))"],30,ready=seeded)
        matches=re.findall(r'__BUSINESS_ID__=(\d+)',(self.output/'synthetic-business-id.log').read_text()) if identity else []
        if identity and len(matches)!=1:raise Blocked('Ambiguous synthetic Business ID')
        if self.mode=='queue-web':
            self.do('real-queue-smoke',exec_web+['queue_runtime_smoke','--business-id',matches[0] if matches else '0','--timeout','45'],60,ready=bool(matches))
        self.do('api-health',['curl','--fail','--silent','--show-error','--max-time','15','http://127.0.0.1:8000/health/'],20,ready=runtime)
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
                        tail=subprocess.run(self.compose+['logs','--no-color','--tail','200'],cwd=self.repo,env=self.environment,stdout=log,stderr=subprocess.STDOUT,timeout=10)
                    stop=subprocess.run(self.compose+['stop','--timeout','5'],cwd=self.repo,env=self.environment,capture_output=True,timeout=20)
                    listing=subprocess.run(['docker','ps','--all','--quiet','--filter','label=com.docker.compose.project='+self.project_name],cwd=self.repo,env=self.environment,text=True,capture_output=True,timeout=10)
                    if stop.returncode or listing.returncode:raise Blocked('Own container stop/list failed')
                    ids=listing.stdout.split()
                    if any(not re.fullmatch(r'[0-9a-f]{12,64}',x) for x in ids):raise Blocked('Invalid own container IDs')
                    states=[]
                    if ids:
                        stopped=subprocess.run(['docker','stop','--time','5',*ids],cwd=self.repo,env=self.environment,text=True,capture_output=True,timeout=15)
                        if stopped.returncode:raise Blocked('Own one-off containers stop failed')
                        inspect=subprocess.run(['docker','inspect',*ids],cwd=self.repo,env=self.environment,text=True,capture_output=True,timeout=10)
                        if inspect.returncode:raise Blocked('Own container stop state unknown')
                        for item in json.loads(inspect.stdout):
                            if (item.get('Config',{}).get('Labels') or {}).get('com.docker.compose.project')!=self.project_name:raise Blocked('Container ownership mismatch')
                            states.append({'id':item['Id'],'running':item['State']['Running'],'status':item['State']['Status']})
                        if any(x['running'] for x in states):raise Blocked('Own container remains running')
                    self.report['shutdown']={'status':'PASS','stopExitCode':stop.returncode,'containers':states}
                except Exception as error:
                    self.report.update(status='BLOCKED',shutdown={'status':'BLOCKED','reason':type(error).__name__+': '+str(error)})
            try:self.report['finalCapacity']=self.capacity()
            except Exception as error:self.report.update(status='BLOCKED',finalAccounting={'status':'BLOCKED','reason':type(error).__name__+': '+str(error)})
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
    parser=argparse.ArgumentParser()
    parser.add_argument('output')
    parser.add_argument('--mode',choices=['backend-targeted','queue-web'],required=True)
    args=parser.parse_args()
    raise SystemExit(StackPacket(Path.cwd().resolve(),Path(args.output).resolve(),args.mode).main())
