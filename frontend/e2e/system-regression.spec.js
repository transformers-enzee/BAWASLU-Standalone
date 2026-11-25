import {test, expect} from './fixtures/local-admin.js';

test('language toggle remains operational after cross-module navigation',async({page})=>{

  for(const route of ['/','/command-center','/watchlist','/social-listening','/inbox','/assistant','/add']){
    await page.goto(route);
    await page.locator('header button[aria-pressed]').nth(1).click();
    await expect(page.locator('header button[aria-pressed]').nth(0)).toBeVisible();
    await page.locator('header button[aria-pressed]').nth(0).click();
    await expect(page.locator('header button[aria-pressed]').nth(1)).toBeVisible();
  }
});
