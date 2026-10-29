from __future__ import annotations
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import db,config,runtime
from .agent import Manager
from .ollama import Ollama,OllamaError
from .registry import Registry
from .safety import SafetyError
from .types import Schedule
from automation.browser import BrowserManager
from automation import system,scheduler
from voice import service as voice

browser=BrowserManager(); ollama=Ollama(); registry=Registry(browser); manager=Manager(ollama,registry)

@asynccontextmanager
async def lifespan(_app):
    db.init()
    stop_scheduler=asyncio.Event()
    browser.lock=asyncio.Lock()
    worker=asyncio.create_task(scheduler.run_loop(stop_scheduler))
    yield
    stop_scheduler.set(); await worker
    runners=[]
    for task in manager.tasks.values():
        if not task.terminal and task.runner: task.runner.cancel(); runners.append(task.runner)
    if runners: await asyncio.gather(*runners,return_exceptions=True)
    await browser.close()

app=FastAPI(title='FRIDAY AI',version='1.0.0',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

@app.middleware('http')
async def local_security(request:Request,call_next):
    host=request.headers.get('host','')
    try: hostname=urlsplit('http://'+host).hostname
    except ValueError: hostname=None
    if hostname not in ('localhost','127.0.0.1','::1','testserver'):
        return JSONResponse({'detail':'Invalid host. FRIDAY only accepts loopback requests.'},status_code=403)
    origin=request.headers.get('origin')
    if origin and not config.PREVIEW:
        expected=f'{request.url.scheme}://{host}'
        if origin.rstrip('/')!=expected.rstrip('/'):
            return JSONResponse({'detail':'Cross-origin requests are blocked.'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    return response

@app.exception_handler(SafetyError)
async def safety_handler(_req,exc): return JSONResponse({'detail':str(exc)},status_code=400)
@app.exception_handler(OllamaError)
async def ollama_handler(_req,exc): return JSONResponse({'detail':str(exc)},status_code=503)

class ChatRequest(BaseModel):
    conversation_id:str|None=None
    message:str=Field(min_length=1,max_length=8000)
class SettingRequest(BaseModel):
    model:str=Field(min_length=1,max_length=200)
class ApprovalRequest(BaseModel):
    approval_id:str
    approved:bool
class MemoryRequest(BaseModel):
    category:Literal['preference','application','language','command','folder','task','shortcut','other']
    name:str=Field(min_length=1,max_length=100)
    value:str=Field(min_length=1,max_length=2000)
class SpeakRequest(BaseModel):
    text:str=Field(min_length=1,max_length=4000)
    voice:str=Field(min_length=1,max_length=150)
    speed:float=Field(default=1,ge=.7,le=1.4)
class ToggleSchedule(BaseModel): enabled:bool

async def model_state():
    try:
        models=await ollama.models(); selected=db.get_setting('model')
        if selected not in models:
            selected=models[0] if models else None
            if selected: db.set_setting('model',selected)
        return {'online':True,'models':models,'selected':selected,'error':None}
    except OllamaError as exc:
        return {'online':False,'models':[],'selected':db.get_setting('model'),'error':str(exc)}

@app.post('/api/shutdown')
async def shutdown():
    if config.PREVIEW or runtime.shutdown_callback is None:
        raise HTTPException(403,'Shutdown is available only through the local desktop runner.')
    runtime.shutdown_callback()
    return {'ok':True,'message':'Graceful shutdown requested.'}

@app.get('/api/status')
async def get_status():
    state=await model_state(); metrics=await asyncio.to_thread(system.metrics)
    return {'backend':'online','mode':'sandbox preview' if config.PREVIEW else 'local','metrics':metrics,'ollama':state,'voice':voice.status(),'windows_control_available':metrics['platform']=='Windows' and not config.PREVIEW, 'workspace':str(config.WORKSPACE),'active_task':next(({'id':t.id,'status':t.status,'conversation_id':t.conversation_id} for t in manager.tasks.values() if not t.terminal),None)}

@app.get('/api/models')
async def get_models(): return await model_state()
@app.put('/api/settings/model')
async def set_model(req:SettingRequest):
    models=await ollama.models()
    if req.model not in models: raise HTTPException(400,'The selected model is not installed in Ollama.')
    db.set_setting('model',req.model); return {'selected':req.model}

@app.get('/api/conversations')
async def get_conversations(): return db.conversations()
@app.get('/api/conversations/{id}/messages')
async def get_messages(id:str):
    if not db.conversation_exists(id): raise HTTPException(404,'Conversation not found.')
    return db.messages(id)
@app.delete('/api/conversations/{id}')
async def delete_conversation(id:str):
    if any(t.conversation_id==id and not t.terminal for t in manager.tasks.values()): raise HTTPException(409,'Stop the active task first.')
    if not db.delete_conversation(id): raise HTTPException(404,'Conversation not found.')
    return {'ok':True}

@app.post('/api/chat')
async def chat(req:ChatRequest):
    message=req.message.strip()
    if not message: raise HTTPException(400,'Enter a message.')
    state=await model_state()
    if not state['online']: raise HTTPException(503,state['error'])
    if not state['selected']: raise HTTPException(409,'Ollama is running, but no model is installed. Pull a model first.')
    cid=req.conversation_id
    if cid and not db.conversation_exists(cid): raise HTTPException(404,'Conversation not found.')
    if not cid: cid=db.new_conversation()
    task=await manager.start(cid,message,state['selected'])
    return {'task_id':task.id,'conversation_id':cid,'model':state['selected']}

@app.get('/api/tasks/{id}/events')
async def task_events(id:str,request:Request):
    try:t=manager.get(id)
    except KeyError:raise HTTPException(404,'Task not found.')
    async def stream():
        index=0
        while True:
            while index<len(t.events):
                data=t.events[index]; index+=1
                yield 'data: '+json.dumps(data,ensure_ascii=False)+'\n\n'
            if t.terminal: break
            t.signal.clear()
            if index<len(t.events): continue
            try: await asyncio.wait_for(t.signal.wait(),timeout=15)
            except asyncio.TimeoutError: yield ': keepalive\n\n'
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
@app.post('/api/tasks/{id}/cancel')
async def cancel(id:str):
    try:manager.cancel(id)
    except KeyError:raise HTTPException(404,'Task not found.')
    return {'ok':True}
@app.post('/api/tasks/{id}/pause')
async def pause(id:str):
    try:manager.pause(id)
    except KeyError:raise HTTPException(404,'Task not found.')
    return {'ok':True}
@app.post('/api/tasks/{id}/resume')
async def resume(id:str):
    try:manager.resume(id)
    except KeyError:raise HTTPException(404,'Task not found.')
    return {'ok':True}
@app.post('/api/tasks/{id}/approval')
async def approval(id:str,req:ApprovalRequest):
    try:manager.decide_approval(id,req.approval_id,req.approved)
    except KeyError:raise HTTPException(404,'Task not found.')
    return {'ok':True}

@app.get('/api/actions')
async def get_actions(): return db.actions()
@app.get('/api/memories')
async def get_memories(): return db.memories()
@app.post('/api/memories')
async def create_memory(req:MemoryRequest): return {'id':db.save_memory(req.category,req.name,req.value)}
@app.put('/api/memories/{id}')
async def edit_memory(id:str,req:MemoryRequest): return {'id':db.save_memory(req.category,req.name,req.value,id)}
@app.delete('/api/memories/{id}')
async def delete_memory(id:str): return {'ok':db.delete_memory(id)}

@app.get('/api/schedules')
async def get_schedules(): return db.schedules()
@app.post('/api/schedules')
async def add_schedule(req:Schedule):
    if config.PREVIEW and req.kind=='open_folder': raise HTTPException(403,'Desktop schedules are disabled in preview.')
    return scheduler.create(req).as_dict()
@app.patch('/api/schedules/{id}')
async def toggle_schedule(id:str,req:ToggleSchedule):
    if not any(s['id']==id for s in db.schedules()): raise HTTPException(404,'Schedule not found.')
    db.update_schedule(id,enabled=int(req.enabled)); return {'ok':True}
@app.delete('/api/schedules/{id}')
async def delete_schedule(id:str): return {'ok':db.delete_schedule(id)}

@app.get('/api/voice')
async def voice_status(): return voice.status()
@app.post('/api/voice/transcribe')
async def transcribe(audio:UploadFile=File(...), language:str|None=Form(None)):
    if config.PREVIEW: raise HTTPException(403,'Microphone processing is disabled in the remote sandbox preview.')
    data=await audio.read(20*1024*1024+1)
    try: return await asyncio.to_thread(voice.transcribe,data,'.webm',language)
    except SafetyError: raise
    except Exception as e: raise HTTPException(500,'Local transcription failed: '+str(e)[:300])
@app.post('/api/voice/speak')
async def speak(req:SpeakRequest):
    if config.PREVIEW: raise HTTPException(403,'Voice processing is disabled in the remote sandbox preview.')
    try: data=await asyncio.to_thread(voice.synthesize,req.text,req.voice,req.speed)
    except SafetyError: raise
    except Exception as e: raise HTTPException(500,'Local speech synthesis failed: '+str(e)[:300])
    return Response(data,media_type='audio/wav',headers={'Cache-Control':'no-store'})

# Built production frontend is served by the loopback backend on the same origin.
dist=config.ROOT/'frontend'/'dist'
if dist.is_dir(): app.mount('/',StaticFiles(directory=str(dist),html=True),name='frontend')
