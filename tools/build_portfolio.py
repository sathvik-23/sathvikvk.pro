"""Render a review preview; release requires explicit editorial approval IDs."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
import argparse, json, math, re, shutil, hashlib, time

SITE = Path(__file__).resolve().parents[1]
PACKAGE = SITE.parent
CONTENT = PACKAGE / 'portfolio-rebuild'
DATE = '2026-11-04'
THEMES = {'context': 'Memory & context', 'deployment': 'Reliable deployment', 'workflows': 'Business workflows'}
REGIONS = ['India', 'UAE', 'Europe', 'USA']
CONFIG = dict(re.findall(r"(\w+): '([^']*)'", (SITE/'site-config.js').read_text()))
BASE = CONFIG['canonicalUrl'].rstrip('/')
EMAIL = CONFIG['email']
LINKEDIN = CONFIG['linkedin']
BOOKING = CONFIG.get('booking', 'https://cal.com/sathvik-vk-tv0tnw/30min')
E = lambda v: escape(str(v if v is not None else 'Unknown'), quote=True)

class SafeHTML(HTMLParser):
    tags = {'p','a','strong','b','em','i','ul','ol','li','code','blockquote','br','h3','h4','table','thead','tbody','tr','th','td','sup'}
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in {'script','style','iframe'}: self.skip+=1; return
        if self.skip or tag not in self.tags: return
        extra=''
        if tag=='a':
            href=dict(attrs).get('href','')
            if urlparse(href).scheme in {'http','https'}: extra=f' href="{E(href)}" rel="noopener noreferrer"'
        self.parts.append(f'<{tag}{extra}>')
    def handle_endtag(self,tag):
        if tag in {'script','style','iframe'}: self.skip=max(0,self.skip-1); return
        if not self.skip and tag in self.tags and tag!='br': self.parts.append(f'</{tag}>')
    def handle_data(self,data):
        if not self.skip: self.parts.append(E(data))

def safe_html(value):
    parser=SafeHTML(); parser.feed(value); return ''.join(parser.parts)

def load(name): return json.loads((CONTENT/name).read_text())
def write(path,text):
    dest=OUT/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(text)
def rel(path,depth=0): return '../'*depth+path
def button(text,path,secondary=False,download=False):
    return f'<a class="button{" secondary" if secondary else ""}" href="{E(path)}"{" download" if download else ""}>{E(text)} <span aria-hidden="true">{"↓" if download else "↗"}</span></a>'

def nav(depth,current):
    links=''.join(f'<a href="{rel(path,depth)}"'+(' aria-current="page"' if key==current else '')+f'>{label}</a>' for key,path,label in [('screens','screens.html','Screens'),('research','research.html','Research'),('journal','journal/','Journal'),('about','about.html','About'),('resume','resume/','CV')])
    links+=f'<a class="quiet-link" href="mailto:{E(EMAIL)}">Email ↗</a>'
    return f'<a class="skip" href="#main">Skip to content</a><div class="wrap"><header class="site-header"><a class="identity" href="{rel("index.html",depth)}">SATHVIK VK<span>PRE-SEED & SEED AI RESEARCH</span></a><nav class="desktop-nav" aria-label="Main navigation">{links}</nav><details class="mobile-menu"><summary>Menu</summary><nav aria-label="Mobile navigation">{links}</nav></details></header></div>'

def footer(depth):
    return f'<div class="wrap"><footer class="site-footer"><div class="footer-main"><div><strong>Sathvik VK</strong><div class="small">Bengaluru · Pre-seed & Seed AI Research</div></div><div class="footer-links"><a href="mailto:{E(EMAIL)}">Email</a><a href="{E(LINKEDIN)}">LinkedIn ↗</a><a href="{rel("resume/",depth)}">CV</a><a href="{E(BOOKING)}">Book a conversation ↗</a></div></div><p class="method">Independent public-source research. Round labels describe the last located announcement; evidence, company claims and analytical judgments are distinguished in each record. <a href="{rel("methodology.html",depth)}">Methodology</a> · <a href="{rel("archive.html",depth)}">Research archive</a></p></footer></div>'

def page(title,description,route,body,depth=0,current=''):
    banner='<div class="review-banner">LOCAL REVIEW PREVIEW · Company screens and journal articles are editorial drafts awaiting Sathvik’s review.</div>' if PREVIEW else ''
    return f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} — Sathvik VK</title><meta name="description" content="{E(description)}"><link rel="canonical" href="{BASE}/{route}"><meta property="og:title" content="{E(title)} — Sathvik VK"><meta property="og:description" content="{E(description)}"><meta property="og:type" content="website"><meta property="og:url" content="{BASE}/{route}"><meta property="og:image" content="{BASE}/social-card.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">'+('<meta name="robots" content="noindex,nofollow">' if PREVIEW else '')+f'<link rel="icon" href="{rel("favicon.svg",depth)}"><link rel="stylesheet" href="{rel("portfolio.css",depth)}"></head><body>{banner}{nav(depth,current)}<main id="main" class="wrap">{body}</main>{footer(depth)}</body></html>'

def round_of(c): return c['roundHistory'][-1]
def stage(c): return round_of(c).get('originalLabel') or 'Unknown'
def date(c): return round_of(c).get('announcementDate') or 'Unknown'
def geography(c):
    hq=c.get('hq') or {}
    if hq: return ', '.join(str(x) for x in [hq.get('city'),hq.get('country')] if x)+' · reported HQ'
    locations=c.get('operatingLocations',[])
    if locations:
        p=locations[0]
        return ', '.join(str(x) for x in [p.get('city'),p.get('country')] if x)+' · '+p.get('locationType','operating presence').replace('_',' ')+'; HQ unverified'
    return 'Operating geography unverified'
def screen_card(s):
    c=BY_ID[s['id']]
    return f'<article class="screen-card"><div class="card-meta"><span class="tag">{E(stage(c))} · {E(c["regions"][0])}</span><span class="status {s["recommendation"].lower()}">{E(s["recommendation"])}</span></div><h3>{E(c["name"])}</h3><p class="question">{E(s["question"])}</p><dl><dt>Evidence</dt><dd>{E(s["strongestEvidence"])}</dd><dt>Open question</dt><dd>{E(s["biggestUnknown"])}</dd></dl><a class="card-link" href="screens/{s["slug"]}.html">Read the screen ↗</a><p class="small">{"Draft assessment" if PREVIEW else "Assessment"} · Reviewed {E(s["reviewed"])}<br>Public research · {E(THEMES[s["theme"]])}</p></article>'

def article_card(a):
    steps=a.get('diagram',{}).get('steps',[])[:3]
    mini='<div class="mini-diagram" aria-hidden="true">'+'<b>→</b>'.join(f'<span>{E(x["title"])}</span>' for x in steps)+'</div>'
    return f'<article class="note-card">{mini}<span class="tag">{E(THEMES[a["theme"]])} · {reading_time(a)} min read</span><h3><a href="journal/{a["slug"]}.html">{E(a["title"])}</a></h3><p>{E(a["summary"])}</p><a href="journal/{a["slug"]}.html">Read {"draft" if PREVIEW else "article"} ↗</a><p class="small">{"Draft updated" if PREVIEW else "Published"} {E(a.get("published") or a["updated"])}</p></article>'

def reading_time(item):
    words=re.sub('<[^>]+>',' ', ' '.join(x['html'] for x in item['sections']))
    return max(1,math.ceil(len(words.split())/220))

def sources_html(sources):
    return '<ol class="source-list">'+''.join(f'<li><a href="{E(s["url"])}">{E(s.get("title",s["url"]))}</a> <span class="small">· {E(s.get("type","primary source")).replace("_"," ")}</span></li>' for s in sources)+'</ol>'

def diagram(d):
    return '<figure class="diagram"><h3>'+E(d['title'])+'</h3><ol>'+''.join(f'<li><div><strong>{E(s["title"])}</strong>{E(s["detail"])}</div></li>' for s in d['steps'])+'</ol><figcaption>'+E(d['caption'])+'</figcaption></figure>'

def write_detail(item,is_screen=True):
    c=BY_ID[item['id']] if is_screen else None
    route=f'{"screens" if is_screen else "journal"}/{item["slug"]}.html'
    summary=item['summary']; sections=item['sections']; label='Company screen' if is_screen else 'Journal'
    intro=f'<section class="page-hero"><p class="eyebrow">{label} · {E(THEMES[item["theme"]])}</p>'
    if PREVIEW: intro+='<p class="editorial-status">Editorial draft · provisional analysis for review</p>'
    intro+=f'<h1>{E(item["title"])}</h1><p class="intro">{E(item.get("question",summary))}</p></section>'
    if is_screen:
        intro=intro.replace('</section>',f'<p class="status">{E(item["recommendation"])} · {E(stage(c))} · Evidence reviewed {E(item["reviewed"])}</p></section>')
    sidebar='<aside class="reading-sidebar" aria-label="Article summary"><dl>'
    if is_screen:
        for k,v in [('Assessment',item['recommendation']),('Last disclosed round',stage(c)),('Announcement',date(c)),('Geography',geography(c))]: sidebar+=f'<dt>{k}</dt><dd>{E(v)}</dd>'
    sidebar+=f'<dt>{"Evidence reviewed" if is_screen else "Draft updated" if PREVIEW else "Published"}</dt><dd>{E(item.get("published") or item.get("reviewed") or item.get("updated"))}</dd><dt>Reading time</dt><dd>{reading_time(item)} minutes</dd></dl><nav aria-label="On this page">'
    sidebar+=''.join(f'<a href="#{E(s["id"])}">{E(s["heading"])}</a>' for s in sections)
    sidebar+='<a href="#sources">Sources</a></nav></aside>'
    body=f'<div class="reading"><div class="summary-box"><p class="eyebrow">{E(item["recommendation"])+" · provisional conclusion" if is_screen else "Conclusion"}</p><p>{E(summary)}</p></div>'
    if not is_screen: body+=diagram(item['diagram'])
    for s in sections: body+=f'<section id="{E(s["id"])}"><h2>{E(s["heading"])}</h2>{safe_html(s["html"])}</section>'
    if is_screen:
        tests=item.get('proposedTest',[])
        body+=diagram({'title':'Proposed evaluation · not run','caption':'This is a proposed diligence design. No results are claimed.','steps':[{'title':f'Step {i+1}','detail':t} for i,t in enumerate(tests)]})
    body+='<section id="sources"><h2>Source register</h2>'+sources_html(item['sources'])+'</section>'
    body+=f'<p><a href="../{"screens.html" if is_screen else "journal/"}">← Back to {"screens" if is_screen else "journal"}</a></p></div>'
    write(route,page(item['title'],summary,route,intro+f'<div class="reading-layout">{body}{sidebar}</div>',1,'screens' if is_screen else 'journal'))

def homepage():
    featured=SCREENS[:3]
    desk='<aside class="desk" aria-label="Research desk"><p class="eyebrow">Research desk / 2027 agenda</p><ol class="desk-list">'+''.join(f'<li><a href="themes.html#{k}"><span>0{i+1}</span>{v}</a></li>' for i,(k,v) in enumerate(THEMES.items()))+'</ol><p class="meta">Evidence reviewed<br><strong>4 November 2026</strong></p>'
    if featured: desk+=f'<div class="featured">Featured screen<a href="screens/{featured[0]["slug"]}.html">{E(BY_ID[featured[0]["id"]]["name"])}: {E(featured[0]["question"])} ↗</a></div>'
    desk+='</aside>'
    body='<section class="home-hero"><div><p class="eyebrow">Bengaluru · Pre-seed & Seed AI Research</p><h1>I study the founders turning AI capability into products customers rely on.</h1><p class="intro">Founder/operator based in Bengaluru, researching memory and context, reliable AI deployment and focused business workflows.</p><div class="actions">'+button('Read screens','screens.html')+button('About / CV','about.html',True)+'</div></div>'+desk+'</section>'
    body+='<section class="section"><div class="section-head"><div><p class="eyebrow">01 / Selected judgment</p><h2>Three companies. Three tests.</h2></div><p>Start with the conclusion, then inspect the evidence and the condition that would change the view.</p></div><div class="grid-three">'+''.join(screen_card(x) for x in featured)+'</div><p class="small">'+('Commissioned research drafts. Recommendations are provisional until editorial review.' if PREVIEW else 'Conditional research assessments, dated to the evidence reviewed.')+'</p></section>'
    themes=[('context','When is context worth a separate budget?','Look for permission-safe memory that improves a real task beyond simpler retrieval.'),('deployment','Can reliability become a product?','Look for tests that predict production failures and reduce the cost of a successful task.'),('workflows','Where does software own the work?','Look for repeated use, a clear buyer and manageable implementation and review costs.')]
    body+='<section class="section"><p class="eyebrow">02 / Where I look for an edge</p><h2>Scarcity moves as intelligence becomes abundant.</h2><div class="grid-three">'+''.join(f'<article class="theme-card"><div class="theme-no">0{i+1}</div><h3>{E(title)}</h3><p>{E(text)}</p><a href="themes.html#{key}">Explore {E(THEMES[key].lower())} →</a></article>' for i,(key,title,text) in enumerate(themes))+'</div></section>'
    body+='<section class="section"><div class="section-head"><div><p class="eyebrow">03 / Regional research</p><h2>Follow the evidence across markets.</h2></div><p>India is my relationship base. The UAE, Europe and USA are research coverage regions.</p></div><div class="regions">'+''.join(f'<a class="region-link" href="research.html?region={r}">{r}<strong>{sum(r in c["regions"] for c in ELIGIBLE)}</strong></a>' for r in REGIONS)+'</div>'
    for s in featured:
        c=BY_ID[s['id']]
        body+=f'<div class="company-preview"><div><strong><a href="research.html?q={E(c["name"])}">{E(c["name"])}</a></strong><span>{E(c["regions"][0])}</span></div><div>{E(stage(c))}<br><span>Announced {E(date(c))}</span></div><div>{E(c["nextEvidence"])}</div></div>'
    body+=f'<p class="coverage-note">{len(ELIGIBLE)} unique records in the published research pool. Counts exclude verification holds. Region membership can overlap. <a href="research.html">Explore the database →</a></p><p class="coverage-note">Coverage gap: no standalone memory company cleared both geography and stage evidence for India or UAE in the supplied research.</p></section>'
    body+='<section class="section"><p class="eyebrow">04 / From building to diligence</p><div class="operator-grid"><div class="operator-panel"><p class="eyebrow">Operator evidence / Perfstaq</p><h3>Where should the human approval sit?</h3><p>Perfstaq connects captured founder context with business workflows. Its public product surfaces make approvals part of taking an action.</p><a href="about.html#operator">Inspect the operator case →</a></div><div><h2>Build the workflow. Question the outcome.</h2><p>Working across AI product development, customer discovery and commercial iteration gives me a practical lens on integration effort, failure recovery and what the user still has to do.</p><p class="small">I attend startup events in Bengaluru and connect with founders through LinkedIn. Published company research here uses public sources.</p><a href="https://perfstaq.com/">Open the product artifact ↗</a></div></div></section>'
    body+='<section class="section"><div class="section-head"><div><p class="eyebrow">05 / Recent notes</p><h2>Arguments you can inspect.</h2></div><p>Research notes connect the product question to a testable business question.</p></div><div class="journal-grid">'+''.join(article_card(x) for x in ARTICLES[:2])+'</div><p><a href="journal/">Open the journal →</a></p></section>'
    body+='<section class="section contact"><div><p class="eyebrow">Start a conversation</p><h2>Have a difficult early-stage AI question?</h2><p>Let’s discuss the evidence, the unknowns and the next useful test.</p></div><div class="actions">'+button('Email Sathvik','mailto:'+EMAIL)+button('Book a conversation',BOOKING,True)+'</div></section>'
    write('index.html',page('Pre-seed & Seed AI Research','Sathvik VK studies founders turning AI capability into products customers rely on. Memory, reliable deployment and business workflows.','',body))

def research_page():
    body='<section class="page-hero"><p class="eyebrow">Research / public evidence</p><h1>The working universe.</h1><p class="intro">Explore companies by region, research theme and last disclosed round. Expand any record to inspect the evidence and the next diligence question.</p></section><section aria-label="Research filters"><nav class="research-tabs" id="region-tabs" aria-label="Research regions"></nav><form class="filters" id="research-filters"><label>Search<input type="search" id="query" name="q" placeholder="Company, product or buyer"></label><label>Theme<select id="theme" name="theme"><option value="">All themes</option>'+''.join(f'<option value="{k}">{v}</option>' for k,v in THEMES.items())+'</select></label><label>Last disclosed stage<select id="stage" name="stage"><option value="">All stages</option><option value="pre-seed">Pre-seed</option><option value="seed">Seed</option></select></label><label>Assessment<select id="assessment" name="assessment"><option value="">All assessments</option><option value="Investigate">Investigate</option><option value="Watch">Watch</option><option value="Pass">Pass</option><option value="Unassessed">Unassessed</option></select></label></form><div class="results-meta"><span id="result-count" role="status" aria-live="polite">Loading research…</span><button type="button" id="reset-filters">Clear filters</button></div><div class="research-head" aria-hidden="true"><span>Company / product</span><span>Theme / assessment</span><span>Last public round</span><span>Geography</span><span>Next evidence</span></div><div id="research-results"></div><div id="research-error" hidden class="error-state" role="alert"><h2>Research could not load.</h2><p>Please reload the page or <a href="data/research-universe.json">open the research JSON</a>.</p><button type="button" id="retry-load" class="button">Try again</button></div><noscript><p>The interactive database needs JavaScript. <a href="data/research-universe.json">Open the full structured dataset</a> or <a href="screens.html">read the static screens</a>.</p></noscript><p class="coverage-note">Overall counts use unique companies. Regional counts may overlap where operating evidence supports more than one membership; exact HQ and operating presence remain separate. Europe includes the UK.</p><p class="coverage-note">Company assessments are distinct from funding stage. An unassessed record is a factual research entry. The latest located announcement does not establish current private capitalization.</p><details class="queue"><summary id="queue-count">Verification queue</summary><p>Excluded from the main pool until the stated evidence gap is resolved.</p><ul id="verification-queue"></ul></details></section><section class="section"><h2>Download the evidence.</h2><p><a href="data/research-universe.json" download>Company dataset (JSON)</a> · <a href="data/source-register.json" download>Source register (JSON)</a> · <a href="archive.html">Historical DeepTech archive</a></p></section>'
    text=page('Research universe','Company research across India, UAE, Europe and USA, with sourced funding context and filters.','research.html',body,current='research').replace('</body>','<script src="research-v3.js" defer></script></body>')
    write('research.html',text)

def theme_pages():
    specs=[('context','Can memory earn a separate budget?','Product teams building assistants that work across people, changing facts and permission boundaries.','Longer-running workflows make stale context and fragmented state visible to users. More stored text is not automatically better context.','Temporal updates, deletion, provenance and access-aware retrieval can become durable value when measured against a simpler baseline.','Application state, ordinary retrieval and native model features may solve enough of the task for a lower total cost.','At pre-seed, test a narrow user problem and retrieval correctness. At seed, establish repeated use, deployment effort and willingness to pay.','A simpler system matches task success and permission safety at lower operating and integration cost.'),('deployment','Can evaluation become an operating advantage?','Engineering and QA teams shipping AI into customer-facing or commercially consequential work.','Agent behavior spans tools, state and retries. A plausible final answer does not establish that the requested action succeeded.','Evaluations tied to human judgments, incident prevention and the cost per successful task can earn an ongoing budget.','Model providers, open-source tools and in-house test suites may absorb the product. Dashboards without changed outcomes are vulnerable.','At pre-seed, compare a defined failure class with blinded human labels. At seed, establish production correlation and an owner who renews the budget.','The product cannot predict costly failures, or its value is reproducible using the customer’s existing stack.'),('workflows','Can software own a painful, repeated job?','The budget owner responsible for a specific process: banking operations, procurement or customer operations.','Models can perform more individual tasks; adoption still depends on trust, integration and the economics of the complete process.','Domain context, distribution, audit trails and repeated workflow use may support pricing and make replacement costly.','An incumbent can add the feature, or a service-heavy implementation consumes the supposed software margin.','At pre-seed, identify the buyer and observe the current work. At seed, inspect repeated use, payment, exception handling and deployment burden.','Repeat demand disappears after a pilot, or manual intervention and support erase customer ROI and contribution margin.')]
    body='<section class="page-hero"><p class="eyebrow">2027 research agenda</p><h1>Three questions worth following.</h1><p class="intro">The opportunity is a hypothesis. Each theme needs a buyer, a measurable advantage and a condition that would invalidate it.</p></section>'
    for i,(key,title,buyer,why,value,counter,evidence,kill) in enumerate(specs):
        body+=f'<section class="section theme-detail" id="{key}"><div><div class="theme-no">0{i+1}</div><p class="eyebrow">{THEMES[key]}</p><h2>{title}</h2><a href="research.html?theme={key}">Explore companies in this theme →</a></div><div>'
        for heading,text in [('Customer and buyer',buyer),('Why now',why),('Where value may accrue',value),('Strongest counterargument',counter),('Stage-appropriate evidence',evidence),('What invalidates the thesis',kill)]: body+=f'<h3>{heading}</h3><p>{text}</p>'
        related=[x for x in SCREENS if x['theme']==key]
        body+='<h3>Related screens</h3><p>'+' · '.join(f'<a href="screens/{x["slug"]}.html">{E(BY_ID[x["id"]]["name"])}</a>' for x in related)+'</p></div></section>'
    body+='<section class="section"><h2>Framework sources</h2><p>These investor and builder perspectives inform the questions; the theme conclusions above are analytical hypotheses. Model-provider APIs remain a valid implementation choice. Differentiation, data control, economics and portability need to be tested in the customer’s workflow.</p>'+sources_html(FRAMEWORKS)+'</section>'
    write('themes.html',page('Research themes','Memory, reliable deployment and business workflow investment hypotheses.','themes.html',body))

def about():
    body='<section class="page-hero"><p class="eyebrow">About / Bengaluru</p><h1>Founder experience.<br>Investment questions.</h1><p class="intro">I’m Sathvik VK, founder of Perfstaq and an operator moving into venture research. I focus on pre-seed and seed AI companies, particularly where product behavior, deployment constraints and business evidence meet.</p><div class="actions">'+button('View CV','resume/')+button('Email Sathvik','mailto:'+EMAIL,True)+'</div></section><section class="section operator-grid" id="operator"><div><p class="eyebrow">Operator case / Perfstaq</p><h2>From captured context to a reviewable action.</h2><p>Building a product sharpens the questions I ask about workflow boundaries, integration cost and failure recovery.</p><a href="https://perfstaq.com/">Inspect the public product ↗</a></div><dl class="operator-facts"><dt>Problem</dt><dd>Founder context arrives through conversations and notes, while the resulting work lives across separate business tools.</dd><dt>My action</dt><dd>Built and iterated AI product and workflow systems at Perfstaq across product design, AI tooling and commercial experimentation. The current public product presents captured context, workspace applications and action approvals.</dd><dt>Inspectable output</dt><dd><a href="https://perfstaq.com/">Perfstaq’s live product presentation</a> describes a Mac capture layer, business workspace and connected assistant actions. Product claims remain attributed to the product; this case does not establish independent performance results.</dd><dt>Evidenced result</dt><dd>A public, inspectable product artifact exists. Revenue, retention and customer outcome metrics are not established by that artifact.</dd><dt>Relevance to diligence</dt><dd>Ask where the human still intervenes, whether approvals protect meaningful actions, what integration costs and how a failed action is recovered.</dd></dl></section><section class="section operator-grid"><div><p class="eyebrow">Research practice</p><h2>Work close to the problem.</h2></div><div><p>I attend startup events in Bengaluru and connect with founders through LinkedIn. My published company coverage uses public sources; authorized conversation notes will identify their evidence separately.</p><p>My earlier DeepTech work includes a 48-company research universe, three screens and a CynLr scenario model. That work remains available as a historical exercise in the <a href="archive.html">research archive</a>.</p><p>My current questions concern memory and context, reliable AI deployment and business workflows. I turn those themes into company-specific tests and revise the view as evidence changes.</p></div></section><section class="section contact"><div><h2>Let’s discuss a company or a difficult product question.</h2><p><a href="mailto:'+EMAIL+'">'+EMAIL+'</a></p></div><div class="actions">'+button('Book a conversation',BOOKING)+button('View CV','resume/',True)+'</div></section>'
    write('about.html',page('About','Sathvik VK, founder of Perfstaq, based in Bengaluru and researching pre-seed and seed AI companies.','about.html',body,current='about'))

def auxiliary():
    body='<section class="page-hero"><p class="eyebrow">Research library</p><h1>Company screens.</h1><p class="intro">A specific company, a conditional conclusion and a proposed next test. Funding labels follow source disclosures.</p></section><section class="section"><div class="grid-three">'+''.join(screen_card(x) for x in SCREENS[:3])+'</div></section>'
    if len(SCREENS)>3: body+='<section class="section"><p class="eyebrow">Additional commissioned research drafts</p><div class="grid-three">'+''.join(screen_card(x) for x in SCREENS[3:])+'</div></section>'
    body+='<section class="section"><p><a href="archive.html">Earlier hardware and later-stage exercises →</a></p></section>'
    library=page('Investment screens','Conditional company research in context infrastructure, AI reliability and business workflows.','screens.html',body,current='screens')
    library=library.replace('</body>','<script>function routeLegacyScreen(){if(["#preseed","#seed","#seed-ai","#series-a"].includes(location.hash))location.replace("archive.html");}addEventListener("hashchange",routeLegacyScreen);routeLegacyScreen();</script></body>')
    write('screens.html',library)
    journal='<section class="page-hero"><p class="eyebrow">Journal / research arguments</p><h1>What would change the view?</h1><p class="intro">Four distinct arguments about what an early-stage AI business needs to prove.</p></section><section class="section"><div class="journal-grid">'+''.join(article_card(x).replace('href="journal/','href="') for x in ARTICLES)+'</div></section><section class="section"><h2>Next on the research desk.</h2><p>Planned fortnightly notes. These dates are a forward editorial calendar.</p><table class="calendar"><thead><tr><th>Planned date</th><th>Research question</th><th>Status</th></tr></thead><tbody>'+''.join(f'<tr><td>{E(x["date"])}</td><td>{E(x["title"])}</td><td>Planned</td></tr>' for x in CALENDAR)+'</tbody></table></section><section class="section"><a href="../archive.html">Historical DeepTech notes →</a></section>'
    write('journal/index.html',page('Journal','Research on memory businesses, successful task economics, paid pilots and pre-seed judgment.','journal/',journal,1,'journal'))
    resume='<section class="page-hero"><p class="eyebrow">CV / Sathvik VK</p><h1>Founder/operator.<br>Pre-seed & Seed AI Research.</h1><p class="intro">Selected investment research, operating background and contact details in one page.</p><div class="actions">'+button('View PDF','Sathvik_VK_Resume.pdf')+button('Download PDF','Sathvik_VK_Resume.pdf',True,True)+button('Editable DOCX','Sathvik_VK_Resume.docx',True,True)+'</div></section><div class="resume-frame"><iframe title="Sathvik VK one-page resume" src="Sathvik_VK_Resume.pdf"></iframe></div>'
    write('resume/index.html',page('Resume','One-page CV for Sathvik VK, founder/operator transitioning into venture research.','resume/',resume,1,'resume'))
    archive='<section class="page-hero"><p class="eyebrow">Historical research / November 2026</p><h1>The DeepTech archive.</h1><p class="intro">Earlier public-source work across AI infrastructure, semiconductors and robotics. These files preserve their original stage and investment-exercise context; they are separate from the current software research pool.</p></section><section class="section archive-list"><a href="view/portfolio.html"><strong>DeepTech portfolio · view PDF</strong><span>Original 48-company mapping, Simplismart / C2i / CynLr screens and independent CynLr Series B IC exercise. Assumptions are illustrative.</span></a><a href="view/model.html"><strong>CynLr model · browser view</strong><span>Historical scenario and financing-structure exercise; proposed economics, not company-reported forecasts.</span></a><a href="view/universe.html"><strong>Original company universe · view workbook data</strong><span>Preserved coverage across stages and sectors; not counted in the new early-stage software pool.</span></a><a href="view/sources.html"><strong>Original source log · browser view</strong><span>Evidence register accompanying the historical exercise.</span></a></section>'
    write('archive.html',page('Historical research archive','Original DeepTech investment exercises preserved with stage and source context.','archive.html',archive))
    method='<section class="page-hero"><p class="eyebrow">Methodology</p><h1>Make the evidence inspectable.</h1></section><div class="reading"><h2>Dates and funding stage</h2><p>A round label is the last public financing announcement located in the sources, not a representation of current private capitalization or an open round. Announcement, source access and editorial review dates are separate. Month-only dates remain month-only.</p><h2>Evidence and judgment</h2><p>Company and investor claims remain attributed. Public announcements establish what was disclosed, not independent technical performance or verified customer results. The screens contain provisional analytical conclusions and proposed tests; no experiment is implied to have been run.</p><h2>Coverage and counts</h2><p>India, UAE, Europe (including the UK) and USA memberships follow cited headquarters or operating-location evidence. Incorporation, nationality and target markets do not establish HQ. Unique company totals differ from overlapping region counts. Conflict holds and stale financing entries are excluded from main pool counts.</p><h2>Unknowns and conflicts</h2><p>Missing values remain null in the dataset. Conflicting amount and stage claims are retained rather than silently reconciled. Founder conversations, customers, revenue or diligence access are never inferred from public profiles.</p><h2>Research access</h2><p>Relationships default to public research only. This portfolio is independent research alongside founder/operator work.</p><h2>Downloads</h2><p><a href="data/research-universe.json">Company data</a> · <a href="data/source-register.json">Source register</a> · <a href="archive.html">Historical files</a></p></div>'
    write('methodology.html',page('Research methodology','Evidence types, date conventions, funding-stage limits and research pool eligibility.','methodology.html',method))

def redirect(old,new):
    title='This research has moved'
    from urllib.parse import urljoin
    canonical=urljoin(BASE+'/'+old,new)
    write(old,f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url={new}"><link rel="canonical" href="{canonical}"><title>{title}</title></head><body><p><a href="{new}">Continue to the updated research</a></p></body></html>')

def artifact_viewers():
    import openpyxl
    original_model=CONTENT/'legacy/model.html'
    model=(original_model if original_model.exists() else SITE/'view/model.html').read_text()
    model_main=re.search(r'<main[^>]*>(.*)</main>',model,re.S)
    if model_main:
        body='<section class="page-hero"><p class="eyebrow">Historical scenario exercise</p><p class="intro">Illustrative CynLr assumptions and financing structures from the original workbook; these are not company-reported projections.</p></section><div class="artifact-model">'+model_main.group(1)+'</div>'
        write('view/model.html',page('CynLr model archive','Historical illustrative model scenarios and financing structures.','view/model.html',body,1))
    assets={'universe':('Research universe archive','Sathvik_VK_Research_Universe.xlsx','Universe'),'sources':('Source log archive','Sathvik_VK_VC_Source_Log.xlsx','Source_Log')}
    for slug,(title,filename,sheet) in assets.items():
        wb=openpyxl.load_workbook(OUT/'public-assets'/filename,read_only=True,data_only=True)
        rows=list(wb[sheet].values); head=rows[0]
        body=f'<section class="page-hero"><p class="eyebrow">Historical DeepTech exercise</p><h1>{title}.</h1><p class="intro">Original workbook contents preserved in their historical context. This archive is separate from the current early-stage software pool.</p>'+button('Download workbook','../public-assets/'+filename,True,True)+'</section><div style="overflow:auto"><table class="calendar"><thead><tr>'
        body+=''.join(f'<th>{E(x)}</th>' for x in head)+'</tr></thead><tbody>'
        for row in rows[1:]:
            if not any(v is not None for v in row): continue
            body+='<tr>'
            for cell in row:
                if isinstance(cell,str) and cell.startswith(('https://','http://')): value=f'<a href="{E(cell)}">Source ↗</a>'
                else: value=E(cell if cell is not None else '—')
                body+=f'<td>{value}</td>'
            body+='</tr>'
        body+='</tbody></table></div>'
        write(f'view/{slug}.html',page(title,'Read and download the original historical workbook.',f'view/{slug}.html',body,1))
    portfolio='<section class="page-hero"><p class="eyebrow">Historical investment exercise</p><h1>DeepTech portfolio.</h1><p class="intro">The original public-source exercise, including the illustrative CynLr Series B case. Funding and scenario assumptions retain their original context.</p><div class="actions">'+button('View PDF','../public-assets/Sathvik_VK_DeepTech_Investment_Portfolio.pdf')+button('Download PDF','../public-assets/Sathvik_VK_DeepTech_Investment_Portfolio.pdf',True,True)+'</div></section><div class="resume-frame"><iframe id="portfolio-pdf" title="Historical DeepTech investment portfolio" src="../public-assets/Sathvik_VK_DeepTech_Investment_Portfolio.pdf#view=FitH"></iframe></div>'
    doc=page('DeepTech portfolio archive','Read the original public-source DeepTech investment exercise.','view/portfolio.html',portfolio,1)
    doc=doc.replace('</body>','<script>const p=location.hash.match(/^#page=(\\d{1,3})$/);if(p)document.getElementById("portfolio-pdf").src="../public-assets/Sathvik_VK_DeepTech_Investment_Portfolio.pdf#page="+p[1];</script></body>')
    write('view/portfolio.html',doc)

FRAMEWORKS=[{'title':'Seedcamp investment FAQ','url':'https://seedcamp.com/faqs/','type':'investor perspective'},{'title':'Bessemer: Vertical AI principles','url':'https://www.bvp.com/atlas/part-iv-ten-principles-for-building-strong-vertical-ai-businesses','type':'investor perspective'},{'title':'Anthropic: Demystifying evals for AI agents','url':'https://www.anthropic.com/research/demystifying-evals-for-ai-agents','type':'builder research'},{'title':'Sequoia: Own Your Intelligence','url':'https://sequoiacap.com/article/own-your-intelligence-a-how-to-guide','type':'investor perspective'}]

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--preview',action='store_true'); parser.add_argument('--output',type=Path); args=parser.parse_args()
    PREVIEW=args.preview; OUT=(args.output or (PACKAGE/'preview-site' if PREVIEW else PACKAGE/'release-site')).resolve()
    if OUT==SITE or SITE in OUT.parents: raise SystemExit('Build output must be separate from the source repository.')
    data=load('companies.json'); ALL_COMPANIES=data['records']; BY_ID={x['id']:x for x in ALL_COMPANIES}
    SCREENS=load('screens.json'); journal=load('journal.json'); ARTICLES=journal['articles']; CALENDAR=journal['calendar']
    approvals=load('editorial-approval.json') if (CONTENT/'editorial-approval.json').exists() else {'screens':[],'articles':[]}
    if not PREVIEW:
        if any(s['id'] not in approvals['screens'] for s in SCREENS[:3]) or any(a['slug'] not in approvals['articles'] for a in ARTICLES):
            raise SystemExit('RELEASE BLOCKED: screen and journal drafts require Sathvik editorial approval; use --preview for review.')
        SCREENS=[s for s in SCREENS if s['id'] in approvals['screens']]
        for x in SCREENS:
            x['editorialStatus']='published'
            x['summary']=x['summary'].removeprefix('Provisional draft: ')
            x['summary']=x['summary'][:1].upper()+x['summary'][1:]
        for x in ARTICLES: x['editorialStatus']='published'; x['published']=approvals['date']
    for c in ALL_COMPANIES:
        related=next((s for s in SCREENS if s['id']==c['id']),None)
        if related and c['theme'] != related['theme']: raise SystemExit('Company/screen theme mismatch: '+c['id'])
        c['assessment']=related['recommendation'] if related else None
        c['assessmentStatus']='draft' if related and PREVIEW else 'published' if related else 'unassessed'
        c['screenUrl']='screens/'+related['slug']+'.html' if related else None
    ELIGIBLE=[x for x in ALL_COMPANIES if x['editorialStatus']=='published' and round_of(x).get('normalizedStage') in {'pre-seed','seed'}]
    if OUT.exists() and (OUT/'build-manifest.json').exists():
        history=CONTENT/'build-history'; history.mkdir(exist_ok=True)
        shutil.move(str(OUT),str(history/(OUT.name+'-'+str(time.time_ns()))))
    OUT.mkdir(parents=True,exist_ok=True)
    # Explicit copy list keeps backups, private drafts, source tools and credentials out.
    for path in ['portfolio.css','research-v3.js','site-config.js','favicon.svg','social-card.png']:
        shutil.copy2(SITE/path,OUT/path)
    (OUT/'public-assets').mkdir(exist_ok=True)
    for filename in ['Sathvik_VK_DeepTech_Investment_Portfolio.pdf','Sathvik_VK_Flagship_Investment_Model.xlsx','Sathvik_VK_Research_Universe.xlsx','Sathvik_VK_VC_Source_Log.xlsx']:
        shutil.copy2(SITE/'public-assets'/filename,OUT/'public-assets'/filename)
    (OUT/'view').mkdir(exist_ok=True)
    shutil.copy2(SITE/'view/view.css',OUT/'view/view.css')
    (OUT/'resume').mkdir(exist_ok=True)
    for suffix in ['pdf','docx']: shutil.copy2(PACKAGE/f'resume/Sathvik_VK_Resume.{suffix}',OUT/f'resume/Sathvik_VK_Resume.{suffix}')
    write('data/research-universe.json',json.dumps(data,indent=2,ensure_ascii=False))
    company_sources=load('sources-companies.json')
    screen_source_urls={s['url'] for screen in SCREENS for s in screen['sources']}
    screen_sources=load('sources-screens.json')
    if not PREVIEW: screen_sources=[s for s in screen_sources if s['url'] in screen_source_urls]
    source_register={'asOf':DATE,'frameworks':FRAMEWORKS,'companies':company_sources.get('sources',[]) if isinstance(company_sources,dict) else company_sources,'screens':screen_sources,'journal':load('sources-journal.json')}
    write('data/source-register.json',json.dumps(source_register,indent=2,ensure_ascii=False))
    homepage(); research_page(); theme_pages(); about(); auxiliary(); artifact_viewers()
    for x in SCREENS: write_detail(x)
    for x in ARTICLES: write_detail(x,False)
    redirect('cases.html','screens.html')
    redirects={'pre-revenue-founder.html':'preseed-judgment.html','pilot-commercial-evidence.html':'paid-pilot.html','robotics-seed-proof.html':'../archive.html','technical-differentiation.html':'../archive.html','series-a-evidence.html':'../archive.html','bottleneck-thesis.html':'../archive.html','robotics-demos.html':'../archive.html','watts-tokens.html':'../archive.html'}
    for old,new in redirects.items(): redirect('journal/'+old,new)
    write('social-card.svg','<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><rect width="1200" height="630" fill="#f5f3ee"/><path d="M70 130H1130" stroke="#d7d7ce"/><g fill="#17211d" font-family="Arial,sans-serif"><text x="70" y="98" font-size="25" letter-spacing="3">SATHVIK VK</text><text x="70" y="240" font-size="64">Pre-seed &amp; Seed</text><text x="70" y="320" font-size="64">AI Research</text><text x="70" y="425" font-size="26" fill="#314d5c">Memory · Reliable deployment · Business workflows</text><text x="70" y="555" font-size="23">sathvikvk.pro</text></g></svg>')
    write('robots.txt','User-agent: *\nDisallow: /\n' if PREVIEW else f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    routes=['','screens.html','research.html','themes.html','about.html','resume/','journal/','methodology.html','archive.html']+[f'screens/{s["slug"]}.html' for s in SCREENS]+[f'journal/{a["slug"]}.html' for a in ARTICLES]
    write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}/{r}</loc><lastmod>{DATE}</lastmod></url>' for r in routes)+'</urlset>')
    write('vercel.json',json.dumps({'headers':[{'source':'/data/(.*)','headers':[{'key':'Cache-Control','value':'public, max-age=0, must-revalidate'}]}],'redirects':[{'source':'/cases.html','destination':'/screens.html','permanent':True}]}))
    manifest={'asOf':DATE,'preview':PREVIEW,'files':{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file()}}
    write('build-manifest.json',json.dumps(manifest,indent=2))
    print(json.dumps({'output':str(OUT),'preview':PREVIEW,'records':len(ALL_COMPANIES),'eligible':len(ELIGIBLE),'screens':len(SCREENS),'articles':len(ARTICLES)},indent=2))
