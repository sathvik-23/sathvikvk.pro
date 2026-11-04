from pathlib import Path
from html.parser import HTMLParser
import json, re, zipfile

ROOT=Path(__file__).resolve().parents[2]
CONTENT=ROOT/'portfolio-rebuild'
class Markdown(HTMLParser):
    def __init__(self): super().__init__(); self.out=[]; self.href=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a': self.out.append('['); self.href.append(dict(attrs).get('href',''))
        elif tag in {'p','ul','ol','blockquote'}: self.out.append('\n\n')
        elif tag=='li': self.out.append('\n- ')
        elif tag in {'strong','b'}: self.out.append('**')
        elif tag in {'em','i'}: self.out.append('*')
    def handle_endtag(self,tag):
        if tag=='a': self.out.append(']('+self.href.pop()+')')
        elif tag=='p': self.out.append('\n\n')
        elif tag in {'strong','b'}: self.out.append('**')
        elif tag in {'em','i'}: self.out.append('*')
    def handle_data(self,text): self.out.append(text)
def text(html):
    parser=Markdown();parser.feed(html);return re.sub(r'\n{3,}','\n\n',''.join(parser.out)).strip()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value)

screens=json.loads((CONTENT/'screens.json').read_text()); journal=json.loads((CONTENT/'journal.json').read_text())
for kind,items in [('screens',screens),('journal',journal['articles'])]:
    for item in items:
        result='# '+item['title']+'\n\nEditorial draft updated 4 November 2026. Publication date: none.\n\n'
        if 'recommendation' in item: result+='Provisional assessment: '+item['recommendation']+'\n\n'
        result+=item['summary']+'\n\n'
        for section in item['sections']: result+='## '+section['heading']+'\n\n'+text(section['html'])+'\n\n'
        if 'diagram' in item:
            diagram=item['diagram'];result+='## '+diagram['title']+'\n\n'+diagram['caption']+'\n\n'
            for i,step in enumerate(diagram['steps']): result+=f'{i+1}. {step["title"]}: {step["detail"]}\n'
        if 'proposedTest' in item:
            result+='## Proposed tests not run\n\n'+'\n'.join('- '+x for x in item['proposedTest'])+'\n\n'
        result+='\n## Sources\n\n'+'\n'.join('- ['+s['title']+']('+s['url']+') · '+s.get('type','source') for s in item['sources'])+'\n'
        save(CONTENT/'drafts'/kind/(item['slug']+'.md'),result)
calendar='# Forward editorial calendar\n\nPrepared 4 November 2026. All entries are planned future work. The four current drafts are separate from this calendar.\n\n| Planned date | Research question | Theme | Status |\n|---|---|---|---|\n'
for row in journal['calendar']: calendar+=f'| {row["date"]} | {row["title"]} | {row["theme"]} | Planned |\n'
save(CONTENT/'EDITORIAL-CALENDAR.md',calendar)
summary='# Editorial review\n\nThe local preview is http://127.0.0.1:4173/. This review bundle contains unpublished drafts and is not a production upload.\n\n## Featured company recommendations\n\n'
for s in screens[:3]: summary+='### '+s['title']+'\n\n'+s['recommendation']+' — '+s['summary']+'\n\n[Full draft](drafts/screens/'+s['slug']+'.md)\n\n'
summary+='## Additional private drafts\n\nTraza (Investigate) and MetisJean (Watch) remain private unless separately approved.\n\n## Journal drafts\n\n'
for a in journal['articles']: summary+='### '+a['title']+'\n\n'+a['summary']+'\n\n[Full draft](drafts/journal/'+a['slug']+'.md)\n\n'
summary+='## Release approval\n\nThe supplied brief requires Sathvik review before these recommendations become his public judgments. No approval is recorded. Production compilation refuses unapproved featured screens or articles. After explicit approval, record only the approved IDs and approval date, build and verify the release output, then deploy through the existing Vercel project and check the real domain.\n'
save(CONTENT/'EDITORIAL-REVIEW.md',summary)

if '--package' in __import__('sys').argv:
    bundle=ROOT/'Sathvik_VK_Portfolio_Review_2026-11-04.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as archive:
        include=[ROOT/'preview-site',CONTENT/'drafts',ROOT/'resume',ROOT/'output/playwright',ROOT/'output/qa-resume',ROOT/'site/tools',ROOT/'site/view',ROOT/'site/public-assets']
        include += [ROOT/'site'/name for name in ['portfolio.css','research-v3.js','site-config.js','favicon.svg','social-card.png','.gitignore','.vercelignore']]
        include+=[p for p in CONTENT.iterdir() if p.is_file() and p.suffix in {'.md','.json','.log'}]
        for item in include:
            for p in ([item] if item.is_file() else sorted(item.rglob('*'))):
                if p.is_file() and '__pycache__' not in p.parts and 'Defense' not in p.name: archive.write(p,str(p.relative_to(ROOT)))
    print(bundle)
