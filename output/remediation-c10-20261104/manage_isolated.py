import os, runpy, socket, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import environ
environ.Env.read_env=lambda *args,**kwargs:None
original_connect=socket.socket.connect
original_connect_ex=socket.socket.connect_ex
def allowed(address):
    return isinstance(address,tuple) and str(address[0]).lower() in {'localhost','127.0.0.1','::1'}
def connect(self,address):
    if not allowed(address): raise RuntimeError('Audit harness blocked external socket connection')
    return original_connect(self,address)
def connect_ex(self,address):
    if not allowed(address): raise RuntimeError('Audit harness blocked external socket connection')
    return original_connect_ex(self,address)
socket.socket.connect=connect
socket.socket.connect_ex=connect_ex
sys.argv=[str(ROOT/'manage.py'),*sys.argv[1:]]
runpy.run_path(str(ROOT/'manage.py'),run_name='__main__')
