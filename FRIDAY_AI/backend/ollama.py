from __future__ import annotations
import json
import httpx
from .config import OLLAMA_URL, OLLAMA_CONTEXT

class OllamaError(RuntimeError): pass
class ToolUnsupported(OllamaError): pass

class Ollama:
    def __init__(self,url=OLLAMA_URL): self.url=url.rstrip('/')
    async def models(self):
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r=await c.get(self.url+'/api/tags'); r.raise_for_status()
                return [m.get('name') or m.get('model') for m in r.json().get('models',[]) if m.get('name') or m.get('model')]
        except (httpx.HTTPError,ValueError) as e: raise OllamaError('Ollama is unreachable. Start Ollama and check http://localhost:11434.') from e
    async def chat(self,model,messages,*,tools=None,format=None):
        body={'model':model,'messages':messages,'stream':False,'options':{'temperature':0.2,'num_ctx':OLLAMA_CONTEXT}}
        if tools is not None: body['tools']=tools
        if format is not None: body['format']=format
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180,connect=5)) as c:
                r=await c.post(self.url+'/api/chat',json=body)
                if r.status_code>=400:
                    text=r.text[:600]
                    if tools is not None and r.status_code in (400,422,500) and ('tool' in text.lower() and any(t in text.lower() for t in ('support','not implement','unsupported'))): raise ToolUnsupported(text)
                    raise OllamaError(f'Ollama error {r.status_code}: {text}')
                data=r.json()
                if data.get('error'): raise OllamaError(str(data['error']))
                return data.get('message',{})
        except (httpx.HTTPError,ValueError) as e: raise OllamaError(f'Ollama request failed: {e}') from e
    async def stream(self,model,messages):
        body={'model':model,'messages':messages,'stream':True,'options':{'temperature':0.3,'num_ctx':OLLAMA_CONTEXT}}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180,connect=5)) as c:
                async with c.stream('POST',self.url+'/api/chat',json=body) as r:
                    if r.status_code>=400:
                        text=(await r.aread()).decode(errors='replace')[:500]
                        raise OllamaError(f'Ollama stream error {r.status_code}: {text}')
                    async for line in r.aiter_lines():
                        if not line.strip(): continue
                        try: data=json.loads(line)
                        except json.JSONDecodeError: raise OllamaError('Ollama sent invalid streaming JSON.')
                        if data.get('error'): raise OllamaError(str(data['error']))
                        chunk=data.get('message',{}).get('content','')
                        if chunk: yield chunk
        except httpx.HTTPError as e: raise OllamaError(f'Ollama streaming failed: {e}') from e
