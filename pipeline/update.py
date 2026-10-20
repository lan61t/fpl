"""One command that refreshes everything: download -> model A -> model B + calibration -> data.json -> index.html.
Usage:  python pipeline/update.py            (full refresh, downloads fresh FPL data)
        python pipeline/update.py --no-fetch (rebuild from data already in data/raw)"""
import subprocess, sys, pathlib
here=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(here))
import fetch
from fplcfg import *
if '--no-fetch' not in sys.argv:
    cur,gw0=fetch.fetch_live(); fetch.fetch_season(PREV)
    print(f'downloaded: data through GW{cur}, next open gameweek GW{gw0}')
for script in ['model.py','model2.py','export.py','build_site.py','snapshot.py']:
    print('>',script); subprocess.run([sys.executable,str(here/script)],check=True,cwd=str(here))
import shutil
node=shutil.which('node')
if node:
    print('> paper_manager.js'); subprocess.run([node,str(here/'paper_manager.js')],check=True,cwd=str(here))
else: print('node not found: skipping the paper manager')
print('> track.py'); subprocess.run([sys.executable,str(here/'track.py')],check=True,cwd=str(here))
print('done')
