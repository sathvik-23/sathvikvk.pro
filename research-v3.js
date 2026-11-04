(() => {
  // Schema v3: the canonical software research pool and its verification queue.
  'use strict';
  const regionNames = ['India', 'UAE', 'Europe', 'USA'];
  const themeNames = {context:'Memory & context',deployment:'Reliable deployment',workflows:'Business workflows'};
  const controls = Object.fromEntries(['q','theme','stage','assessment'].map(k => [k,document.getElementById(k === 'q' ? 'query' : k)]));
  const results = document.getElementById('research-results');
  const count = document.getElementById('result-count');
  const error = document.getElementById('research-error');
  const tabs = document.getElementById('region-tabs');
  let companies = [], region = '', ready = false;

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text === null ? 'Unknown' : String(text);
    if (className) node.className = className;
    return node;
  }
  function link(text,url) {
    const node = element('a',text);
    try {
      const target = new URL(url,location.href);
      if (['https:','http:'].includes(target.protocol)) { node.href = target.href; node.rel = 'noopener noreferrer'; }
    } catch (_) { /* A malformed source is rendered as plain text. */ }
    return node;
  }
  const round = c => c.roundHistory[c.roundHistory.length - 1];
  const eligible = c => c.editorialStatus === 'published' && ['pre-seed','seed'].includes(round(c).normalizedStage);
  const assessment = c => c.assessment || 'Unassessed';
  const textValue = v => typeof v === 'string' ? v : Array.isArray(v) ? v.map(textValue).join('; ') : v === null || v === undefined ? 'Unknown' : [v.city,v.country,v.locationType,v.evidenceType].filter(Boolean).join(' · ').replaceAll('_',' ');

  function readURL() {
    const p = new URLSearchParams(location.search);
    region = regionNames.includes(p.get('region')) ? p.get('region') : '';
    for (const [key,node] of Object.entries(controls)) {
      const value = p.get(key) || '';
      node.value = node.tagName === 'SELECT' && !Array.from(node.options).some(o => o.value === value) ? '' : value;
    }
  }
  function queryFor(nextRegion = region) {
    const p = new URLSearchParams();
    if (nextRegion) p.set('region',nextRegion);
    for (const [key,node] of Object.entries(controls)) if (node.value.trim()) p.set(key,node.value.trim());
    return p;
  }
  function syncURL() {
    const q = queryFor().toString();
    history.replaceState(null,'',location.pathname+(q ? '?'+q : '')+location.hash);
  }
  function matches(c,ignoreRegion = false) {
    if (!eligible(c)) return false;
    if (!ignoreRegion && region && !c.regions.includes(region)) return false;
    if (controls.theme.value && c.theme !== controls.theme.value) return false;
    if (controls.stage.value && round(c).normalizedStage !== controls.stage.value) return false;
    if (controls.assessment.value && assessment(c) !== controls.assessment.value) return false;
    const q = controls.q.value.trim().toLowerCase();
    const haystack = [c.name,c.product,c.buyer,themeNames[c.theme],c.nextEvidence,textValue(c.evidence)].join(' ').toLowerCase();
    return !q || haystack.includes(q);
  }
  function renderTabs() {
    tabs.replaceChildren();
    for (const name of ['',...regionNames]) {
      const n = companies.filter(c => matches(c,true) && (!name || c.regions.includes(name))).length;
      const a = element('a',`${name || 'All regions'} · ${n}`);
      const q = queryFor(name).toString();
      a.href = location.pathname + (q ? '?'+q : '');
      a.setAttribute('aria-current',String(name === region));
      a.addEventListener('click',event => { if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return; event.preventDefault(); region=name; syncURL(); render(); });
      tabs.append(a);
    }
  }
  function cell(primary,secondary) {
    const node = element('span'); node.append(element('strong',primary));
    if (secondary) node.append(element('small',secondary));
    return node;
  }
  function datum(dl,label,value) {
    const group=element('div'); group.append(element('dt',label),element('dd',textValue(value))); dl.append(group);
  }
  function record(c) {
    const details = element('details',undefined,'record');
    const summary=element('summary');
    summary.append(cell(c.name,c.product),cell(themeNames[c.theme],assessment(c)+(c.assessmentStatus === 'draft' ? ' · draft' : '')));
    const r = round(c);
    const money = r.amount === null ? 'Amount unconfirmed' : `${r.currency || ''} ${Number(r.amount).toLocaleString('en-US')}`;
    summary.append(cell(r.originalLabel,`${r.announcementDate || 'Date unknown'} · ${money}`));
    const hq=c.hq;
    const knownPlace=hq || c.operatingLocations[0];
    const place=knownPlace ? [knownPlace.city,knownPlace.country].filter(Boolean).join(', ') : 'Location unverified';
    const placeType=hq ? 'Reported headquarters' : knownPlace ? (knownPlace.locationType || 'Operating presence').replaceAll('_',' ')+' · HQ unverified' : 'HQ unverified';
    summary.append(cell(place,placeType));
    summary.append(element('span',c.nextEvidence,'next-evidence'));
    const body=element('div',undefined,'record-body');
    const dl=element('dl');
    for (const [label,value] of [['Buyer',c.buyer],['Evidence',c.evidence],['Alternatives · analytical view',c.alternatives],['Key risk · analytical view',c.risk],['Next evidence to seek',c.nextEvidence],['Qualification',c.qualificationNotes],['Source conflicts',c.conflicts.length ? c.conflicts : 'None identified in this research'],['Operating locations',c.operatingLocations.length ? c.operatingLocations : 'Unknown'],['Region evidence',c.regionRationale]]) datum(dl,label,value);
    body.append(dl);
    const sources=element('div',undefined,'sources');
    for (const s of c.sources) sources.append(link(`${s.title} · ${(s.type || '').replaceAll('_',' ')}`,s.url));
    body.append(sources,element('p',`Evidence reviewed ${c.reviewed} · Public research only`,'small'));
    if (c.screenUrl) body.append(link('Read company screen →',c.screenUrl));
    details.append(summary,body); return details;
  }
  function renderQueue() {
    const held = companies.filter(c => !eligible(c));
    document.getElementById('queue-count').textContent=`Verification queue · ${held.length} excluded records`;
    const list = document.getElementById('verification-queue'); list.replaceChildren();
    for (const c of held) {
      const li=element('li'); li.append(element('strong',c.name+' — '),document.createTextNode(c.eligibilityReason || textValue(c.qualificationNotes)));
      for (const s of c.sources.slice(0,2)) li.append(document.createTextNode(' · '),link(s.title,s.url));
      list.append(li);
    }
  }
  function render() {
    if (!ready) return;
    renderTabs(); const filtered=companies.filter(c => matches(c)); const total=companies.filter(eligible).length;
    count.textContent=`${filtered.length} of ${total} unique published companies`;
    results.replaceChildren(...filtered.map(record));
    if (!filtered.length) {
      const empty=element('div',undefined,'empty-state');
      empty.append(element('h2','No companies match these filters.'),element('p','Try another region or clear one of the filters. The verification queue is separate from these results.'));
      results.append(empty);
    }
  }
  async function load() {
    ready=false; error.hidden=true; results.replaceChildren(); tabs.replaceChildren(); count.textContent='Loading research…';
    try {
      const response = await fetch('data/research-universe.json',{cache:'no-cache'});
      if (!response.ok) throw new Error('Research request failed');
      const data = await response.json();
      if (data.schemaVersion !== '3.0' || !Array.isArray(data.records)) throw new Error('Unsupported research data');
      companies=data.records; ready=true; readURL(); render(); renderQueue();
    } catch (failure) { count.textContent='Research unavailable'; error.hidden=false; }
  }
  document.getElementById('research-filters').addEventListener('submit',event => event.preventDefault());
  for (const node of Object.values(controls)) node.addEventListener(node.tagName==='INPUT' ? 'input' : 'change',() => {syncURL();render();});
  document.getElementById('reset-filters').addEventListener('click',() => {region=''; for (const node of Object.values(controls)) node.value=''; syncURL();render();});
  document.getElementById('retry-load').addEventListener('click',load);
  window.addEventListener('popstate',() => {readURL();render();});
  load();
})();
