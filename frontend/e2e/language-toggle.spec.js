import {test,expect} from '@playwright/test';

// In the standalone Command Centre, language changes must preserve source data.
test('Command Centre locale changes labels, restores English and preserves source text',async ({page})=>{
 await page.goto('/ui-freeze/smart-radar-v6_2.html?build=119.8');
 await page.waitForFunction(()=>typeof window.BAWASLUInterfaceLocale?.setLanguage==='function');
 await page.evaluate(()=>{
  const label=document.createElement('button');
  label.id='qa-i18n-label';
  label.textContent='Activity by Platform';
  document.body.appendChild(label);
  const original=document.createElement('p');
  original.id='qa-original-evidence';
  original.setAttribute('data-i18n-exempt','true');
  original.textContent='Potential Violations';
  document.body.appendChild(original);
  const input=document.createElement('input');
  input.id='qa-search-label';
  input.placeholder='Search posts';
  input.value='Public Concern';
  document.body.appendChild(input);
 });
 await page.evaluate(()=>window.BAWASLUInterfaceLocale.setLanguage('id'));
 await expect(page.locator('#qa-i18n-label')).toHaveText('Aktivitas per Platform');
 await expect(page.locator('#qa-search-label')).toHaveAttribute('placeholder','Cari unggahan');
 await expect(page.locator('#qa-original-evidence')).toHaveText('Potential Violations');
 await expect(page.locator('#qa-search-label')).toHaveValue('Public Concern');
 await page.evaluate(()=>window.BAWASLUInterfaceLocale.setLanguage('en'));
 await expect(page.locator('#qa-i18n-label')).toHaveText('Activity by Platform');
 await expect(page.locator('#qa-search-label')).toHaveAttribute('placeholder','Search posts');
 await expect(page.locator('#qa-original-evidence')).toHaveText('Potential Violations');
});

test('language message is accepted only from same-origin parent',async ({page})=>{
 await page.goto('/ui-freeze/smart-radar-v6_2.html?build=119.8');
 await page.waitForFunction(()=>Boolean(window.BAWASLUInterfaceLocale));
 await page.evaluate(()=>{
  const p=document.createElement('p');p.id='qa-cross-frame';p.textContent='Social Listening';document.body.appendChild(p);
  window.dispatchEvent(new MessageEvent('message',{
   origin:'https://untrusted.example',data:{type:'BAWASLU_UI_LANGUAGE',language:'id'}
  }));
 });
 await expect(page.locator('#qa-cross-frame')).toHaveText('Social Listening');
 await page.evaluate(()=>window.postMessage({type:'BAWASLU_UI_LANGUAGE',language:'id'},window.location.origin));
 await expect(page.locator('#qa-cross-frame')).toHaveText('Pemantauan Media Sosial');
});


test('Operational interface labels switch both directions without changing evidence or form values',async ({page})=>{
 await page.goto('/ui-freeze/smart-radar-v6_2.html?build=119.8');
 await page.waitForFunction(()=>typeof window.BAWASLUInterfaceLocale?.setLanguage==='function');
 await page.evaluate(()=>{
  for(const [i,value] of ['Executive intelligence overview','Monitoring & Collection','Source-linked grouping review'].entries()){
   const element=document.createElement('span');element.id='qa-label-'+i;element.textContent=value;document.body.append(element);
  }
  const submit=document.createElement('input');submit.type='submit';submit.id='qa-submit';submit.value='Apply search';document.body.append(submit);
  const typed=document.createElement('input');typed.type='text';typed.id='qa-typed';typed.value='Apply search';document.body.append(typed);
  const evidence=document.createElement('p');evidence.id='qa-evidence';evidence.dataset.i18nExempt='true';evidence.textContent='Executive intelligence overview';document.body.append(evidence);
 });
 await page.evaluate(()=>window.BAWASLUInterfaceLocale.setLanguage('id'));
 await expect(page.locator('#qa-label-0')).toHaveText('Ringkasan intelijen eksekutif');
 await expect(page.locator('#qa-label-1')).toHaveText('Pemantauan & Pengumpulan');
 await expect(page.locator('#qa-label-2')).toHaveText('Tinjauan pengelompokan berdasarkan sumber');
 await expect(page.locator('#qa-submit')).toHaveValue('Terapkan pencarian');
 await expect(page.locator('#qa-typed')).toHaveValue('Apply search');
 await expect(page.locator('#qa-evidence')).toHaveText('Executive intelligence overview');
 await page.evaluate(()=>window.BAWASLUInterfaceLocale.setLanguage('en'));
 await expect(page.locator('#qa-label-0')).toHaveText('Executive intelligence overview');
 await expect(page.locator('#qa-submit')).toHaveValue('Apply search');
});
