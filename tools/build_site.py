"""Render Markdown docs as standalone, browsable HTML pages.

    python tools/build_site.py

Generates HTML pages for entries in PAGES whose source Markdown exists. Generated
HTML outputs are local/not tracked when listed in .gitignore.

Optional local-only pages can be listed in an untracked `local-pages.json` (same keys as PAGES,
paths relative to the repo root). Public pages never link to them.

Each page gets a sticky, filterable contents panel, light/dark styling, and "- [ ]" checklist items
become tick boxes whose state is remembered in the browser (localStorage).
Requires: pip install markdown
"""
from html import escape
from pathlib import Path
import json
import os
import re

import markdown

ROOT = Path(__file__).resolve().parent.parent

PAGES = [
    dict(src=ROOT / 'docs' / 'build-guide.md', out=ROOT / 'index.html',
         title='Dare Careers Dashboard Build Guide', menu='Build guide',
         eyebrow='Dare Careers · Power BI Dashboard Lab',
         lede='Load, model, build and polish the learner-progress dashboard in Power BI Desktop '
              '(October 2026 release). Expected values for every measure are in the data dictionary.'),
    dict(src=ROOT / 'docs' / 'issues-and-fixes.md', out=ROOT / 'fixes.html',
         title='Issues, Fixes & Report Update', menu='Issues & fixes',
         eyebrow='Dare Careers · Review of 21 Nov 2026',
         lede='Every issue found in the data, model and report, how each was fixed, and the '
              'step-by-step procedure (including the data reload) to update the existing Power BI report.'),
    dict(src=ROOT / 'docs' / 'update-existing-report.md', out=ROOT / 'update.html',
         title='Update the Existing Report', menu='Update the report',
         eyebrow='Power BI Desktop 2.159 · October 2026',
         lede='Click-by-click: move measures, replace queries, reload and check the data, fix the model, '
              'paste the corrected DAX, reconnect visuals, polish and verify.'),
    dict(src=ROOT / 'docs' / 'transformation-walkthrough.md', out=ROOT / 'walkthrough.html',
         title='Transformation Walkthrough', menu='Raw → report walkthrough',
         eyebrow='Power BI Desktop 2.159 · October 2026',
         lede='Every transformation from the raw CSV and Excel files to the report pages: each Power Query '
              'step, the model, derived columns, every DAX measure, and a 10-minute demo script for the reviewer.'),
    dict(src=ROOT / 'docs' / 'final-report.md', out=ROOT / 'report.html',
         title='Final Report', menu='Final report',
         eyebrow='Dare Careers · Learner Progress pipeline',
         lede='Sources, pipeline, transformations, semantic model, report pages, data-quality checks and '
              'deliverables, in one short report.'),
]
PUBLIC = len(PAGES)
_local = ROOT / 'local-pages.json'
if _local.exists():
    for _pg in json.loads(_local.read_text(encoding='utf-8')):
        PAGES.append({**_pg, 'src': ROOT / _pg['src'], 'out': ROOT / _pg['out'], 'local': True})

CSS = """
:root{--bg:#f4f7fb;--paper:#fff;--ink:#142033;--muted:#556274;--line:#d9e2ee;--accent:#0f766e;
--accent-soft:#e6f4f2;--code-bg:#eef2f7;--pre-bg:#0f172a;--pre-ink:#e6edf3;--warn:#fff7e6;--warn-line:#f0c36d}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d1420;--paper:#152033;--ink:#e5ecf5;
--muted:#9fb0c6;--line:#2a3a52;--accent:#2dd4bf;--accent-soft:#12312f;--code-bg:#1e2b40;--pre-bg:#0a0f18;
--warn:#2e2614;--warn-line:#7a5d1f}}
:root[data-theme="dark"]{--bg:#0d1420;--paper:#152033;--ink:#e5ecf5;--muted:#9fb0c6;--line:#2a3a52;
--accent:#2dd4bf;--accent-soft:#12312f;--code-bg:#1e2b40;--pre-bg:#0a0f18;--warn:#2e2614;--warn-line:#7a5d1f}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 "Segoe UI",system-ui,sans-serif}
a{color:var(--accent);text-underline-offset:2px}
header{background:linear-gradient(120deg,#10213a,#123c5a 60%,#0f5f73);color:#fff;padding:40px 16px 32px}
header .in{max-width:1240px;margin:auto}header .eb{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:#cfe7ef;font-weight:700}
.menu{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px;position:static;background:none;border:0;padding:0;max-height:none;overflow:visible;border-radius:0}.menu a{display:inline-block;color:#fff;text-decoration:none;font-size:.88rem;padding:6px 12px;border:1px solid rgba(255,255,255,.3);border-radius:999px;background:rgba(255,255,255,.08)}
.menu a:hover{background:rgba(255,255,255,.2)}.menu a.cur{background:#fff;color:#10213a;font-weight:600}.menu small{opacity:.75}
header h1{margin:.3em 0 .2em;font-size:clamp(1.8rem,4.5vw,2.8rem);line-height:1.15}header p{max-width:860px;color:#dbeaf0;margin:0}
.layout{max-width:1240px;margin:auto;padding:20px 16px;display:grid;grid-template-columns:270px minmax(0,1fr);gap:24px;align-items:start}
nav{position:sticky;top:12px;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:14px;max-height:calc(100vh - 24px);overflow:auto}
nav input{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit;margin-bottom:8px}
nav a{display:block;padding:4px 8px;border-radius:6px;text-decoration:none;font-size:.9rem;color:var(--ink)}
nav a:hover,nav a.on{background:var(--accent-soft);color:var(--accent)}
nav .tools{display:flex;gap:6px;margin-top:10px}nav button{flex:1;font:inherit;font-size:.8rem;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);cursor:pointer}
main{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:8px 32px 32px;min-width:0}
h2{margin-top:2em;padding-top:.6em;border-top:1px solid var(--line);font-size:1.45rem}h2:first-of-type{border-top:0}
h3{margin-top:1.6em;font-size:1.12rem}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.92rem;display:block;overflow-x:auto}
main img{display:block;max-width:100%;height:auto;margin:16px 0 4px;border:1px solid var(--line);border-radius:10px;background:#fff}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}th{background:var(--accent-soft)}
code{background:var(--code-bg);padding:.1em .35em;border-radius:5px;font-size:.88em;font-family:Consolas,ui-monospace,monospace}
pre{background:var(--pre-bg);color:var(--pre-ink);padding:14px 16px;border-radius:10px;overflow:auto;font-size:.86rem;line-height:1.5}
pre code{background:none;padding:0;color:inherit}
blockquote{margin:14px 0;padding:10px 16px;background:var(--warn);border-left:4px solid var(--warn-line);border-radius:6px}
blockquote p{margin:.3em 0}
li.task{list-style:none;margin-left:-1.3em}li.task input{margin-right:8px;transform:scale(1.15);accent-color:var(--accent)}
li.task.done label{color:var(--muted);text-decoration:line-through}
details{border:1px solid var(--line);border-radius:10px;padding:8px 14px;margin:10px 0;background:var(--bg)}
details[open]{background:var(--paper)}summary{cursor:pointer;font-weight:600}
.progress{font-size:.85rem;color:var(--muted);margin:6px 0 0}
footer{max-width:1240px;margin:auto;padding:4px 16px 28px;color:var(--muted);font-size:.85rem}
@media (max-width:900px){.layout{grid-template-columns:minmax(0,1fr)}nav{position:static;max-height:none}main{padding:4px 16px 24px}}
@media print{nav,header .eb{display:none}.layout{display:block}main{border:0}}
"""

JS = """
(function(){
  var key='chk:'+location.pathname, saved={};
  try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
  var boxes=[].slice.call(document.querySelectorAll('li.task input'));
  function progress(){var n=boxes.filter(function(b){return b.checked}).length;
    var el=document.getElementById('progress'); if(el) el.textContent=boxes.length?('Checklist: '+n+' / '+boxes.length+' ticked'):'';}
  boxes.forEach(function(b,i){b.checked=!!saved[i];b.parentNode.classList.toggle('done',b.checked);
    b.addEventListener('change',function(){saved[i]=b.checked;b.parentNode.classList.toggle('done',b.checked);
      try{localStorage.setItem(key,JSON.stringify(saved))}catch(e){} progress();});});
  progress();
  var reset=document.getElementById('reset'); if(reset) reset.onclick=function(){saved={};boxes.forEach(function(b){b.checked=false;b.parentNode.classList.remove('done')});
    try{localStorage.removeItem(key)}catch(e){} progress();};
  var q=document.getElementById('q'), links=[].slice.call(document.querySelectorAll('nav a[href^="#"]'));
  q.addEventListener('input',function(){var t=q.value.toLowerCase();links.forEach(function(a){
    var s=document.getElementById(a.getAttribute('href').slice(1)), body='';
    for(var n=s&&s.nextElementSibling;n&&n.tagName!=='H2';n=n.nextElementSibling) body+=n.textContent;
    a.style.display=(!t||a.textContent.toLowerCase().indexOf(t)>-1||body.toLowerCase().indexOf(t)>-1)?'':'none';});});
  var theme=document.getElementById('theme'); theme.onclick=function(){var r=document.documentElement;
    var dark=r.getAttribute('data-theme')==='dark'||(!r.getAttribute('data-theme')&&matchMedia('(prefers-color-scheme: dark)').matches);
    r.setAttribute('data-theme',dark?'light':'dark');};
  var heads=links.map(function(a){return document.getElementById(a.getAttribute('href').slice(1))}).filter(Boolean);
  if('IntersectionObserver' in window){var ob=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)
    links.forEach(function(a){a.classList.toggle('on',a.getAttribute('href')==='#'+e.target.id)})})},{rootMargin:'-10% 0px -80% 0px'});
    heads.forEach(function(h){ob.observe(h)});}
})();
"""


def rewrite_links(html: str, src: Path, out: Path) -> str:
    """Make relative links and image paths in the Markdown work from the output page's folder."""
    def fix(m):
        attr, href = m.group(1), m.group(2)
        if re.match(r'^(#|[a-z]+:|/)', href):
            return m.group(0)
        path, _, frag = href.partition('#')
        target = (src.parent / path).resolve()
        for pg in PAGES:  # a link to another guide's Markdown goes to its HTML page
            if target == pg['src'].resolve():
                target = pg['out'].resolve()
        rel = os.path.relpath(target, out.parent).replace(os.sep, '/')
        return f'{attr}="{rel}{"#" + frag if frag else ""}"'
    return re.sub(r'\b(href|src)="([^"]+)"', fix, html)


def tasks(html: str) -> str:
    """Turn GitHub-style '[ ]' / '[x]' list items into tick boxes."""
    def box(m):
        checked = ' checked' if m.group(1).lower() == 'x' else ''
        return f'<li class="task"><label><input type="checkbox"{checked}>'
    html = re.sub(r'<li>\s*(?:<p>)?\[([ xX])\]\s*', box, html)
    return re.sub(r'(<li class="task"><label><input[^>]*>)(.*?)</li>', r'\1\2</label></li>', html, flags=re.S)


def menu(current: dict) -> str:
    """Links to the generated pages, relative to the current page. Local-only pages are linked only
    from other local-only pages, so nothing committed points at them."""
    items = []
    for pg in PAGES if current.get('local') else PAGES[:PUBLIC]:
        if not pg['src'].exists():
            continue
        href = os.path.relpath(pg['out'], current['out'].parent).replace(os.sep, '/')
        label = escape(pg['menu']) + (' <small>(private)</small>' if pg.get('local') else '')
        cls = ' class="cur" aria-current="page"' if pg is current else ''
        items.append(f'<a href="{href}"{cls}>{label}</a>')
    return '<nav class="menu" aria-label="Guides">' + ''.join(items) + '</nav>'


def render(page: dict) -> None:
    src, out = page['src'], page['out']
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'md_in_html', 'sane_lists'],
                           extension_configs={'toc': {'permalink': False}})
    text = src.read_text(encoding='utf-8-sig')
    text = re.sub(r'\A# .*\n', '', text)  # page header replaces the H1
    body = tasks(rewrite_links(md.convert(text), src, out))
    def flat(tokens):
        for t in tokens:
            yield t
            yield from flat(t.get('children', []))
    nav = ''.join(f'<a href="#{t["id"]}">{escape(t["name"])}</a>' for t in flat(md.toc_tokens) if t['level'] == 2)
    out.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(page['title'])}</title><style>{CSS}</style></head>
<body><header><div class="in"><div class="eb">{escape(page['eyebrow'])}</div><h1>{escape(page['title'])}</h1>
<p>{escape(page['lede'])}</p>{menu(page)}</div></header>
<div class="layout"><nav aria-label="Contents"><input id="q" type="search" placeholder="Filter sections…" aria-label="Filter sections">
{nav}<div class="tools"><button id="theme" type="button">Light / dark</button><button id="reset" type="button">Reset ticks</button></div>
<p class="progress" id="progress"></p></nav>
<main>{body}</main></div>
<footer>Generated from {escape(os.path.relpath(src, ROOT).replace(os.sep, '/'))} by tools/build_site.py. Edit the Markdown, not this file.</footer>
<script>{JS}</script></body></html>
""", encoding='utf-8')
    print(f'wrote {os.path.relpath(out, ROOT)}')


if __name__ == '__main__':
    for p in PAGES:
        if p['src'].exists():
            render(p)
        else:
            print(f'skip {os.path.relpath(p["src"], ROOT)} (not found)')
