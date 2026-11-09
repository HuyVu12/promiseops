import pytest

from promiseops.storage import db, seed


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    seed.seed(c)
    yield c
    c.close()
