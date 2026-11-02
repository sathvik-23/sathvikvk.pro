(()=>{
  const q=s=>document.querySelector(s), norm=s=>(s||'').toLowerCase(), chosen=s=>(s||'').startsWith('All')?'All':s;
  let rows=window.RESEARCH_UNIVERSE||[];
  function render(){
    const term=norm(q('#db-search')?.value), stage=chosen(q('#db-stage')?.value), sector=chosen(q('#db-sector')?.value), geo=chosen(q('#db-geography')?.value);
    const out=rows.filter(r=>(!term||JSON.stringify(r).toLowerCase().includes(term))&&(stage==='All'||norm(r.stage).includes(norm(stage)))&&(sector==='All'||r.sector===sector)&&(geo==='All'||r.geography===geo));
    q('#db-count').textContent=`${out.length} of ${rows.length} companies`;
    q('#research-table tbody').innerHTML=out.map(r=>`<tr><td><b>${r.company}</b><small>${r.subsector||''}</small></td><td>${r.stage}</td><td>${r.sector}</td><td>${r.geography||'—'}</td><td><span class="decision ${(r.decision||'Tracked').toLowerCase()}">${r.decision||'Tracked'}</span></td><td>${r.trigger||r.killQuestion||'Next customer, product or financing signal'}</td><td><a href="${r.sourceUrl||'#'}" target="_blank" rel="noreferrer">${r.sourceId||'—'} ↗</a></td></tr>`).join('');
  }
  document.querySelectorAll('[data-db-filter]').forEach(x=>x.addEventListener('input',render));
  if(rows.length){ render(); }
  else { fetch('data/research-universe.json').then(r=>r.json()).then(data=>{rows=Array.isArray(data)?data:data.companies||[];render();}).catch(()=>{q('#db-count').textContent='Research data unavailable';}); }
})();
