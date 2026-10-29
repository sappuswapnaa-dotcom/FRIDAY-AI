from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from backend.config import ROOT
from backend.safety import SafetyError

MODEL = Path(os.environ.get('FRIDAY_WHISPER_MODEL', str(ROOT/'models'/'whisper'))).expanduser()
VOICES = Path(os.environ.get('FRIDAY_PIPER_VOICES', str(ROOT/'voice'/'voices'))).expanduser()
_model=None
_lock=threading.Lock()

def piper_exe():
    configured=os.environ.get('FRIDAY_PIPER_EXE')
    if configured and Path(configured).is_file(): return configured
    local=ROOT/'voice'/'piper'/'piper.exe'
    return str(local) if local.is_file() else shutil.which('piper')

def voices():
    if not VOICES.is_dir(): return []
    return [p.stem for p in sorted(VOICES.glob('*.onnx')) if p.with_suffix('.onnx.json').is_file()]

def status():
    try:
        import importlib.util
        installed=importlib.util.find_spec('faster_whisper') is not None
    except Exception: installed=False
    model_ready=MODEL.is_dir() and (MODEL/'model.bin').is_file()
    return {'whisper_package':installed,'whisper_model':model_ready,'whisper_ready':installed and model_ready,'whisper_path':str(MODEL), 'piper_ready':bool(piper_exe() and voices()),'piper_executable':bool(piper_exe()),'piper_voices':voices()}

def transcribe(data: bytes, extension='.webm', language=None):
    global _model
    if not status()['whisper_ready']: raise SafetyError('Offline recognition is not configured. Install voice/requirements-voice.txt and a local faster-whisper model; see README.')
    if not data or len(data)>20*1024*1024: raise SafetyError('Audio is empty or exceeds 20 MB.')
    with _lock:
        from faster_whisper import WhisperModel
        if _model is None: _model=WhisperModel(str(MODEL),device='cpu',compute_type='int8',local_files_only=True)
        file=None
        try:
            with tempfile.NamedTemporaryFile(suffix=extension,delete=False) as f: file=Path(f.name); f.write(data)
            segments,info=_model.transcribe(str(file),beam_size=1,language=language or None, vad_filter=True)
            text=' '.join(s.text.strip() for s in segments).strip()
            return {'text':text,'language':info.language}
        finally:
            if file: file.unlink(missing_ok=True)

def synthesize(text,voice,speed):
    exe=piper_exe()
    if not exe or voice not in voices(): raise SafetyError('Piper executable or selected local voice is not available. See README.')
    if not .7<=speed<=1.4: raise SafetyError('Voice speed must be between 0.7 and 1.4.')
    model=VOICES/(voice+'.onnx'); path=None
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f: path=Path(f.name)
        run=subprocess.run([exe,'--model',str(model),'--output_file',str(path),'--length_scale',str(round(1/speed,3))],input=text.encode('utf-8'),capture_output=True,timeout=90,check=False)
        if run.returncode!=0 or not path.exists() or path.stat().st_size<44:
            raise SafetyError('Piper could not synthesize audio. Check the voice model and executable.')
        return path.read_bytes()
    finally:
        if path: path.unlink(missing_ok=True)
