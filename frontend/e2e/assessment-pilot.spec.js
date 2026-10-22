import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;

test('40-50 post assessment pilot previews stored evidence without provider calls',async({page})=>{
 const paid=[];
 page.on('request',req=>{if(req.url().includes('socialcrawl.dev')||req.url().includes('api.openai.com'))paid.push(req.url())});
 await page.goto('/login');
 await page.getByLabel(/email/i).fill('admin@bawaslu.local');
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
 await page.goto('/social-listening?tab=campaigns');
 await page.getByRole('button',{name:/New Campaign/i}).click();
 const dialog=page.getByRole('dialog');
 const name='QA assessment pilot '+Date.now();
 await dialog.getByLabel(/Campaign name/i).fill(name);
 const keywords=dialog.getByRole('textbox',{name:'Main keywords'});
 await keywords.fill('pemilu');await keywords.press('Enter');
 await dialog.getByRole('button',{name:'Save Draft'}).click();
 await page.getByRole('row').filter({hasText:name}).getByRole('button',{name:'Open Dashboard'}).click();
 const pilot=page.getByLabel('AI assessment pilot');
 await pilot.locator('summary').click();
 await pilot.getByLabel('Sample size').selectOption('50');
 await pilot.getByRole('button',{name:'Preview sample (free)'}).click();
 await expect(pilot.getByText('0 of 50 records selected',{exact:false})).toBeVisible();
 await expect(pilot.getByRole('progressbar',{name:'Pilot assessment completion'})).toHaveAttribute('aria-valuenow','0');
 await expect(pilot).toContainText('No AI provider called, no credits charged');
 expect(paid).toEqual([]);
});
