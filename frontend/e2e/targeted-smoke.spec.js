import {test, expect} from './fixtures/local-admin.js';

test('targeted release preserves authenticated shell and critical navigation',async({page})=>{
 const paid=[];page.on('request',r=>{if(/socialcrawl\.dev|api\.openai\.com/i.test(r.url()))paid.push(r.url())});
 const response=await page.goto('/');
 expect(response?.status()||200).toBeLessThan(500);
 await expect(page.getByRole('button',{name:/log out|keluar/i})).toBeVisible();
 const nav=page.getByRole('navigation');
 for(const name of ['Command Centre','Social Listening','Intelligence Inbox']){
  await expect(nav.getByRole('link',{name:new RegExp('^'+name+'$','i')})).toBeVisible();
 }
 await expect(page.locator('body')).not.toContainText(/page not found|application error|uncaught runtime error/i);
 expect(paid).toEqual([]);
});
