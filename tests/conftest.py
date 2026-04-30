import pytest
from autocorrel8Main.app import database
from autocorrel8Main.app.database import create_case

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    
    db_file = tmp_path / "test_database.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    database.init_db()
    return db_file


@pytest.fixture
def sample_case(temp_db):
    return create_case(name="Test Case", path="/tmp/case1", investigator="Josh")