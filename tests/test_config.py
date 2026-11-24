from mypropicks.config import PORTFOLIOS, load_config, data_dir


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.yaml")
    assert cfg["weights"]["momentum"] == 0.25
    assert PORTFOLIOS["midcap30"]["n"] == 30
    assert PORTFOLIOS["nifty20"]["n"] == 20
    assert PORTFOLIOS["smallcap50"]["n"] == 50


def test_file_overrides_default(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("weights:\n  momentum: 0.5\n")
    cfg = load_config(p)
    assert cfg["weights"]["momentum"] == 0.5
    assert cfg["weights"]["growth"] == 0.20


def test_data_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MYPROPICKS_DATA_DIR", str(tmp_path))
    assert data_dir() == tmp_path
