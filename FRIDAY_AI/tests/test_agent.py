import asyncio
import json
import pytest
from backend import db
from backend.agent import Manager
from backend.ollama import ToolUnsupported
from backend.registry import Registry
from backend.safety import SafetyError
from automation.browser import BrowserManager

class FakeOllama:
    def __init__(self,decisions,unsupported=False,chunks=('Done',' safely.')):
        self.decisions=list(decisions);self.unsupported=unsupported;self.chunks=chunks;self.native_seen=False
    async def chat(self,model,messages,tools=None,format=None):
        if tools is not None:
            self.native_seen=True
            if self.unsupported: raise ToolUnsupported('model does not support tools')
        result=self.decisions.pop(0) if self.decisions else {}
        return result
    async def stream(self,model,messages):
        for chunk in self.chunks:
            yield chunk

def call(name,args): return {'content':'','tool_calls':[{'function':{'name':name,'arguments':args}}]}
def manager(fake): return Manager(fake,Registry(BrowserManager()))

async def wait_approval(task):
    async def wait():
        while task.approval_id is None:
            task.signal.clear()
            if task.approval_id is not None: return
            await task.signal.wait()
    await asyncio.wait_for(wait(),2)

@pytest.mark.asyncio
async def test_native_tool_execution_and_real_chunk_events(isolated_storage):
    fake=FakeOllama([call('set_plan',{'steps':['Create the file','Verify it']}),call('create_text_file',{'path':'result.txt','content':'hello'}),{}])
    m=manager(fake);cid=db.new_conversation();task=await m.start(cid,'Create a text file.','test-model')
    await asyncio.wait_for(task.runner,3)
    assert fake.native_seen and task.status=='completed'
    assert (isolated_storage/'result.txt').read_text()=='hello'
    assert [e['text'] for e in task.events if e['type']=='delta']==['Done',' safely.']
    assert any(e['type']=='plan' for e in task.events)
    assert db.actions()[0]['status']=='verified'
    assert db.actions()[0]['arguments']['content']=='[redacted]'
    assert db.messages(cid)[-1]['content']=='Done safely.'

@pytest.mark.asyncio
async def test_structured_fallback_validates_and_executes(isolated_storage):
    decisions=[{'content':json.dumps({'plan':['Create the folder'],'action':{'name':'create_folder','arguments':{'path':'Projects'}},'answer':''})}, {'content':json.dumps({'plan':[],'action':None,'answer':'Done'})}]
    m=manager(FakeOllama(decisions,unsupported=True));cid=db.new_conversation();t=await m.start(cid,'Create a folder called Projects.','test')
    await asyncio.wait_for(t.runner,3)
    assert (isolated_storage/'Projects').is_dir() and t.status=='completed'
    assert any('structured' in e.get('message','') for e in t.events)

@pytest.mark.asyncio
async def test_invalid_fallback_never_executes_shell(isolated_storage):
    bad={'content':json.dumps({'plan':[],'action':{'name':'run_shell','arguments':{'command':'echo unsafe'}},'answer':''})}
    m=manager(FakeOllama([bad,bad,bad],unsupported=True));cid=db.new_conversation();t=await m.start(cid,'Open something','test')
    await asyncio.wait_for(t.runner,3)
    assert t.status=='failed'
    assert not db.actions() and not list(isolated_storage.iterdir())
    assert any('valid structured' in e.get('message','') for e in t.events)

@pytest.mark.asyncio
async def test_overwrite_requires_approval_and_denial_does_not_write(isolated_storage):
    p=isolated_storage/'important.txt';p.write_text('old')
    m=manager(FakeOllama([call('create_text_file',{'path':'important.txt','content':'new'}),{}],chunks=('I could not overwrite it.',)))
    cid=db.new_conversation();t=await m.start(cid,'Create important.txt','test');await wait_approval(t)
    with pytest.raises(SafetyError):m.decide_approval(t.id,'wrong-id',True)
    m.decide_approval(t.id,t.approval_id,False)
    await asyncio.wait_for(t.runner,3)
    assert p.read_text()=='old' and t.status=='needs_attention'
    assert db.actions()[0]['status']=='denied'
    assert 'Verification note' in db.messages(cid)[-1]['content']

@pytest.mark.asyncio
async def test_cancel_during_approval_does_not_write(isolated_storage):
    p=isolated_storage/'important.txt';p.write_text('old')
    m=manager(FakeOllama([call('create_text_file',{'path':'important.txt','content':'new'})]))
    cid=db.new_conversation();t=await m.start(cid,'Create important.txt','test');await wait_approval(t)
    m.cancel(t.id);await asyncio.wait_for(t.runner,3)
    assert t.status=='cancelled' and p.read_text()=='old'
    assert 'cancelled' in db.messages(cid)[-1]['content'].lower()

@pytest.mark.asyncio
async def test_guard_does_not_claim_an_unexecuted_action():
    m=manager(FakeOllama([{}],chunks=('Opened it!',)))
    cid=db.new_conversation();t=await m.start(cid,'Open Notepad.','test');await asyncio.wait_for(t.runner,3)
    assert t.status=='needs_attention' and 'did not execute' in t.answer.lower()
    assert 'Opened it!' not in t.answer

def test_sensitive_browser_actions_and_tainted_outbound_need_approval():
    from backend.types import WebSearch,WebClick
    b=BrowserManager(); b.current_url=lambda:'https://example.com/'
    r=Registry(b)
    assert r.approval('browser_click',WebClick(selector='#submit'))[1]=='https://example.com/'
    assert r.approval('browser_search',WebSearch(engine='google',query='hello'),True)
    assert r.approval('browser_search',WebSearch(engine='google',query='hello'),False) is None

@pytest.mark.asyncio
async def test_approved_overwrite_rechecks_changed_target(isolated_storage):
    p=isolated_storage/'changed.txt';p.write_text('version one')
    m=manager(FakeOllama([call('create_text_file',{'path':'changed.txt','content':'replacement'}),{}],chunks=('The file was not replaced.',)))
    cid=db.new_conversation();t=await m.start(cid,'Create changed.txt','test');await wait_approval(t)
    p.write_text('user changed it while the dialog was open')
    m.decide_approval(t.id,t.approval_id,True);await asyncio.wait_for(t.runner,3)
    assert p.read_text()=='user changed it while the dialog was open'
    assert t.status=='needs_attention' and db.actions()[0]['status']=='failed'
