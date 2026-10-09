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

test('release navigation exposes every completed administrator module',async({page})=>{
  await uiLogin(page);
  const nav=page.getByRole('navigation');
  const modules=[
    'Home','Watchlist','Social Listening','Intelligence Inbox',
    'Intelligence Assistant','Add Intelligence','Data Sources',
    'Validation','Administration'
  ];
  for(const name of modules){
    await expect(nav.getByRole('link',{name:new RegExp('^'+name+'$','i')})).toBeVisible();
  }
});

test('completed module routes remain authenticated after direct navigation',async({page})=>{
  await uiLogin(page);
  const routes=['/','/watchlist','/social-listening','/inbox','/assistant','/add','/sources','/validation','/administration'];
  for(const route of routes){
    const response=await page.goto(route);
    expect(response?.status()||200).toBeLessThan(500);
    await expect(page.getByRole('button',{name:/log out|keluar/i})).toBeVisible();
    await expect(page.locator('body')).not.toContainText(/page not found|uncaught runtime error|application error/i);
  }
});

test('release build does not expose paid-provider execution during navigation',async({page})=>{
  const paidCalls=[];
  page.on('request',request=>{
    const url=request.url();
    if(/socialcrawl\.dev|api\.openai\.com/i.test(url)) paidCalls.push(url);
  });
  await uiLogin(page);
  for(const route of ['/','/watchlist','/social-listening','/inbox','/assistant','/add','/sources','/validation','/administration']){
    await page.goto(route);
    await page.waitForLoadState('domcontentloaded');
  }
  expect(paidCalls).toEqual([]);
});
