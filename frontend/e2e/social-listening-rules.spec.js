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

test('saved Social Listening search can pause resume and load filters without provider calls',async({page})=>{
  await uiLogin(page);
  await page.goto('/social-listening');

  const name='QA Saved Search '+Date.now();
  await page.getByLabel(/keyword/i).fill('bawaslu qa');
  await page.getByPlaceholder(/saved search name/i).fill(name);
  await page.getByRole('button',{name:/save search/i}).click();

  await page.getByRole('button',{name:/saved searches/i}).click();
  const card=page.locator('.intel-card').filter({hasText:name});
  await expect(card).toBeVisible();
  await expect(card.getByText('Active',{exact:true})).toBeVisible();
  await expect(card.getByText('Mine',{exact:true})).toBeVisible();
  await expect(card.getByText(/Created by:/i)).toBeVisible();
  await expect(card.getByText(/Scope:/i)).toBeVisible();

  await card.getByRole('button',{name:/pause/i}).click();
  await expect(card.getByText('Inactive',{exact:true})).toBeVisible();

  await card.getByRole('button',{name:/resume/i}).click();
  await expect(card.getByText('Active',{exact:true})).toBeVisible();

  await card.getByRole('button',{name:/load filters/i}).click();
  await expect(page.getByLabel(/keyword/i)).toHaveValue('bawaslu qa');
});
