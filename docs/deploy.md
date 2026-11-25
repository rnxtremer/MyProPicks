# Deploying MyProPicks to Streamlit Community Cloud (free)

## How it works in the cloud

| Piece | Where it lives | Who can see it |
|---|---|---|
| Code, monthly lists, rankings | This repo (`MyProPicks`) | Public, if you make the repo public |
| Monthly review | A GitHub Action (`.github/workflows/review.yml`), 08:00 IST on the 1st, or on demand | Results are the model portfolio only |
| Your trades and capital | A second, **private** repo (`MyProPicks-data`) | Only you |
| The app | Streamlit Community Cloud | Analysis pages: anyone with the link. Holdings, Log a trade, Settings: only with the app password |

The review never reads your trades or capital, so what it commits here reveals nothing about
your money. Your own sells, buys and quantities are worked out live on the locked
**My holdings & P&L** page.

Cloud mode switches on when the app finds a GitHub token in its secrets. Without one (on your
PC), everything works on local files exactly as before, and no password is asked for.

## One-time setup

### 1. The two repos
1. **Code repo:** `MyProPicks`, already pushed. It can be public or private.
2. **Data repo:** on github.com → **New repository** → name `MyProPicks-data` →
   **Private** → tick **Add a README** (so the repo isn't empty) → Create. Leave it otherwise
   empty: the app creates `data/trades.csv` and `data/capital.yaml` in it the first time you
   log a trade or save your capital.

### 2. A token the app can use
GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate new token (or edit
your existing one):
- Repository access: **Only select repositories** → `MyProPicks` **and** `MyProPicks-data`
- Permissions: **Contents: Read and write**, **Actions: Read and write**
- Copy the token. Never paste it into chat or commit it.

### 3. Deploy on Streamlit Community Cloud
1. Go to share.streamlit.io and sign in with GitHub.
2. **Create app** → repo `MyProPicks`, branch `main`, main file `dashboard/app.py`.
3. **Advanced settings** → Python **3.13**, and paste into **Secrets** (or, for an app that's
   already running: ⋮ → **Settings** → **Secrets**):
   ```toml
   [github]
   token = "your-fine-grained-token"
   repo = "your-github-username/MyProPicks"
   data_repo = "your-github-username/MyProPicks-data"
   branch = "main"

   [app]
   password = "choose-a-long-password"
   ```
4. Deploy. Without `data_repo`, the app refuses to save trades or capital rather than put
   them in the code repo. Without `password`, the private pages stay closed.

### 4. Check the review Action
Repo → **Actions** → *Monthly review* → **Run workflow** once to confirm it works. The first
run takes about 40 minutes; later runs reuse cached data.

### 5. Making the code repo public
Only after the steps above are done: repo **Settings** → **Danger zone** → **Change
visibility** → **Public**. Your trades and capital were never committed to it, so its history
holds nothing private.

## Things to know
- **Private pages:** *My holdings & P&L*, *Log a trade* and *Settings & review* ask for the
  password once per browser session. The **Lock** button in the sidebar locks them again.
- **Logging a trade** commits `data/trades.csv` to the data repo, not this one, so the app
  doesn't reload.
- **Sleep:** free apps go to sleep after a few days without visits; opening the link wakes it
  in under a minute.
- **Yahoo Finance** occasionally limits requests from cloud servers. If a review shows many
  fetch failures, run it again from the Actions tab.
- **Your PC copy:** trades logged in the cloud are in the data repo. To use them on your PC,
  copy `data/trades.csv` and `data/capital.yaml` from `MyProPicks-data` into this folder's
  `data/` (both are git-ignored here). Run `git pull` to get the latest reviews.
- The Windows scheduled task (`scripts/install_monthly_task.ps1`) isn't needed any more.
