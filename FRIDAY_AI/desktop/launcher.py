"""Interactive Windows launcher. Installs only project dependencies with consent."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parents[1]
VENV=ROOT/'.venv'
PYTHON=VENV/'Scripts'/'python.exe'
PIDFILE=ROOT/'database'/'friday.pid'
SERVER=ROOT/'desktop'/'server.py'
PORT=8765
URL=f'http://127.0.0.1:{PORT}'


def ask(message,default=False):
    suffix=' [Y/n] ' if default else ' [y/N] '
    try: answer=input(message+suffix).strip().lower()
    except (EOFError,KeyboardInterrupt): return False
    return answer in ('y','yes') if answer else default

def run(command,cwd=ROOT):
    print('> '+' '.join(str(x) for x in command),flush=True)
    result=subprocess.run([str(x) for x in command],cwd=cwd,check=False)
    if result.returncode: raise RuntimeError(f'Command exited with code {result.returncode}. See messages above.')

def get_json(url,timeout=3):
    with urllib.request.urlopen(url,timeout=timeout) as response:
        return json.load(response)

def port_in_use():
    with socket.socket() as s:
        s.settimeout(.3)
        return s.connect_ex(('127.0.0.1',PORT))==0

def dependencies():
    modules=['fastapi','uvicorn','httpx','pydantic','psutil','multipart','playwright','docx','pptx','openpyxl','pypdf','PIL','pytesseract','pyautogui','pywinauto','pycaw','comtypes']
    code="import importlib.util,sys; missing=[m for m in sys.argv[1:] if importlib.util.find_spec(m) is None]; print(', '.join(missing)); sys.exit(bool(missing))"
    result=subprocess.run([str(PYTHON),'-c',code,*modules],capture_output=True,text=True)
    return result.returncode==0,result.stdout.strip()

def ensure_environment():
    if sys.version_info < (3,10): raise RuntimeError('Python 3.10 or newer is required. Python 3.11 or 3.12 is recommended.')
    if not PYTHON.exists():
        print('\nA project-local Python environment is needed in .venv.')
        if not ask('Create it now?',True): raise RuntimeError('Setup cancelled; no environment created.')
        run([sys.executable,'-m','venv',str(VENV)])
    ok,missing=dependencies()
    if not ok:
        print('\nMissing project dependencies: '+missing)
        print('Installing requirements downloads Python packages into this project environment, not system software.')
        if not ask('Install project Python dependencies now?',True): raise RuntimeError('Install was declined. Run .venv\\Scripts\\python -m pip install -r requirements.txt later.')
        run([PYTHON,'-m','pip','install','-r',ROOT/'requirements.txt'])
        ok,missing=dependencies()
        if not ok: raise RuntimeError('Some Python dependencies are still missing: '+missing)
    print('Python project dependencies: OK')
    if not (ROOT/'frontend'/'dist'/'index.html').is_file():
        npm=shutil.which('npm.cmd') or shutil.which('npm')
        if not npm: raise RuntimeError('The built dashboard is missing. Install Node.js LTS, then run npm --prefix frontend install and npm --prefix frontend run build.')
        print('\nA dashboard build is needed. npm will download project-local frontend dependencies.')
        if not ask('Install frontend dependencies and build the dashboard?',True): raise RuntimeError('Frontend build was declined.')
        run([npm,'--prefix','frontend','install']); run([npm,'--prefix','frontend','run','build'])
    print('Dashboard build: OK')
    local=Path(os.environ.get('LOCALAPPDATA',''))
    pf=Path(os.environ.get('PROGRAMFILES','C:/Program Files'))
    pf86=Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))
    chrome=any(p.is_file() for p in [pf/'Google/Chrome/Application/chrome.exe',pf86/'Google/Chrome/Application/chrome.exe',local/'Google/Chrome/Application/chrome.exe'])
    cache=local/'ms-playwright'
    chromium=cache.exists() and any(cache.glob('chromium-*'))
    if not chrome and not chromium:
        print('\nOptional browser automation requires installed Chrome or Playwright Chromium.')
        if ask('Download Playwright Chromium now?',False): run([PYTHON,'-m','playwright','install','chromium'])
        else: print('Skipped. You can install it later: .venv\\Scripts\\python -m playwright install chromium')

def check_ollama():
    address=os.environ.get('FRIDAY_OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
    try:
        data=get_json(address+'/api/tags'); models=[m.get('name') or m.get('model') for m in data.get('models',[])]
        print('\nOllama: reachable at '+address)
        print('Installed models: '+(', '.join(str(x) for x in models) if models else '(none)'))
        if not models: print('Install a model yourself, e.g.: ollama pull qwen2.5:3b')
    except (OSError,ValueError,urllib.error.URLError):
        print('\nOLLAMA IS NOT RUNNING OR NOT REACHABLE at '+address)
        print('Start Ollama from the Start menu (or run ollama serve), then install a model, e.g. ollama pull qwen2.5:3b.')
        print('The dashboard will open offline and reconnect after Ollama is available.')

def verify_process(pid,created=None):
    try:
        import psutil
        p=psutil.Process(int(pid))
        if created is not None and abs(p.create_time()-float(created))>1: return None
        parts=p.cmdline()
        if not any(Path(part).resolve()==SERVER.resolve() for part in parts if part): return None
        return p
    except Exception: return None

def read_pid():
    try:return json.loads(PIDFILE.read_text(encoding='utf-8'))
    except (OSError,ValueError):return None

def start():
    if os.name!='nt': raise RuntimeError('This launcher is for Windows. See README for development instructions.')
    print('FRIDAY AI  |  Local Windows startup\n'+'-'*44)
    ensure_environment(); check_ollama()
    # The launcher itself may be running on system Python; use project packages for psutil.
    site=VENV/'Lib'/'site-packages'
    if str(site) not in sys.path: sys.path.insert(0,str(site))
    if port_in_use():
        existing=read_pid()
        if existing and verify_process(existing.get('pid'),existing.get('created')):
            print('\nFRIDAY is already running. Opening the dashboard.');webbrowser.open(URL);return
        raise RuntimeError(f'Port {PORT} is already in use by another process. It was not changed or stopped.')
    (ROOT/'database').mkdir(exist_ok=True)
    log_path=ROOT/'database'/'friday.log'
    with open(log_path,'ab',buffering=0) as log:
        flags=getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)
        process=subprocess.Popen([str(PYTHON),str(SERVER)],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=flags,close_fds=True)
    import psutil
    PIDFILE.write_text(json.dumps({'pid':process.pid,'created':psutil.Process(process.pid).create_time(),'server':str(SERVER)}),encoding='utf-8')
    healthy=False
    for _ in range(25):
        if process.poll() is not None: break
        try:
            state=get_json(URL+'/api/status',timeout=2)
            if state.get('backend')=='online': healthy=True;break
        except (OSError,ValueError,urllib.error.URLError): pass
        time.sleep(.4)
    if not healthy:
        raise RuntimeError(f'Backend did not become ready. Check {log_path}. Use STOP_FRIDAY.bat to stop it if needed.')
    print('\nFRIDAY backend and dashboard are running at '+URL)
    print('The automation engine is local to this Windows session. Use STOP_FRIDAY.bat to stop it.')
    if not webbrowser.open(URL): print('Open the address above in your browser.')

def stop():
    print('FRIDAY AI  |  Stop local server\n'+'-'*44)
    record=read_pid()
    if not record: print('No FRIDAY process record found. Nothing was stopped.');return
    process=verify_process(record.get('pid'),record.get('created'))
    if not process:
        print('The recorded process is not this project server. Nothing was stopped.');PIDFILE.unlink(missing_ok=True);return
    try:
        request=urllib.request.Request(URL+'/api/shutdown',data=b'{}',headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(request,timeout=3) as response: response.read()
        process.wait(timeout=12)
    except Exception:
        print('Graceful shutdown did not finish; stopping the verified FRIDAY process.')
        process.terminate()
        try:process.wait(timeout=6)
        except Exception: process.kill();process.wait(timeout=3)
    PIDFILE.unlink(missing_ok=True)
    print('FRIDAY server stopped. Ollama and other applications were left running.')
    print('Actions already dispatched may have completed; check their result before restarting.')

if __name__=='__main__':
    try:
        if len(sys.argv)>1 and sys.argv[1]=='stop': stop()
        else: start()
    except (Exception,KeyboardInterrupt) as exc:
        print('\nFRIDAY startup/stop error: '+str(exc));sys.exit(1)
