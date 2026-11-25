import {test, expect} from './fixtures/local-admin.js';


test('Command Center loads read-only operational overview without paid-provider calls',async({page})=>{
  const paidCalls=[];
  page.on('request',request=>{if(/socialcrawl\.dev|api\.openai\.com/i.test(request.url())) paidCalls.push(request.url())});

  await page.goto('/command-center');
  await expect(page.getByRole('heading',{name:/Command Center/i})).toBeVisible();
  await expect(page.getByRole('main')).toBeVisible();
  
  
  expect(paidCalls).toEqual([]);
});

test('Command Center drill-down links point to operational modules',async({page})=>{

  await page.goto('/command-center');
  await expect(page.getByRole('main').getByRole('link',{name:/Intelligence Inbox/i}).first()).toHaveAttribute('href','/inbox');
  await expect(page.locator('aside').getByRole('link',{name:'Validation',exact:true})).toHaveAttribute('href','/validation');
  await expect(page.getByRole('main').locator('a[href="/social-listening"]').first()).toBeVisible();
});
