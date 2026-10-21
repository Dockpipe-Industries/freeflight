import {chromium} from 'playwright';
import {writeFile} from 'node:fs/promises';
const [url,output]=process.argv.slice(2);
const browser=await chromium.launch({channel:'chromium',args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const receipt=await(await fetch(url+'/release.json')).json();
const company=receipt.environment==='production'?'https://dockpipe.com/#company':'https://staging.dockpipe.com/#company';
const evidence=[],errors=[];
async function captureWorkflowPanel(page, width) {
 const screenshot = await page.screenshot();
 const glyphPixels = await page.evaluate(async ({encoded, width}) => {
  const response = await fetch('data:image/png;base64,' + encoded);
  const image = await createImageBitmap(await response.blob());
  const canvas = document.createElement('canvas');
  canvas.width = image.width;
  canvas.height = image.height;
  const context = canvas.getContext('2d');
  context.drawImage(image, 0, 0);
  // Interior text areas for the two fixed test viewports; exclude borders and controls.
  const area = width > 760 ? [850, 280, 400, 240] : [40, 700, 300, 100];
  const pixels = context.getImageData(...area).data;
  let count = 0;
  for (let index = 0; index < pixels.length; index += 4) {
   if (pixels[index] > 120 && pixels[index + 1] > 120 && pixels[index + 2] > 120) count++;
  }
  image.close();
  return count;
 }, {encoded: screenshot.toString('base64'), width});
 if (glyphPixels < 500) throw Error('Workflow panel text disappeared during Qt rendering');
 return screenshot;
}
try{
 const robots=await(await fetch(url+'/robots.txt')).text();
 if(receipt.environment==='staging' && !robots.includes('Disallow: /'))throw Error('Staging indexing');
 if(receipt.environment==='production' && robots.includes('Disallow: /'))throw Error('Production indexing');
 if(receipt.environment==='production'){
  const sitemap=await(await fetch(url+'/sitemap.xml')).text();
  if(sitemap.includes('staging')||sitemap.includes('localhost'))throw Error('Production sitemap');
  for(const match of sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)){
   const canonical=new URL(match[1]);const response=await fetch(url+canonical.pathname);const html=await response.text();
   if(canonical.hostname!==receipt.hostname||response.status!==200||!html.includes('rel="canonical" href="'+canonical.href+'"')||!html.includes('content="index, follow"'))throw Error('Canonical route failed');
  }
 }else if((await fetch(url+'/sitemap.xml')).status!==404)throw Error('Unexpected staging sitemap');
 for(const [name,width,height] of [['wide',1440,1000],['narrow',390,844]]){
  const context=await browser.newContext({viewport:{width,height},colorScheme:'light',permissions:['clipboard-read','clipboard-write']});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url,{waitUntil:'networkidle'});await page.waitForFunction(()=>!document.getElementById('loading'),null,{timeout:60000});
  await page.waitForTimeout(500);
  const canvas=page.locator('canvas').first();const bounds=await canvas.boundingBox();if(!bounds||bounds.width<width-40)throw Error('Viewport');
  await writeFile(output+'/'+name+'-light.png', await captureWorkflowPanel(page,width));
  // Exercise the real Qt theme control, then prove its saved value survives reload.
  const inner=Math.min(1180,width-(width<760?36:96));
  await page.mouse.click((width+inner)/2-50,width<760?42:44);await page.keyboard.press('End');await page.keyboard.press('Enter');
  await page.waitForFunction(()=>localStorage.getItem('freeflight-theme')==='dark');
  await page.waitForTimeout(250);await writeFile(output+'/'+name+'-dark.png', await captureWorkflowPanel(page,width));
  await page.reload({waitUntil:'networkidle'});await page.waitForFunction(()=>!document.getElementById('loading'),null,{timeout:60000});
  if(await page.evaluate(()=>document.documentElement.dataset.theme)!=='dark')throw Error('Theme persistence');
  // The actual Qt Docs navigation must open the semantic reader.
  await page.mouse.click(width<760?240:1075,width<760?92:44);
  await page.locator('#docs-reader').waitFor({state:'visible'});
  const reader=page.locator('#docs-reader');
  if(await reader.locator('nav a').count()!==7)throw Error('Guide catalog');
  await page.getByLabel('Search guides').fill('workspaces');
  await reader.getByRole('link',{name:'Workspaces and trust',exact:true}).click();
  await page.getByLabel('Search guides').fill('');
  if(!page.url().includes('docs%2Fworkspaces.md'))throw Error('Document route');
  await reader.getByRole('link',{name:'Configuration',exact:true}).click();
  await page.waitForTimeout(100);
  const copy=reader.locator('pre').filter({hasText:'"trustedRoots"'}).first().getByRole('button',{name:'Copy code example'});await copy.click();
  await page.waitForFunction(()=>Array.from(document.querySelectorAll('.code-copy')).some(b=>b.textContent==='Copied'));
  if(await copy.textContent()!=='Copied')throw Error('Code copy');
  const copied=await page.evaluate(()=>navigator.clipboard.readText());if(!copied.includes('trustedRoots'))throw Error('Wrong source example');
  await page.goBack();await page.waitForTimeout(100);if(!page.url().includes('workspaces'))throw Error('History');
  await page.screenshot({path:output+'/'+name+'-docs-dark.png'});
  await page.evaluate(()=>freeflightTheme('light'));await page.screenshot({path:output+'/'+name+'-docs-light.png'});
  if(await reader.locator('script,img,iframe').count())throw Error('Unsafe docs element');
  for(const link of await reader.locator('article a[href]').evaluateAll(as=>as.map(a=>a.getAttribute('href'))))if(!/^(https?:|#docs\/)/.test(link))throw Error('Unexpected document link');
  await page.getByRole('button',{name:'Close documentation'}).click();
  if(await reader.isVisible())throw Error('Close reader');
  if(width>760){
    await context.route(company.split('#')[0],route=>route.fulfill({status:200,body:'Company destination test'}));
    const popupPromise=page.waitForEvent('popup');await page.mouse.click(417,900);const popup=await popupPromise;
    await popup.waitForURL(company);await popup.close();
  }
  await page.goto(url+'/review.html');
  if(await page.locator('section[id]').count()!==6)throw Error('Accessible sections');
  if(await page.locator('a').filter({hasText:'Company'}).getAttribute('href')!==company)throw Error('Environment Company link');
  if(/tglider|glider/i.test(await page.locator('body').innerText()))throw Error('Unrelated product copy');
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Horizontal overflow');
  evidence.push({name,width,height,themes:['light','dark'],docs:7,company,copy:true,history:true});await context.close();
 }
 // Verify system preference without a persisted override.
 const system=await browser.newContext({colorScheme:'dark'});const p=await system.newPage();await p.goto(url);await p.waitForFunction(()=>document.documentElement.dataset.theme==='dark');await system.close();
 if(errors.length)throw Error(errors.join('\n'));
 await writeFile(output+'/verification.json',JSON.stringify({environment:receipt.environment,sourceCommit:receipt.sourceCommit,evidence,errors},null,2));
 console.log('Desktop/mobile light/dark, persistence, source docs, search, history, copy and Company destinations passed.');
}finally{await browser.close();}
