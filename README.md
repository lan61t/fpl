# FPL Assistant

A weekly Fantasy Premier League helper that runs as a plain web page (no server, no login).
Enter your squad, bank and free transfers, and it suggests transfers, a lineup and captain, chip timing, and compares you with mini-league rivals.

**Live site:** https://lan61t.github.io/fpl/

## How the numbers update

A scheduled GitHub Actions job (`.github/workflows/update.yml`) runs every 3 hours:

1. downloads the official FPL data (players, fixtures, live gameweek stats) and last season's open data,
2. re-runs the model,
3. commits a fresh `data.json` and `index.html`, which GitHub Pages then serves.

The page reads `data.json` when it opens and every 30 minutes, and has a **Check for updates** button.
You can also run the job on demand: repository **Actions** tab, **Update FPL data**, **Run workflow**.
Your squad, bank and rivals are saved in your browser only. Use **Backup** on the About tab to move them to another device.

## The model in one paragraph

Expected points are 75% *Model B* (appearance, goals and assists from xG/xA, clean sheets, saves, bonus, defensive contribution, with a logistic minutes model) and 25% *Model A* (points per 90 x minutes x fixture), then calibrated per position against past results.
Backtests (walk-forward, every prediction made before the gameweek) showed this ranks players better than recent form; the biggest single gain came from the minutes model. See the About tab in the app for the numbers and the limits. Nothing here beats luck, and gains under about 2 expected points are within the noise.

## Run it yourself

```bash
pip install -r requirements.txt
python pipeline/update.py          # download + model + build (about 40 seconds)
python -m http.server 8000         # then open http://localhost:8000/
```

## Layout

| Path | What it is |
|---|---|
| `index.html`, `data.json` | The built site and its data (generated; do not edit by hand) |
| `src/template.html`, `src/logic.js` | The page and its logic (edit these) |
| `pipeline/` | `fetch.py`, `model.py`, `model2.py`, `export.py`, `build_site.py`; `update.py` runs them all |
| `data/calib.json`, `data/minutes_weights.json` | Fitted constants (calibration and minutes model), committed |

## At the start of a new season

1. In `pipeline/fplcfg.py` set `SEASON` and `PREV` (and append the finished season to `HIST_SEASONS`).
2. Run `python pipeline/train_minutes.py` once (downloads about 50 MB of history) and commit `data/minutes_weights.json`.
3. Run `python pipeline/update.py` and push.

## Credits and limits

Data: the official Fantasy Premier League API and the [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) historical dataset. Not affiliated with the Premier League or FPL.
The app cannot read your FPL account and does not know team news that is not in the FPL data; always check press conferences before a deadline.
