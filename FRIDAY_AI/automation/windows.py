from __future__ import annotations
import ctypes
import os
import platform
import shutil
import subprocess
import time
import uuid
from pathlib import Path
import psutil
from backend.config import WORKSPACE
from backend.result import Result
from backend.safety import SafetyError, reject_obvious_secrets

def require_windows():
    if platform.system()!='Windows': raise SafetyError('Windows desktop control is unavailable on this operating system.')

def _registry_app(exe):
    import winreg
    for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        for view in (0, getattr(winreg,'KEY_WOW64_32KEY',0)):
            try:
                with winreg.OpenKey(hive, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\'+exe,0,winreg.KEY_READ|view) as key:
                    value=winreg.QueryValueEx(key,None)[0].strip('"')
                    value=os.path.expandvars(value)
                    if Path(value).is_file(): return value
            except OSError: pass
    return None

def find_executable(exe, candidates=()):
    require_windows()
    direct=shutil.which(exe) or _registry_app(exe)
    if direct: return direct
    for p in candidates:
        if p and Path(p).is_file(): return str(p)
    return None

def discover(name):
    require_windows()
    root=Path(os.environ.get('SystemRoot',r'C:\Windows'))
    pf=Path(os.environ.get('ProgramFiles',r'C:\Program Files'))
    pf86=Path(os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'))
    local=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData'/'Local')))
    roaming=Path(os.environ.get('APPDATA',str(Path.home()/'AppData'/'Roaming')))
    specs={
      'chrome':('chrome.exe',[pf/'Google/Chrome/Application/chrome.exe',pf86/'Google/Chrome/Application/chrome.exe',local/'Google/Chrome/Application/chrome.exe']),
      'notepad':('notepad.exe',[root/'System32/notepad.exe']),
      'calculator':('calc.exe',[root/'System32/calc.exe']),
      'file explorer':('explorer.exe',[root/'explorer.exe']),
      'downloads':('explorer.exe',[root/'explorer.exe']),
      'task manager':('taskmgr.exe',[root/'System32/taskmgr.exe']),
      'word':('WINWORD.EXE',[pf/'Microsoft Office/root/Office16/WINWORD.EXE',pf86/'Microsoft Office/root/Office16/WINWORD.EXE']),
      'whatsapp':('WhatsApp.exe',[local/'WhatsApp/WhatsApp.exe']),
      'spotify':('Spotify.exe',[roaming/'Spotify/Spotify.exe',local/'Microsoft/WindowsApps/Spotify.exe'])}
    exe,candidates=specs[name]
    return find_executable(exe,candidates)

def launch(args,expected=None):
    require_windows(); executable=discover(args.name)
    if not executable:
        return Result(False,False,f'{args.name} was not found in the usual Windows application paths. Microsoft Store apps may need a shortcut or manual launch.',{'application':args.name})
    argv=[executable]
    if args.name=='downloads':
        downloads=Path.home()/'Downloads'
        if not downloads.is_dir(): return Result(False,False,'The default Downloads folder was not found. Configure your actual folder and open it by path.',{})
        argv.append(str(downloads))
    proc=subprocess.Popen(argv,close_fds=True)  # fixed discovered executable; never a model-generated shell command
    time.sleep(0.8)
    alive=proc.poll() is None and psutil.pid_exists(proc.pid)
    if alive:
        return Result(True,True,f'{args.name} process was observed after launch.',{'application':args.name,'pid':proc.pid,'verification':'process observed; window contents not verified'})
    # Single-instance apps sometimes hand off to an existing process.
    try:
        from pywinauto import Desktop
        titles=[w.window_text() for w in Desktop(backend='uia').windows() if w.is_visible()]
        patterns={'notepad':'notepad','calculator':'calculator','file explorer':'file explorer','downloads':'downloads','task manager':'task manager','chrome':'chrome','word':'word','spotify':'spotify','whatsapp':'whatsapp'}
        matched=any(patterns[args.name] in t.lower() for t in titles)
    except Exception: matched=False
    return Result(True,matched, f'{args.name} window observed.' if matched else 'Launch request returned, but a window or running process could not be verified.',{'application':args.name,'pid':proc.pid})

def open_path(args,expected=None):
    from backend.safety import safe_path
    require_windows(); p=safe_path(args.path,must_exist=True)
    if p.is_file() and p.suffix.lower() not in {'.txt','.md','.csv','.pdf','.docx','.pptx','.xlsx','.png','.jpg','.jpeg','.webp'}:
        raise SafetyError('Only folders and common documents/images can be opened; executable or shortcut files are blocked.')
    os.startfile(str(p))
    return Result(True,False,'Windows accepted the open request; the resulting application window was not verified.',{'path':str(p)})

def list_windows(_args,expected=None):
    require_windows()
    from pywinauto import Desktop
    result=[]
    for w in Desktop(backend='uia').windows():
        try:
            title=w.window_text()
            if title and w.is_visible(): result.append({'title':title[:200],'handle':w.handle})
        except Exception: pass
        if len(result)>=50: break
    return Result(True,True,'Visible window titles collected.',{'windows':result})

def window_action(args,expected=None):
    require_windows()
    from pywinauto import Desktop
    w=Desktop(backend='uia').window(title=args.title)
    if not w.exists(timeout=2): raise SafetyError('An exact matching window title was not found.')
    if args.action=='focus': w.set_focus()
    elif args.action=='minimize': w.minimize()
    elif args.action=='maximize': w.maximize()
    else: w.restore()
    time.sleep(.3)
    user32=ctypes.windll.user32
    verified = {'focus': lambda: user32.GetForegroundWindow()==w.handle,'minimize':lambda:bool(user32.IsIconic(w.handle)),'maximize':lambda:bool(user32.IsZoomed(w.handle)),'restore':lambda:not user32.IsIconic(w.handle) and not user32.IsZoomed(w.handle)}[args.action]()
    return Result(True,verified,'Window state verified.' if verified else 'Window action was requested but could not be verified.',{'title':args.title,'action':args.action})

def _foreground_title():
    u=ctypes.windll.user32; h=u.GetForegroundWindow(); length=u.GetWindowTextLengthW(h); buf=ctypes.create_unicode_buffer(length+1); u.GetWindowTextW(h,buf,length+1); return buf.value

def desktop_click(args,expected=None):
    require_windows(); import pyautogui
    if _foreground_title()!=args.window_title: raise SafetyError('Foreground window title has changed; click cancelled.')
    w,h=pyautogui.size()
    if args.x>=w or args.y>=h: raise SafetyError('Coordinates must be on the primary screen.')
    pyautogui.FAILSAFE=True; pyautogui.click(args.x,args.y)
    return Result(True,False,'The click was dispatched to the approved foreground window; its effect was not verified.',{'window_title':args.window_title,'x':args.x,'y':args.y})

def desktop_type(args,expected=None):
    require_windows(); import pyautogui
    reject_obvious_secrets(args.text)
    if not all(32<=ord(ch)<=126 for ch in args.text): raise SafetyError('Desktop typing accepts printable ASCII only; no shortcuts or newlines.')
    if _foreground_title()!=args.window_title: raise SafetyError('Foreground window title has changed; typing cancelled.')
    try:
        import comtypes
        comtypes.CoInitialize()
        from pywinauto.uia_defines import IUIA
        focused=IUIA().iuia.GetFocusedElement()
        if focused is None or focused.CurrentIsPassword: raise SafetyError('No accessible focused field, or the field is a password field.')
    except SafetyError: raise
    except Exception as exc: raise SafetyError('Cannot confirm the focused control is not a password field; typing cancelled.') from exc
    pyautogui.FAILSAFE=True; pyautogui.write(args.text,interval=.005)
    return Result(True,False,'Text was typed into the approved window; the target application did not verify the resulting value.',{'window_title':args.window_title,'characters':len(args.text)})

def volume(args,expected=None):
    require_windows()
    import comtypes
    comtypes.CoInitialize()
    from pycaw.pycaw import AudioUtilities
    device=AudioUtilities.GetSpeakers()
    if device is None: raise SafetyError('No default audio endpoint was found.')
    try:
        endpoint=device.EndpointVolume
    except AttributeError:
        from pycaw.pycaw import IAudioEndpointVolume
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        endpoint=cast(device.Activate(IAudioEndpointVolume._iid_,CLSCTX_ALL,None),POINTER(IAudioEndpointVolume))
    endpoint.SetMasterVolumeLevelScalar(args.percent/100,None)
    actual=round(endpoint.GetMasterVolumeLevelScalar()*100)
    return Result(True,abs(actual-args.percent)<=1,'System volume read back from the audio endpoint.',{'requested':args.percent,'actual':actual})

def screenshot(args,expected=None):
    require_windows()
    from PIL import ImageGrab
    directory=WORKSPACE/'screenshots'; directory.mkdir(parents=True,exist_ok=True)
    path=directory/f'screen-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}.png'
    image=ImageGrab.grab(all_screens=True); image.save(path,'PNG')
    if not path.is_file() or path.stat().st_size==0: raise RuntimeError('Screenshot could not be verified.')
    data={'path':str(path),'width':image.width,'height':image.height}
    if args.mode=='ocr':
        try:
            import pytesseract
            text=pytesseract.image_to_string(image,timeout=30)
            data.update({'text':text[:12000], 'untrusted':True, 'truncated':len(text)>12000})
        except Exception as exc:
            return Result(False,False,'Screenshot saved, but OCR failed. Install and configure the local Tesseract executable.',{**data,'error':str(exc)[:250]})
    return Result(True,True,'Screenshot captured and file verified.' + (' OCR text is untrusted.' if args.mode=='ocr' else ''),data)
