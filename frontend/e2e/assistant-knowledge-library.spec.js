import {test,expect} from '@playwright/test';
import config from '../playwright.config.js';

const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
async function login(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(email);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}

test('knowledge library resolves authorized national document metadata',async({page})=>{
 let reads=0;
 await page.route('**/api/assistant-knowledge/documents',async route=>{
  reads++;
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   documents:[{id:1,title:'BAWASLU_Sample_AI_Knowledge_Full_Text',filename:'sample.pdf',
    scope:'NATIONAL',province:'',pages:12,extracted_chars:24000,
    document_type:'OTHER',review_status:'UNREVIEWED',embedding_status:'NOT_INDEXED'}],
   can_upload:false,can_review:false,default_scope:'NATIONAL',default_province:'',paid_provider_called:false
  })});
 });
 await login(page);
 await page.goto('/assistant');
 const library=page.getByRole('region',{name:'Assistant PDF knowledge library'});
 await expect(library).toContainText('1 PDF');
 await expect(library).not.toContainText('Loading PDF library');
 await library.locator('button[aria-expanded]').click();
 await expect(library.getByText('BAWASLU_Sample_AI_Knowledge_Full_Text')).toBeVisible();
 await expect(library).toContainText('12 pages');
 expect(reads).toBeGreaterThanOrEqual(1);
});

test('knowledge library distinguishes unavailable metadata from a true zero PDF result',async({page})=>{
 await page.route('**/api/assistant-knowledge/documents',route=>
  route.fulfill({status:503,contentType:'application/json',
   body:JSON.stringify({detail:'Service temporarily unavailable'})}));
 await login(page);
 await page.goto('/assistant');
 const library=page.getByRole('region',{name:'Assistant PDF knowledge library'});
 await expect(library).toContainText('PDF unavailable');
 await expect(library).not.toContainText('0 PDF');
 await library.locator('button[aria-expanded]').click();
 await expect(library.getByRole('alert')).toContainText('Service temporarily unavailable');
});
