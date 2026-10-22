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

test('Command Center loads read-only operational overview without paid-provider calls',async({page})=>{
  const paidCalls=[];
  page.on('request',request=>{if(/socialcrawl\.dev|api\.openai\.com/i.test(request.url())) paidCalls.push(request.url())});
  await uiLogin(page);
  await page.goto('/command-center');
  await expect(page.getByRole('heading',{name:/Command Center/i})).toBeVisible();
  await expect(page.getByRole('main')).toBeVisible();
  
  
  expect(paidCalls).toEqual([]);
});

test('Command Center drill-down links point to operational modules',async({page})=>{
  await uiLogin(page);
  await page.goto('/command-center');
  await expect(page.getByRole('main').getByRole('link',{name:/Intelligence Inbox/i}).first()).toHaveAttribute('href','/inbox');
  await expect(page.getByRole('main').getByRole('link',{name:'Validation',exact:true})).toHaveAttribute('href','/validation');
  await expect(page.getByRole('main').getByRole('link',{name:'Social Review Queue',exact:true})).toBeVisible();
});
