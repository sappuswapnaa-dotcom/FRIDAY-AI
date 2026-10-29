import pytest
from backend import config,db,safety

@pytest.fixture(autouse=True)
def isolated_storage(tmp_path,monkeypatch):
    data=tmp_path/'database'; workspace=tmp_path/'workspace'; workspace.mkdir()
    monkeypatch.setattr(config,'DATA_DIR',data)
    monkeypatch.setattr(config,'DB_PATH',data/'friday.db')
    monkeypatch.setattr(config,'WORKSPACE',workspace)
    monkeypatch.setattr(safety,'WORKSPACE',workspace)
    monkeypatch.setattr(config,'PREVIEW',False)
    monkeypatch.setenv('FRIDAY_ALLOWED_ROOTS',str(workspace))
    db.init()
    return workspace
