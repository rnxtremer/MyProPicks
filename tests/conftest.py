import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def tmp_data(monkeypatch, tmp_path):
    """Point every module at an empty temporary data folder."""
    monkeypatch.setenv("MYPROPICKS_DATA_DIR", str(tmp_path))
    return tmp_path
