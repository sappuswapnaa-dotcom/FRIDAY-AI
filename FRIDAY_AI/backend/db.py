from __future__ import annotations
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from . import config
from .safety import reject_obvious_secrets

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def uid() -> str:
    return uuid.uuid4().hex

def connect():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys = ON')
    return c

def init():
    with connect() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id,id);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, category TEXT NOT NULL, name TEXT NOT NULL, value TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, name TEXT NOT NULL, arguments TEXT NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY, kind TEXT NOT NULL, label TEXT NOT NULL, payload TEXT NOT NULL, next_run TEXT NOT NULL, repeat_mode TEXT NOT NULL, enabled INTEGER NOT NULL, created_at TEXT NOT NULL, last_result TEXT);
        ''')

def new_conversation(title='New conversation'):
    id = uid(); ts = now()
    with connect() as c:
        c.execute('INSERT INTO conversations VALUES(?,?,?,?)', (id,title[:80],ts,ts))
    return id

def conversations():
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM conversations ORDER BY updated_at DESC LIMIT 100')]

def conversation_exists(id):
    with connect() as c:
        return c.execute('SELECT 1 FROM conversations WHERE id=?',(id,)).fetchone() is not None

def messages(id, limit=100):
    with connect() as c:
        rows = c.execute('SELECT role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?', (id,limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

def add_message(id, role, content):
    if role not in ('user','assistant'):
        raise ValueError('Invalid message role.')
    ts = now()
    with connect() as c:
        c.execute('INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)',(id,role,content,ts))
        if role == 'user':
            c.execute("UPDATE conversations SET updated_at=?, title=CASE WHEN title='New conversation' THEN ? ELSE title END WHERE id=?",(ts,' '.join(content.split())[:60] or 'Conversation',id))
        else:
            c.execute('UPDATE conversations SET updated_at=? WHERE id=?',(ts,id))

def delete_conversation(id):
    with connect() as c:
        return c.execute('DELETE FROM conversations WHERE id=?',(id,)).rowcount > 0

def get_setting(key, default=None):
    with connect() as c:
        row=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return json.loads(row['value']) if row else default

def set_setting(key,value):
    with connect() as c:
        c.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value)))

def memories():
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM memories ORDER BY updated_at DESC LIMIT 100')]

def save_memory(category, name, value, id=None):
    reject_obvious_secrets(f'{name}={value}')
    if category not in ('preference','application','language','command','folder','task','shortcut','other'):
        raise ValueError('Unsupported memory category.')
    id = id or uid()
    with connect() as c:
        c.execute('''INSERT INTO memories(id,category,name,value,updated_at) VALUES(?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET category=excluded.category,name=excluded.name,value=excluded.value,updated_at=excluded.updated_at''',(id,category,name[:100],value[:2000],now()))
    return id

def delete_memory(id):
    with connect() as c:
        return c.execute('DELETE FROM memories WHERE id=?',(id,)).rowcount > 0

def action(task_id,name,arguments,status,detail):
    with connect() as c:
        c.execute('INSERT INTO actions(task_id,name,arguments,status,detail,created_at) VALUES(?,?,?,?,?,?)',(task_id,name,json.dumps(arguments,ensure_ascii=False),status,str(detail)[:1200],now()))

def actions(limit=30):
    with connect() as c:
        rows = c.execute('SELECT * FROM actions ORDER BY id DESC LIMIT ?', (min(limit,200),)).fetchall()
    result=[]
    for r in rows:
        d=dict(r); d['arguments']=json.loads(d['arguments']); result.append(d)
    return result

def save_schedule(kind,label,payload,next_run,repeat_mode):
    id=uid()
    with connect() as c:
        c.execute('INSERT INTO schedules VALUES(?,?,?,?,?,?,?,?,?)',(id,kind,label,json.dumps(payload),next_run,repeat_mode,1,now(),None))
    return id

def schedules():
    with connect() as c:
        rows=c.execute('SELECT * FROM schedules ORDER BY created_at DESC').fetchall()
    out=[]
    for r in rows:
        d=dict(r); d['payload']=json.loads(d['payload']); d['enabled']=bool(d['enabled']); out.append(d)
    return out

def update_schedule(id, *, enabled=None, next_run=None, last_result=None):
    cols=[]; values=[]
    for k,v in [('enabled',enabled),('next_run',next_run),('last_result',last_result)]:
        if v is not None: cols.append(f'{k}=?'); values.append(v)
    if not cols: return
    with connect() as c: c.execute(f"UPDATE schedules SET {','.join(cols)} WHERE id=?",[*values,id])

def delete_schedule(id):
    with connect() as c: return c.execute('DELETE FROM schedules WHERE id=?',(id,)).rowcount > 0
