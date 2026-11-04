async (page) => {
  const base='http://127.0.0.1:4173';
  const assert=(ok,message) => {if (!ok) throw new Error(message);};
  const report=[];
  const dataset=await (await page.request.get(base+'/data/research-universe.json')).json();
  const eligible=dataset.records.filter(c=>c.editorialStatus==='published' && ['pre-seed','seed'].includes(c.roundHistory.at(-1).normalizedStage));
  await page.goto(base+'/research.html');
  await page.locator('.record').first().waitFor();
  assert(await page.locator('.record').count()===eligible.length,'Initial eligible count');
  for (const region of ['India','UAE','Europe','USA']) {
    await page.goto(base+'/research.html?region='+region);
    await page.locator('.record').first().waitFor();
    assert(await page.locator('.record').count()===eligible.filter(c=>c.regions.includes(region)).length,'Region '+region);
    for (const theme of ['context','deployment','workflows']) {
      await page.getByRole('combobox',{name:'Theme',exact:true}).selectOption(theme);
      const expected=eligible.filter(c=>c.regions.includes(region)&&c.theme===theme);
      assert(await page.locator('.record').count()===expected.length,'Combined region/theme '+region+'/'+theme);
      assert(new URL(page.url()).searchParams.get('region')===region,'Region lost from URL');
      assert(new URL(page.url()).searchParams.get('theme')===theme,'Theme lost from URL');
    }
    report.push({region,combinedFilters:'pass'});
  }
  await page.goto(base+'/research.html?region=India&theme=deployment&stage=pre-seed&assessment=Investigate&q=SuperBryn');
  await page.locator('.record').first().waitFor();
  assert(await page.locator('.record').count()===1,'All filters intersection');
  assert((await page.locator('.record').innerText()).includes('SuperBryn'),'Wrong intersection company');
  await page.reload(); await page.locator('.record').first().waitFor();
  assert(await page.getByLabel('Search',{exact:true}).inputValue()==='SuperBryn','URL search restoration');
  await page.locator('.record summary').click();
  assert(await page.locator('.record').getAttribute('open')!==null,'Record does not expand');
  assert(await page.locator('.record-body .sources a[href^="https:"]').count()>0,'Expanded sources absent');
  await page.getByLabel('Search',{exact:true}).fill('no-company-matches-this-query');
  assert(await page.locator('.empty-state').isVisible(),'Empty state missing');
  await page.getByRole('button',{name:'Clear filters',exact:true}).click();
  assert(await page.locator('.record').count()===eligible.length,'Clear filters failed');
  report.push({filters:'stage + assessment + keyword + reload + details + empty + reset pass'});
  await page.route('**/data/research-universe.json',route=>route.abort());
  await page.reload(); await page.locator('#research-error').waitFor({state:'visible'});
  assert(await page.locator('.record').count()===0,'Failure retained stale rows');
  await page.unroute('**/data/research-universe.json');
  await page.getByRole('button',{name:'Try again',exact:true}).click();
  await page.locator('.record').first().waitFor();
  report.push({loadingFailure:'visible failure and retry pass'});
  const bad=JSON.parse(JSON.stringify(dataset));
  bad.records[0].name='<img src=x onerror="window.__injected=1">';
  bad.records[0].sources[0].url='javascript:alert(1)';
  await page.route('**/data/research-universe.json',route=>route.fulfill({json:bad}));
  await page.reload(); await page.locator('.record').first().waitFor();
  assert(await page.locator('.record img').count()===0,'Research string interpreted as HTML');
  await page.locator('.record summary').first().click();
  assert(await page.locator('.record a[href^="javascript:"]').count()===0,'Unsafe source URL rendered');
  assert(await page.evaluate(()=>window.__injected===undefined),'Injected handler executed');
  await page.unroute('**/data/research-universe.json');
  report.push({safeRendering:'text and URL safety pass'});
  const routes=['/','/screens.html','/screens/qontext.html','/research.html','/journal/memory-business.html','/about.html'];
  for (const width of [1440,768,390]) {
    await page.setViewportSize({width,height:844});
    for (const route of routes) {
      await page.goto(base+route);
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
      assert(!overflow,'Horizontal overflow '+width+' '+route);
      if (route==='/') await page.screenshot({path:'output/playwright/home-'+width+'.png',fullPage:false});
      if ((width===1440 || width===390) && route==='/research.html') {
        await page.locator('.record').first().waitFor();
        await page.screenshot({path:'output/playwright/research-'+width+'.png',fullPage:false});
      }
      if ((width===1440 || width===390) && route==='/screens/qontext.html') await page.screenshot({path:'output/playwright/screen-'+width+'.png',fullPage:false});
      if (width===390 && route==='/journal/memory-business.html') await page.screenshot({path:'output/playwright/article-390.png',fullPage:false});
    }
    report.push({viewport:width,routes:routes.length,overflow:'none'});
  }
  await page.goto(base+'/');
  await page.locator('.mobile-menu summary').focus();
  await page.keyboard.press('Enter');
  assert(await page.locator('.mobile-menu nav').isVisible(),'Keyboard menu did not open');
  await page.getByRole('navigation',{name:'Mobile navigation',exact:true}).getByRole('link',{name:'Research',exact:true}).click();
  assert(new URL(page.url()).pathname==='/research.html','Mobile navigation route failed');
  report.push({mobileMenu:'keyboard and navigation pass'});
  await page.goto(base+'/view/portfolio.html#page=16');
  assert((await page.locator('#portfolio-pdf').getAttribute('src')).endsWith('#page=16'),'PDF page fragment not forwarded');
  for (const route of ['/resume/','/resume/Sathvik_VK_Resume.pdf','/resume/Sathvik_VK_Resume.docx','/view/model.html','/view/sources.html','/view/universe.html']) {
    const response=await page.request.get(base+route); assert(response.ok(),'Artifact failed '+route);
  }
  await page.goto(base+'/cases.html');
  await page.waitForURL('**/screens.html');
  await page.goto(base+'/screens.html#seed-ai');
  await page.waitForURL('**/archive.html');
  await page.goto(base+'/journal/pre-revenue-founder.html');
  await page.waitForURL('**/preseed-judgment.html');
  report.push({artifacts:'resume + workbook viewers + PDF fragment + legacy redirects pass'});
  return report;
}
