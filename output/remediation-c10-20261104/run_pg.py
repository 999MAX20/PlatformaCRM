import base64,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.codex_verify import isolated_runtime,find_available_port
OUT=Path(__file__).resolve().parent
PG=Path('C:/Program Files/PostgreSQL/17/bin')
labels=sys.argv[1:] or ['apps.bots.tests_booking_terms_concurrency', 'apps.bots.tests_booking_terms']
started=time.time()
with (OUT/'postgres-concurrency.log').open('w',encoding='utf-8') as log, isolated_runtime(python=sys.executable) as rt:
    rt.environment.update(CONNECTOR_CREDENTIAL_KEYS=json.dumps({'audit':base64.urlsafe_b64encode(os.urandom(32)).decode()}),CONNECTOR_CREDENTIAL_ACTIVE_KEY_ID='audit',PYTHONDONTWRITEBYTECODE='1')
    data=rt.database_path.parent/'pg'; port=str(find_available_port((5432,8000,5173)))
    hidden=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    def pg(name,*args):
        subprocess.run([str(PG/(name+'.exe')),*args],env=rt.environment,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=hidden)
    active=False
    try:
        pg('initdb','-D',str(data),'-U','audit','-A','trust','--encoding=UTF8','--locale=C')
        pg('pg_ctl','-D',str(data),'-l',str(data.parent/'pg.log'),'-o',f'-h 127.0.0.1 -p {port}','-w','start'); active=True
        pg('createdb','-h','127.0.0.1','-p',port,'-U','audit','audit')
        rt.environment['DATABASE_URL']=f'postgresql://audit@127.0.0.1:{port}/audit'
        command=[sys.executable,str(OUT/'manage_isolated.py'),'test',*labels,'--noinput','--keepdb','-v','2']
        proc=subprocess.run(command,cwd=ROOT,env=rt.environment,stdout=log,stderr=subprocess.STDOUT)
        result={'command':command,'returncode':proc.returncode,'duration_seconds':round(time.time()-started,2),'engine':'isolated native PostgreSQL17; loopback ephemeral cluster','labels':labels}
        (OUT/'postgres-concurrency.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        import psycopg
        with psycopg.connect(host='127.0.0.1',port=port,user='audit',dbname='postgres',autocommit=True) as conn:
            assert conn.execute('SHOW data_directory').fetchone()[0].replace('\\','/').lower()==str(data).replace('\\','/').lower()
            assert str(conn.execute('SHOW port').fetchone()[0])==port
            sessions=conn.execute("SELECT pid,state FROM pg_stat_activity WHERE datname='test_audit'").fetchall()
            result['teardown_sessions']=[{'pid':pid,'state':state} for pid,state in sessions]
            conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='test_audit' AND pid<>pg_backend_pid()")
            conn.execute('DROP DATABASE IF EXISTS test_audit')
            result['teardown']='PASS; own loopback port and absolute temporary data_directory verified; explicitly closed test_audit sessions and dropped disposable database'
        (OUT/'postgres-concurrency.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)
    finally:
        if active: pg('pg_ctl','-D',str(data),'-m','fast','-w','stop')
sys.exit(result['returncode'])
