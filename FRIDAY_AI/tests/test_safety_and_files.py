from pathlib import Path
import zipfile
import pytest
from backend import config,db
from backend.safety import SafetyError,safe_path,safe_public_url,redact_arguments
from backend.types import Folder,TextFile,PowerPoint,Slide,Spreadsheet,ReadFile,FileTransfer
from automation import files,windows

def test_paths_cannot_escape_or_follow_symlinks(isolated_storage,tmp_path):
    assert safe_path('notes/a.txt')==isolated_storage/'notes/a.txt'
    with pytest.raises(SafetyError): safe_path('../../outside.txt')
    with pytest.raises(SafetyError): safe_path(str(tmp_path/'elsewhere'))
    outside=tmp_path/'external';outside.mkdir()
    try: (isolated_storage/'link').symlink_to(outside,target_is_directory=True)
    except OSError: pytest.skip('Symlink creation unavailable')
    with pytest.raises(SafetyError): safe_path('link/secret.txt')

@pytest.mark.parametrize('url',['http://127.0.0.1:8765/','http://localhost/','http://169.254.169.254/latest','http://10.1.2.3/','http://[::1]/','file:///etc/passwd','https://user:password@example.com/'])
def test_private_or_unsafe_urls_rejected(url):
    with pytest.raises(SafetyError):safe_public_url(url,resolve=False)

def test_public_url_and_redacted_log():
    assert safe_public_url('https://example.com/test',resolve=False)=='https://example.com/test'
    assert redact_arguments('create_text_file',{'path':'a.txt','content':'private'})=={'path':'a.txt','content':'[redacted]'}

def test_file_create_verify_and_overwrite_requires_current_approval(isolated_storage):
    a=TextFile(path='hello.txt',content='first')
    r=files.text_file(a); assert r.ok and r.verified
    path=isolated_storage/'hello.txt'; assert path.read_text()=='first'
    with pytest.raises(SafetyError): files.text_file(TextFile(path='hello.txt',content='blocked'))
    fp=files.fingerprint(path);path.write_text('different after approval')
    with pytest.raises(SafetyError):files.text_file(TextFile(path='hello.txt',content='blocked'),fp)
    assert path.read_text()=='different after approval'
    fp=files.fingerprint(path); r=files.text_file(TextFile(path='hello.txt',content='approved'),fp)
    assert r.verified and path.read_text()=='approved'

def test_real_docx_pptx_and_spreadsheet_generation(isolated_storage):
    from backend.types import WordFile
    from openpyxl import load_workbook
    assert files.word_file(WordFile(path='report.docx',title='Summary',paragraphs=['A real document'])).verified
    assert files.powerpoint(PowerPoint(path='deck.pptx',title='Title',slides=[Slide(title='Slide one',bullets=['Fact'])])).verified
    assert files.spreadsheet(Spreadsheet(path='data.xlsx',rows=[['Name','Value'],['Formula','=2+2']])).verified
    for name in ('report.docx','deck.pptx','data.xlsx'): assert zipfile.is_zipfile(isolated_storage/name)
    wb=load_workbook(isolated_storage/'data.xlsx'); assert wb.active['B2'].value=="'=2+2"
    assert 'A real document' in files.read_file(ReadFile(path='report.docx')).data['text']

def test_copy_move_and_credential_read_protection(isolated_storage):
    (isolated_storage/'a.txt').write_text('hello')
    result=files.transfer(FileTransfer(source='a.txt',destination='b.txt'));assert result.verified
    moved=files.transfer(FileTransfer(source='b.txt',destination='c.txt'),move=True)
    assert moved.verified and not (isolated_storage/'b.txt').exists() and (isolated_storage/'c.txt').read_text()=='hello'
    (isolated_storage/'.env').write_text('PASSWORD=bad')
    with pytest.raises(SafetyError):files.read_file(ReadFile(path='.env'))

def test_memory_rejects_obvious_credentials():
    with pytest.raises(SafetyError):db.save_memory('preference','password','hunter2')
    id=db.save_memory('language','Preferred language','English')
    assert db.memories()[0]['id']==id
    assert db.delete_memory(id)

def test_windows_control_honestly_unavailable_on_non_windows(monkeypatch):
    monkeypatch.setattr(windows.platform,'system',lambda:'Linux')
    with pytest.raises(SafetyError,match='unavailable'):windows.require_windows()
