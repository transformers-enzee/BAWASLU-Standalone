import {test, expect} from './fixtures/local-admin.js';


test('release navigation exposes every completed administrator module',async({page})=>{

  await page.goto('/');
  const nav=page.getByRole('navigation');
  // V3 navigation embeds Candidate Watchlist inside Social Listening.
  const modules=['Command Centre','Social Listening','Intelligence Inbox',
    'Data Sources','Validation','Administration'];
  for(const name of modules){
    await expect(nav.getByRole('link',{name:new RegExp('^'+name+'$','i')})).toBeVisible();
  }
  await expect(nav.locator('a[href="/management/ai-assistant"]')).toBeVisible();
  await expect(nav.locator('a[href="/ai-assistant"]')).toBeVisible();
  // Existing assistant versions must remain visible; AI-4 is additive only.
  for(const href of ['/assistant','/ai-assistant','/ai-assistant-v2-new','/ai-4',
                      '/management/assistant','/management/ai-assistant',
                      '/management/ai-assistant-v2-new','/management/ai-4']){
    await expect(nav.locator('a[href="'+href+'"]')).toBeVisible();
  }
  await expect(nav.getByRole('link',{name:/^Watchlist$/i})).toHaveCount(0);
  await expect(nav.getByRole('link',{name:/^Add Intelligence$/i})).toHaveCount(0);
  await expect(page.locator('header').getByRole('link',{name:/^Add Intelligence$/i})).toBeVisible();
});

test('completed module routes remain authenticated, error-free and free of paid-provider navigation calls',async({page})=>{
  const paidCalls=[],pageErrors=[];
  page.on('request',request=>{
    if(/socialcrawl\.dev|api\.openai\.com/i.test(request.url())) paidCalls.push(request.url());
  });
  page.on('pageerror',error=>pageErrors.push(String(error)));
  const routes=['/','/command-center','/watchlist','/social-listening','/inbox','/assistant','/add','/sources','/validation','/administration'];
  // One traversal preserves the former three route-health checks.
  for(const route of routes){
    const response=await page.goto(route);
    expect(response?.status()||200).toBeLessThan(500);
    await expect(page).toHaveURL(new RegExp(route==='/'?'/$':route.replace('/','\\/')));
    await expect(page.getByRole('button',{name:/log out|keluar/i})).toBeVisible();
    await expect(page.getByText(/page not found/i)).toHaveCount(0);
    await expect(page.getByRole('alert').filter({hasText:/access denied/i})).toHaveCount(0);
    await expect(page.locator('body')).not.toContainText(/application error|uncaught runtime error/i);
  }
  expect(pageErrors).toEqual([]);
  expect(paidCalls).toEqual([]);
});
