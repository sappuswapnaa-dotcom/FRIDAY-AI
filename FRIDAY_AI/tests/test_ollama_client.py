import json
import httpx
import pytest
from backend.ollama import Ollama,ToolUnsupported,OllamaError

@pytest.mark.asyncio
async def test_model_discovery_and_actual_ndjson_decoding(monkeypatch):
    seen=[]
    def handle(req):
        seen.append((req.method,req.url.path))
        if req.url.path=='/api/tags':return httpx.Response(200,json={'models':[{'name':'qwen:test'}]})
        payload=json.loads(req.content)
        assert payload['stream'] is True and payload['model']=='qwen:test'
        return httpx.Response(200,text='{"message":{"content":"Hello"},"done":false}\n{"message":{"content":" world"},"done":true}\n')
    original=httpx.AsyncClient
    monkeypatch.setattr('backend.ollama.httpx.AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handle),**kwargs))
    client=Ollama('http://127.0.0.1:11434')
    assert await client.models()==['qwen:test']
    chunks=[s async for s in client.stream('qwen:test',[{'role':'user','content':'hi'}])]
    assert chunks==['Hello',' world'] and seen==[('GET','/api/tags'),('POST','/api/chat')]

@pytest.mark.asyncio
async def test_native_unsupported_and_structured_schema_wire(monkeypatch):
    requests=[]
    def handle(req):
        data=json.loads(req.content);requests.append(data)
        if 'tools' in data:return httpx.Response(400,json={'error':'model does not support tools'})
        return httpx.Response(200,json={'message':{'role':'assistant','content':'{"action":null}'}})
    original=httpx.AsyncClient
    monkeypatch.setattr('backend.ollama.httpx.AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handle),**kwargs))
    client=Ollama('http://127.0.0.1:11434')
    with pytest.raises(ToolUnsupported):await client.chat('small',[],tools=[{'type':'function'}])
    result=await client.chat('small',[],format={'type':'object'})
    assert result['content']=='{"action":null}' and requests[1]['format']=={'type':'object'}

@pytest.mark.asyncio
async def test_model_connection_failure_is_explicit(monkeypatch):
    def handle(req):raise httpx.ConnectError('no server',request=req)
    original=httpx.AsyncClient
    monkeypatch.setattr('backend.ollama.httpx.AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handle),**kwargs))
    with pytest.raises(OllamaError,match='unreachable'):await Ollama('http://127.0.0.1:11434').models()
