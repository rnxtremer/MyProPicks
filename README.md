# MyProPicks

Your own monthly stock picks, built to work the way ProPicks does, across three portfolios: Nifty 20
(from the Nifty 100), Nifty Midcap 30 (from the Midcap 150) and Nifty Smallcap 50 (from the
Smallcap 250).

On the 1st of each month it ranks every stock in each NSE list. Eligibility follows NSE's
index rules, and the ranking uses five ProPicks-style Financial Health categories plus a
fair-value estimate. It then tells you which stocks to sell and which to buy. You place the
trades yourself, log them, and it tracks your profit and loss.

## Daily use
Open the dashboard:
```powershell
.venv\Scripts\streamlit.exe run dashboard\app.py
```
Or log trades from the command line (see below).

## Command line
```powershell
.venv\Scripts\python.exe -m mypropicks review
.venv\Scripts\python.exe -m mypropicks log --portfolio nifty20 --action BUY --symbol TCS --qty 10 --price 3450
.venv\Scripts\python.exe -m mypropicks status
```

## Monthly automatic run (one-time setup)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_monthly_task.ps1
```

## Settings
Edit `config.yaml` to set your capital per portfolio, the category weights and the liquidity
floors, or set capital in the dashboard's Settings page.

## How the ranking works
See `docs/design.md`, sections 6.2a–6.2c.

_Rules-based ranking for personal research. Not investment advice. No returns are guaranteed._
