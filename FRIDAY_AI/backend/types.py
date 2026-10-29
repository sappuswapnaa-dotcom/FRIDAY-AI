from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class Args(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Empty(Args): pass
class Plan(Args):
    steps: list[str] = Field(min_length=1,max_length=8,description='Concise execution steps')
class App(Args):
    name: Literal['chrome','notepad','calculator','file explorer','downloads','word','whatsapp','spotify','task manager']
class Volume(Args):
    percent: int = Field(ge=0,le=100)
class Window(Args):
    title: str = Field(min_length=1,max_length=150)
    action: Literal['focus','minimize','maximize','restore']
class DesktopClick(Args):
    window_title: str = Field(min_length=1,max_length=150,description='Exact foreground window title')
    x: int = Field(ge=0,le=30000)
    y: int = Field(ge=0,le=30000)
class DesktopType(Args):
    window_title: str = Field(min_length=1,max_length=150,description='Exact foreground window title')
    text: str = Field(min_length=1,max_length=2000,description='Plain non-secret printable ASCII text; no keyboard shortcuts')
class WebOpen(Args):
    url: str = Field(min_length=1,max_length=2048)
class WebSearch(Args):
    engine: Literal['google','youtube']
    query: str = Field(min_length=1,max_length=300)
class WebClick(Args):
    selector: str = Field(min_length=1,max_length=300,description='Playwright selector for one visible element')
class WebFill(WebClick):
    text: str = Field(max_length=2000,description='Non-secret text to put into the input')
class WebSelect(WebClick):
    value: str = Field(max_length=300)
class WebScroll(Args):
    pixels: int = Field(ge=-3000,le=3000)
class WebUpload(WebClick):
    path: str = Field(min_length=1,max_length=1000)
class WebDownload(WebClick):
    path: str = Field(min_length=1,max_length=1000,description='Nonexistent target file in an authorized folder')
class Folder(Args):
    path: str = Field(min_length=1,max_length=1000)
class TextFile(Folder):
    content: str = Field(max_length=100000)
class WordFile(Folder):
    title: str = Field(max_length=200)
    paragraphs: list[str] = Field(default_factory=list,max_length=100)
class Slide(Args):
    title: str = Field(max_length=200)
    bullets: list[str] = Field(default_factory=list,max_length=12)
class PowerPoint(Folder):
    title: str = Field(max_length=200)
    slides: list[Slide] = Field(min_length=1,max_length=30)
class Spreadsheet(Folder):
    sheet_name: str = Field(default='Sheet1',min_length=1,max_length=31)
    rows: list[list[str]] = Field(min_length=1,max_length=500)
class ReadFile(Folder): pass
class SearchFiles(Args):
    directory: str = Field(min_length=1,max_length=1000)
    pattern: str = Field(default='*',max_length=100,description='Filename wildcard, e.g. *.pdf; no directory components')
class FileTransfer(Args):
    source: str = Field(min_length=1,max_length=1000)
    destination: str = Field(min_length=1,max_length=1000)
class Screen(Args):
    mode: Literal['screenshot','ocr','vision'] = 'screenshot'
    question: str = Field(default='',max_length=500)
class Schedule(Args):
    kind: Literal['reminder','open_folder']
    label: str = Field(min_length=1,max_length=150)
    when: str = Field(min_length=10,max_length=50,description='ISO 8601 datetime with timezone offset')
    repeat: Literal['once','daily'] = 'once'
    path: str = Field(default='',max_length=1000)
