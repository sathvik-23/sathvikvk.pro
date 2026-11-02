(() => {
  const c = window.SATHVIK_SITE || {};
  document.querySelectorAll('a[href*="YOUR_EMAIL@example.com"]').forEach(a => a.href = a.href.replaceAll('YOUR_EMAIL@example.com', c.email || 'YOUR_EMAIL@example.com'));
  document.querySelectorAll('a[href*="YOUR-LINKEDIN"]').forEach(a => a.href = c.linkedin || a.href);
  const canonical = document.querySelector('link[rel="canonical"]');
  if (canonical && c.canonicalUrl) canonical.href = c.canonicalUrl;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const total = document.querySelector('#total-companies');
  const sectorGrid = document.querySelector('#sector-grid');
  const database = document.querySelector('#database-preview');
  const search = document.querySelector('#company-search');
  const filter = document.querySelector('#sector-filter');
  let data = { sectors: [], companies: [] };

  const renderDatabase = () => {
    const query = (search?.value || '').trim().toLowerCase();
    const selected = filter?.value || 'all';
    const rows = data.companies.filter(company => (selected === 'all' || company.sector === selected) && (!query || company.company.toLowerCase().includes(query))).slice(0, 12);
    if (!rows.length) { database.innerHTML = '<p class="muted">No companies match this view yet.</p>'; return; }
    database.innerHTML = '<div class="database-head"><span>Company</span><span>Sector</span><span>Sub-sector</span><span>Decision</span><span>Confidence</span><span>Next trigger</span></div>' + rows.map(company => {
      const sector = data.sectors.find(item => item.id === company.sector);
      return `<div class="database-row"><strong>${esc(company.company)}</strong><span>${esc(sector?.short_label || 'Unclassified')}</span><span>${esc(company.sub_sector || 'TBD')}</span><span>${esc(company.decision || 'Seed record')}</span><span>${esc(company.confidence ?? 'TBD')}</span><span class="muted">${esc(company.next_trigger || 'TBD')}</span></div>`;
    }).join('') + `<p class="database-note">Showing ${rows.length} of ${data.companies.length} public seed records. Full fields—decision, confidence, last reviewed and next trigger—populate as each record is re-reviewed.</p>`;
  };

  const render = () => {
    total.textContent = data.summary?.tracked_companies ?? data.companies.length;
    const candidateCount = document.querySelector('#candidate-count');
    const proceedCount = document.querySelector('#proceed-count');
    if (candidateCount) candidateCount.textContent = data.summary?.investment_candidates ?? data.companies.filter(company => ['PROCEED','WATCH','PASS'].includes(company.decision)).length;
    if (proceedCount) proceedCount.textContent = data.summary?.proceed_screens ?? data.companies.filter(company => String(company.decision).startsWith('PROCEED')).length;
    sectorGrid.innerHTML = data.sectors.map((sector, index) => {
      const count = data.companies.filter(company => company.sector === sector.id).length;
      return `<button class="bottleneck-card" type="button" data-sector="${esc(sector.id)}"><span>0${index + 1}</span><strong>${esc(sector.label)}</strong><b>${count}</b><small>companies tracked</small><p>${esc(sector.bottleneck)}</p></button>`;
    }).join('');
    filter.innerHTML = '<option value="all">All sectors</option>' + data.sectors.map(sector => `<option value="${esc(sector.id)}">${esc(sector.short_label)}</option>`).join('');
    sectorGrid.querySelectorAll('[data-sector]').forEach(button => button.addEventListener('click', () => { filter.value = button.dataset.sector; renderDatabase(); database.scrollIntoView({ behavior: 'smooth', block: 'center' }); }));
    renderDatabase();
  };
  fetch('data/research-universe.json').then(response => { if (!response.ok) throw new Error('research data unavailable'); return response.json(); }).then(json => { data = json; render(); }).catch(() => { total.textContent = '97'; document.querySelector('#candidate-count').textContent = '41'; document.querySelector('#proceed-count').textContent = '3'; sectorGrid.innerHTML = '<p class="muted">The research map is temporarily unavailable. The public universe workbook remains available below.</p>'; });
  search?.addEventListener('input', renderDatabase);
  filter?.addEventListener('change', renderDatabase);
})();
