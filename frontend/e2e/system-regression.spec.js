import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

const ADMIN_EMAIL='admin@bawaslu.local';
const ADMIN_PASSWORD=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;

async function uiLogin(page){
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  await page.getByLabel(/^password$/i).fill(ADMIN_PASSWORD);
  await page.getByRole('button',{name:/log in|masuk/i}).click();
  await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}

test('completed workspace routes load without client errors or access denial for national administrator',async({page})=>{
  const pageErrors=[];
  page.on('pageerror',error=>pageErrors.push(String(error)));
  await uiLogin(page);

  const routes=['/','/watchlist','/social-listening','/inbox','/assistant','/add','/sources','/validation','/administration'];
  for(const route of routes){
    await page.goto(route);
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveURL(new RegExp(route==='/'?'/$':route.replace('/','\\/')));
    await expect(page.getByText(/page not found/i)).toHaveCount(0);
    await expect(page.getByRole('alert').filter({hasText:/access denied/i})).toHaveCount(0);
    await expect(page.locator('body')).not.toContainText(/application error|uncaught runtime error/i);
  }
  expect(pageErrors).toEqual([]);
});

test('language toggle remains operational after cross-module navigation',async({page})=>{
  await uiLogin(page);
  for(const route of ['/','/watchlist','/social-listening','/inbox','/assistant','/add']){
    await page.goto(route);
    await page.getByRole('button',{name:'ID'}).click();
    await expect(page.getByRole('button',{name:'EN'})).toBeVisible();
    await page.getByRole('button',{name:'EN'}).click();
    await expect(page.getByRole('button',{name:'ID'})).toBeVisible();
  }
});
