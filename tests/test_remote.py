"""Cloud mode: files are saved to the GitHub repo so they survive app restarts."""
import base64
import json

import pytest

from mypropicks import config, ledger, remote


class FakeGitHub:
    """Stands in for the GitHub contents API."""

    def __init__(self, files=None, fail_put=False):
        self.files = dict(files or {})  # repo path -> text
        self.puts, self.dispatches = [], []
        self.fail_put = fail_put

    def __call__(self, method, url, body=None):
        if "/dispatches" in url:
            self.dispatches.append(body)
            return 204, {}
        path = url.split("/contents/", 1)[1].split("?")[0]
        if method == "GET":
            if path not in self.files:
                return 404, {}
            return 200, {"sha": f"sha-{path}",
                         "content": base64.b64encode(self.files[path].encode()).decode()}
        if method == "PUT":
            if self.fail_put:
                return 409, {"message": "conflict"}
            self.puts.append((path, body))
            self.files[path] = base64.b64decode(body["content"]).decode()
            return 200, {}
        raise AssertionError(method)


@pytest.fixture
def cloud(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    monkeypatch.setattr(remote, "PROJECT_ROOT", root)
    monkeypatch.setenv("MYPROPICKS_DATA_DIR", str(root / "data"))
    monkeypatch.setenv("MYPROPICKS_CONFIG", str(root / "config.yaml"))
    monkeypatch.setenv("MYPROPICKS_GH_TOKEN", "test-token")
    monkeypatch.setenv("MYPROPICKS_GH_REPO", "owner/MyProPicks")
    gh = FakeGitHub()
    monkeypatch.setattr(remote, "_http", gh)
    return root, gh


def test_disabled_without_token(monkeypatch):
    monkeypatch.delenv("MYPROPICKS_GH_TOKEN", raising=False)
    monkeypatch.delenv("MYPROPICKS_GH_REPO", raising=False)
    assert remote.enabled() is False


def test_trade_is_saved_to_github(cloud):
    root, gh = cloud
    ledger.append_trade("2026-12-01", "nifty20", "TCS", "BUY", 10, 3450)
    path, body = gh.puts[-1]
    assert path == "data/trades.csv"
    assert body["sha"] is None and "TCS" in gh.files[path]


def test_trade_uses_latest_github_copy(cloud):
    """A trade logged from another device must not be overwritten."""
    root, gh = cloud
    gh.files["data/trades.csv"] = ("date,portfolio,symbol,action,qty,price,charges,note\n"
                                   "2026-12-01,nifty20,INFY,BUY,5.0,1500.0,0.0,\n")
    ledger.append_trade("2026-12-02", "nifty20", "TCS", "BUY", 10, 3450)
    saved = gh.files["data/trades.csv"]
    assert "INFY" in saved and "TCS" in saved
    assert gh.puts[-1][1]["sha"] == "sha-data/trades.csv"


def test_failed_save_leaves_nothing_behind(cloud, monkeypatch):
    root, gh = cloud
    gh.fail_put = True
    with pytest.raises(ValueError, match="GitHub"):
        ledger.append_trade("2026-12-01", "nifty20", "TCS", "BUY", 10, 3450)
    assert ledger.load_trades().empty


def test_capital_is_saved_to_github(cloud):
    root, gh = cloud
    config.save_capital({"nifty20": 50000})
    assert "50000" in gh.files["config.yaml"]


def test_trigger_review(cloud):
    root, gh = cloud
    remote.trigger_review()
    assert gh.dispatches == [{"ref": "main"}]


def test_local_mode_makes_no_calls(tmp_data, monkeypatch):
    monkeypatch.delenv("MYPROPICKS_GH_TOKEN", raising=False)
    monkeypatch.setattr(remote, "_http", lambda *a, **k: pytest.fail("network call in local mode"))
    ledger.append_trade("2026-12-01", "nifty20", "TCS", "BUY", 10, 3450)
    assert len(ledger.load_trades()) == 1
