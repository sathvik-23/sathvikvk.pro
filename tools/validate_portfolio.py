from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
import argparse,json,re,sys,subprocess

parser=argparse.ArgumentParser(); parser.add_argument('output',type=Path); args=parser.parse_args(); root=args.output.resolve()
errors=[]; checks=0
def check(ok,message):
    global checks
    checks+=1
    if not ok: errors.append(message)
class Document(HTMLParser):
    def __init__(self,path):
        super().__init__(); self.links=[]; self.ids=set(); self.path=path; self.heading=0; self.canonical=[]; self.lang=None; self.frames=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='html': self.lang=a.get('lang')
        if tag=='h1': self.heading+=1
        if 'id' in a:
            check(a['id'] not in self.ids,f'Duplicate HTML id {self.path}: {a["id"]}'); self.ids.add(a['id'])
        if tag=='a':
            check(bool(a.get('href')),f'Empty anchor {self.path}'); self.links.append(a.get('href',''))
        if tag in {'script','img','iframe'} and a.get('src'): self.links.append(a['src'])
        if tag=='iframe': check(bool(a.get('title')),f'Iframe lacks title {self.path}')
        if tag=='link' and a.get('href'):
            if a.get('rel')=='canonical': self.canonical.append(a['href'])
            else: self.links.append(a['href'])

data=json.loads((root/'data/research-universe.json').read_text()); records=data['records']
check(data['schemaVersion']=='3.0','Wrong dataset version')
check(len({c['id'] for c in records})==len(records),'Duplicate company IDs')
eligible=[c for c in records if c['editorialStatus']=='published' and c['roundHistory'][-1]['normalizedStage'] in {'pre-seed','seed'}]
for c in records:
    for field in ['id','website','theme','product','buyer','roundHistory','hq','operatingLocations','regions','regionRationale','conflicts','qualificationNotes','reviewed','relationship','assessment','editorialStatus','eligibilityReason','evidence','alternatives','risk','nextEvidence','sources']:
        check(field in c,f'Missing {field}: {c["id"]}')
    check(c['theme'] in {'context','deployment','workflows'},f'Unknown theme {c["id"]}')
    check(c['assessment'] in {None,'Investigate','Watch','Pass'},f'Invalid assessment {c["id"]}')
    check(c['relationship']=='public_research_only',f'Unsubstantiated relationship {c["id"]}')
    check(set(c['regions']).issubset({'India','UAE','Europe','USA'}),f'Invalid region {c["id"]}')
    check(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',c['reviewed'])),f'Invalid reviewed date {c["id"]}')
    source_ids={s['id'] for s in c['sources']}
    check(len(source_ids)==len(c['sources']),f'Duplicate sources {c["id"]}')
    for s in c['sources']: check(urlparse(s['url']).scheme=='https',f'Invalid source {s["url"]}')
    for r in c['roundHistory']:
        check(r['normalizedStage'] in {'pre-seed','seed',None},f'Invalid stage {c["id"]}')
        check(set(r['sourceIds']).issubset(source_ids),f'Broken round/source references {c["id"]}')
        check(r['amount'] is None or isinstance(r['amount'],(int,float)),f'Non-numeric round {c["id"]}')
    if c.get('screenUrl'):
        target=root/c['screenUrl']; check(target.exists(),f'Screen missing {c["id"]}')
        if target.exists():
            html=target.read_text(); check(c['name'] in html,f'Screen identity mismatch {c["id"]}'); check(c['assessment'] in html,f'Screen assessment mismatch {c["id"]}')
check(next(c for c in records if c['id']=='us-supermemory')['roundHistory'][-1]['amount'] is None,'Supermemory conflict was erased')
for cid in ['ae-qanooni','eu-cognee']: check(next(c for c in records if c['id']==cid) not in eligible,f'Conflict hold counted {cid}')
docs={}
for path in root.rglob('*.html'):
    doc=Document(path.relative_to(root)); doc.feed(path.read_text()); docs[path.resolve()]=doc
    check(doc.lang=='en',f'Language missing {path}')
    check(len(doc.canonical)==1,f'Canonical missing/duplicate {path}')
    check(not re.search(r'YOUR_|NO UNFINISHED READ LINKS|RESEARCH_UNIVERSE|data\.js',path.read_text()),f'Legacy residue {path}')
    if 'http-equiv="refresh"' not in path.read_text(): check(doc.heading==1,f'H1 count {path}: {doc.heading}')
for path,doc in docs.items():
    for href in doc.links:
        url=urlparse(href)
        if url.scheme in {'http','https','mailto','tel'}: continue
        check(not url.scheme,f'Unsafe scheme {path}: {href}')
        target=(root/unquote(url.path).lstrip('/') if url.path.startswith('/') else path.parent/unquote(url.path)).resolve() if url.path else path
        if target.is_dir(): target=target/'index.html'
        check(target.is_relative_to(root),f'Escaped public root {path}: {href}')
        check(target.exists(),f'Broken local route {path.relative_to(root)}: {href}')
        if url.fragment and target.suffix=='.html' and target in docs:
            check(url.fragment in docs[target].ids or url.fragment.startswith('page='),f'Broken fragment {path.relative_to(root)}: {href}')
for path in root.rglob('*'):
    if not path.is_file(): continue
    check(not re.search(r'Defense|\.bak$|pre-redesign|\.git|private|screens\.json|journal\.json|approval',str(path.relative_to(root)),re.I),f'Non-public file in build {path}')
    if path.suffix in {'.html','.json','.js'}: check('/Users/' not in path.read_text(),f'Local path exposed {path}')
home=(root/'index.html').read_text()
check(f'{len(eligible)} unique records' in home,'Homepage unique count mismatch')
for region in ['India','UAE','Europe','USA']:
    count=sum(region in c['regions'] for c in eligible)
    check(f'{region}<strong>{count}</strong>' in home,f'Region count mismatch {region}')
check('data.js' not in home,'Legacy browser data loaded')
check('Read PDF' not in home,'Unexpected homepage archive promotion')
for name in ['Sathvik_VK_Resume.pdf','Sathvik_VK_Resume.docx']: check((root/'resume'/name).exists(),f'Missing resume {name}')
report={'checks':checks,'errors':errors,'htmlPages':len(docs),'companies':len(records),'eligible':len(eligible),'holds':len(records)-len(eligible),'regions':{r:sum(r in c['regions'] for c in eligible) for r in ['India','UAE','Europe','USA']}}
print(json.dumps(report,indent=2)); sys.exit(bool(errors))
