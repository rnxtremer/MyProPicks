# Deploying MyProPicks to Streamlit Community Cloud (free)

## How it works in the cloud

| Piece | Where it runs |
|---|---|
| Dashboard | Streamlit Community Cloud, from your **private** GitHub repo |
| Monthly review | A GitHub Action (`.github/workflows/review.yml`), 08:00 IST on the 1st, or on demand |
| Your trades, capital, live ranks | Saved straight into the repo by the app, so they survive restarts |
| Review results | Committed to the repo by the Action; the app picks them up when it reloads |

Cloud mode switches on when the app finds a GitHub token in its secrets. Without one (on your
PC), everything works on local files exactly as before.

## One-time setup

### 1. Create a private repo and push
1. On github.com → **New repository** → name `MyProPicks` → **Private** → no README → Create.
2. Push this folder: `git remote add origin <repo-url>` then `git push -u origin main`.

### 2. Make a token the app can use
GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate new token:
- Repository access: **Only select repositories** → `MyProPicks`
- Permissions: **Contents: Read and write**, **Actions: Read and write**
- Copy the token. Never paste it into chat or commit it.

### 3. Deploy on Streamlit Community Cloud
1. Go to share.streamlit.io and sign in with GitHub.
2. **Create app** → *Deploy a public app from GitHub* → repo `MyProPicks`, branch `main`,
   main file `dashboard/app.py`.
3. **Advanced settings** → Python **3.13**, and paste into **Secrets**:
   ```toml
   [github]
   token = "your-fine-grained-token"
   repo = "your-github-username/MyProPicks"
   branch = "main"
   ```
4. Deploy. Because the repo is private, the app is private too: only people you invite
   (Settings → Sharing) can open it.

### 4. Check the review Action
Repo → **Actions** → *Monthly review* → **Run workflow** once to confirm it works. The first
run takes about 40 minutes; later runs reuse cached data.

## Things to know
- **Logging a trade** commits `data/trades.csv` to the repo. That makes the app reload once,
  which takes a few seconds.
- **Sleep:** free apps go to sleep after a few days without visits; opening the link wakes it
  in under a minute.
- **Yahoo Finance** occasionally limits requests from cloud servers. If a review shows many
  fetch failures, run it again from the Actions tab.
- **Your PC copy** is no longer the master: run `git pull` before using it locally, so you
  see trades logged in the cloud.
- The Windows scheduled task (`scripts/install_monthly_task.ps1`) isn't needed any more.
