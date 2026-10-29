"""Production entry point. Bind only to loopback; never expose host-control APIs."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import uvicorn
from backend import runtime
if __name__=='__main__':
    server=uvicorn.Server(uvicorn.Config('backend.app:app',host='127.0.0.1',port=8765,log_level='info',workers=1))
    runtime.shutdown_callback=lambda: setattr(server,'should_exit',True)
    server.run()
