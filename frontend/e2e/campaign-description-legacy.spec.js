import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;

test('campaign description edit persists after reopening without paid provider calls',async({page})=>{
 const paid=[];
 page.on('request',req=>{if(req.url().includes('socialcrawl.dev')||req.url().includes('api.openai.com'))paid.push(req.url())});
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(email);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
 await page.goto('/social-listening?tab=campaigns');
 await page.getByRole('button',{name:/New Campaign/i}).click();
 const modal=page.getByRole('dialog',{name:'Create Campaign'});
 const name='QA Description Edit '+Date.now();
 await modal.getByLabel('Campaign name *').fill(name);
 const keywords=modal.getByRole('textbox',{name:'Main keywords'});
 await keywords.fill('pemilu');await keywords.press('Enter');
 await modal.getByRole('button',{name:'Save Draft'}).click();
 await expect(page.getByRole('row').filter({hasText:name})).toBeVisible();
 await page.getByRole('row').filter({hasText:name}).getByRole('button',{name:'Edit'}).click();
 const edit=page.getByRole('dialog',{name:'Edit Campaign'});
 const description='Monitor Indonesian election governance and potential violations using verified source evidence.';
 await edit.getByLabel('Description').fill(description);
 await edit.getByRole('button',{name:'Save Draft'}).click();
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.getByRole('row').filter({hasText:name}).getByRole('button',{name:'Edit'}).click();
 await expect(page.getByRole('dialog',{name:'Edit Campaign'}).getByLabel('Description')).toHaveValue(description);
 expect(paid).toEqual([]);
});
