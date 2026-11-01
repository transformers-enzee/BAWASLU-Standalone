import {test,expect} from '@playwright/test';

// In the standalone Command Centre, language changes must preserve source data.
test('Command Centre locale changes labels, restores English and preserves source text',async ({page})=>{
 await page.goto('/ui-freeze/smart-radar-v6_2.html?build=119.7');
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
 await page.goto('/ui-freeze/smart-radar-v6_2.html?build=119.7');
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
