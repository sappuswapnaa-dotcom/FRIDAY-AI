"""Optional real browser checks; opt in with FRIDAY_BROWSER_E2E=1 and install Chromium."""
import os
import pytest
from backend.types import WebOpen,WebClick,Empty
from backend.safety import SafetyError
from automation.browser import BrowserManager

pytestmark=pytest.mark.skipif(os.environ.get('FRIDAY_BROWSER_E2E')!='1',reason='Requires installed Playwright Chromium and external network')

@pytest.mark.asyncio
async def test_real_browser_public_page_and_stale_target():
    from playwright.async_api import async_playwright
    p=await async_playwright().start(); browser=await p.chromium.launch(headless=True)
    context=await browser.new_context();m=BrowserManager();m.playwright=p;m.browser=browser;m.context=context
    await context.route('**/*',m._route);m.page=await context.new_page()
    try:
        result=await m.open(WebOpen(url='https://example.com/'))
        assert result.ok and result.verified and result.data['http_status']==200
        assert (await m.read(Empty())).data['untrusted'] is True
        await m.page.set_content('<button id="test" onclick="window.clicked=true">Original</button>')
        snapshot=await m.describe_target('#test')
        await m.page.locator('#test').evaluate('(e)=>e.innerText="Changed"')
        with pytest.raises(SafetyError): await m.click(WebClick(selector='#test'),snapshot)
        assert not await m.page.evaluate('!!window.clicked')
        approved=await m.describe_target('#test')
        click=await m.click(WebClick(selector='#test'),approved)
        assert click.ok and not click.verified and await m.page.evaluate('!!window.clicked')
    finally: await m.close()
