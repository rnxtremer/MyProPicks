"""Cloud mode: keep the app's files in GitHub.

Free cloud hosts wipe files the app writes whenever it restarts. When MYPROPICKS_GH_TOKEN and
MYPROPICKS_GH_REPO are set, files the app changes are committed through GitHub's contents API,
and the review can be started as a GitHub Action. Without them, nothing here does anything and
the app works purely on local files.

Two repos are used. The code repo (MYPROPICKS_GH_REPO) may be public: it gets the review results
and live ranks. Your trades and capital are private, so they only ever go to the data repo
(MYPROPICKS_GH_DATA_REPO), which should be a private repo.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .config import PROJECT_ROOT

API = "https://api.github.com"
WORKFLOW = "review.yml"
PRIVATE_FILES = ("trades.csv", "capital.yaml")


def enabled() -> bool:
    return bool(os.environ.get("MYPROPICKS_GH_TOKEN") and os.environ.get("MYPROPICKS_GH_REPO"))


def data_repo() -> str:
    """The private repo for trades and capital. Raises ValueError if it isn't set."""
    repo = os.environ.get("MYPROPICKS_GH_DATA_REPO")
    if not repo:
        raise ValueError("Your trades and capital need a private data repo. Add data_repo "
                         "under [github] in the app's secrets (see docs/deploy.md).")
    return repo


def _branch() -> str:
    return os.environ.get("MYPROPICKS_GH_BRANCH", "main")


def _http(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Authorization", f"Bearer {os.environ['MYPROPICKS_GH_TOKEN']}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "MyProPicks")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else {}
        except ValueError:
            return e.code, {"message": raw.decode(errors="replace")}
    except urllib.error.URLError as e:
        return 0, {"message": str(e.reason)}


def _repo_path(local: Path) -> str:
    return Path(local).resolve().relative_to(Path(PROJECT_ROOT).resolve()).as_posix()


def _url(path: str, repo: str | None = None) -> str:
    return f"{API}/repos/{repo or os.environ['MYPROPICKS_GH_REPO']}/contents/{path}"


def pull(local: Path, repo: str | None = None) -> str | None:
    """Copy the repo's version of a file over the local one. Returns its sha (None if absent)."""
    status, data = _http("GET", f"{_url(_repo_path(local), repo)}?ref={_branch()}")
    if status == 404:
        return None
    if status != 200:
        raise ValueError(f"Couldn't read {local.name} from GitHub: {data.get('message', status)}")
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(base64.b64decode(data["content"]))
    return data["sha"]


def _sha(local: Path, repo: str | None = None) -> str | None:
    status, data = _http("GET", f"{_url(_repo_path(local), repo)}?ref={_branch()}")
    return data.get("sha") if status == 200 else None


def push(local: Path, message: str, sha: str | None = ..., repo: str | None = None) -> None:
    """Commit the local file to the repo (the code repo unless `repo` is given).

    Raises ValueError if GitHub refuses.
    """
    if Path(local).name in PRIVATE_FILES and repo is None:
        raise ValueError(f"{Path(local).name} is private and only goes to the data repo.")
    if sha is ...:
        sha = _sha(local, repo)
    body = {"message": message, "branch": _branch(), "sha": sha,
            "content": base64.b64encode(Path(local).read_bytes()).decode()}
    status, data = _http("PUT", _url(_repo_path(local), repo), body)
    if status not in (200, 201):
        raise ValueError(f"Couldn't save {Path(local).name} to GitHub: {data.get('message', status)}")


def sync_private() -> None:
    """Fetch your trades and capital from the data repo. Does nothing if it isn't set up."""
    from .config import data_dir  # late import keeps tests' data folder override working
    if not enabled() or not os.environ.get("MYPROPICKS_GH_DATA_REPO"):
        return
    for name in PRIVATE_FILES:
        pull(data_dir() / name, repo=data_repo())


def trigger_review() -> None:
    """Start the monthly-review GitHub Action now."""
    url = f"{API}/repos/{os.environ['MYPROPICKS_GH_REPO']}/actions/workflows/{WORKFLOW}/dispatches"
    status, data = _http("POST", url, {"ref": _branch()})
    if status != 204:
        raise ValueError(f"GitHub didn't start the review: {data.get('message', status)}")
