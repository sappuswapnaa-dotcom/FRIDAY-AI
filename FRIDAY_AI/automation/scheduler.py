from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta
from backend import db
from backend.result import Result
from backend.safety import safe_path, SafetyError
from automation import windows

def parse_time(value):
    try:
        t=datetime.fromisoformat(value.replace('Z','+00:00'))
        if t.tzinfo is None: raise ValueError()
        return t.astimezone(timezone.utc)
    except ValueError as e: raise SafetyError('Use an ISO 8601 date and time with a timezone offset.') from e

def create(args,expected=None):
    t=parse_time(args.when)
    if t <= datetime.now(timezone.utc): raise SafetyError('Schedule time must be in the future.')
    payload={}
    if args.kind=='open_folder':
        p=safe_path(args.path,must_exist=True)
        if not p.is_dir(): raise SafetyError('Choose an authorized existing folder.')
        payload={'path':str(p)}
    id=db.save_schedule(args.kind,args.label,payload,t.isoformat(),args.repeat)
    return Result(True,True,'Schedule saved. It runs only while FRIDAY is running.',{'id':id,'next_run':t.isoformat(),'repeat':args.repeat})

async def run_loop(stop: asyncio.Event):
    while not stop.is_set():
        current=datetime.now(timezone.utc)
        for s in db.schedules():
            if not s['enabled'] or parse_time(s['next_run'])>current: continue
            try:
                if s['kind']=='reminder':
                    detail='Reminder: '+s['label']; status='verified'
                else:
                    from backend.types import Folder
                    r=await asyncio.to_thread(windows.open_path,Folder(path=s['payload']['path']))
                    detail=r.message; status='verified' if r.verified else ('unverified' if r.ok else 'failed')
                db.action('schedule:'+s['id'],s['kind'],{'schedule_id':s['id']},status,detail)
            except Exception as exc:
                status='failed'; detail=str(exc)[:500]; db.action('schedule:'+s['id'],s['kind'],{'schedule_id':s['id']},status,detail)
            if s['repeat_mode']=='daily':
                nxt=parse_time(s['next_run'])
                while nxt<=current: nxt+=timedelta(days=1)
                db.update_schedule(s['id'],next_run=nxt.isoformat(),last_result=detail)
            else: db.update_schedule(s['id'],enabled=0,last_result=detail)
        try: await asyncio.wait_for(stop.wait(),timeout=5)
        except asyncio.TimeoutError: pass
