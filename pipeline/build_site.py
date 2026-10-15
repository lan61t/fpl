"""Build index.html from src/template.html + src/logic.js, embedding data.json as an offline fallback copy."""
from fplcfg import *
src=ROOT/'src'
tpl=(src/'template.html').read_text(encoding='utf8')
logic=(src/'logic.js').read_text(encoding='utf8').replace("if(typeof module!=='undefined')module.exports","if(false)module.exports")
data=(ROOT/'data.json').read_text(encoding='utf8')
assert tpl.count('/*__DATA__*/null')==1 and '/*__LOGIC__*/' in tpl
body=tpl.replace('/*__DATA__*/null',data).replace('/*__LOGIC__*/',logic)
ICON="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%231d5fa8'/%3E%3Cpath d='M7 22l6-7 5 4 7-10' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E"
head=('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
      '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
      '<title>FPL Assistant</title><meta name="description" content="Weekly Fantasy Premier League helper: transfers, captain, lineup, chips and mini-league comparison.">'
      f'<link rel="icon" href="{ICON}"><style>body{{margin:0}}</style></head>\n<body>\n')
(ROOT/'index.html').write_text(head+body+'\n</body></html>\n',encoding='utf8')
print('index.html written:',round((ROOT/'index.html').stat().st_size/1024),'KB')
