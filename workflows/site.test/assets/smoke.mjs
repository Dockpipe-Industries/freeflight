import { chromium } from 'playwright';
import { writeFile } from 'node:fs/promises';
const [url, output] = process.argv.slice(2);
const browser = await chromium.launch({ channel: 'chromium', args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const receipt = await (await fetch(`${url}/release.json`)).json();
const robots = await (await fetch(`${url}/robots.txt`)).text();
if (receipt.environment === 'production') {
  const sitemap = await (await fetch(`${url}/sitemap.xml`)).text();
  if (sitemap.includes('staging') || sitemap.includes('localhost') || robots.includes('Disallow: /')) throw new Error('Invalid production indexing');
  for (const match of sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)) {
    const canonical = new URL(match[1]);
    if (canonical.hostname !== receipt.hostname) throw new Error('Wrong sitemap host');
    const response = await fetch(url + canonical.pathname);
    const html = await response.text();
    if (response.status !== 200 || !html.includes(`rel="canonical" href="${canonical.href}"`) || !html.includes('content="index, follow"')) throw new Error('Canonical route failed');
  }
} else if (!robots.includes('Disallow: /') || (await fetch(`${url}/sitemap.xml`)).status !== 404) throw new Error('Invalid staging indexing');
const errors = [];
const evidence = [];
try {
  for (const [name, width, height] of [['wide', 1440, 1000], ['narrow', 390, 844]]) {
    const page = await browser.newPage({ viewport: { width, height } });
    page.on('pageerror', error => { errors.push(error.message); console.error(error.message); });
    page.on('console', message => { console.log('browser:', message.type(), message.text()); if (message.type() === 'error') errors.push(message.text()); });
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => !document.getElementById('loading'), null, { timeout: 60000 });
    const canvas = page.locator('canvas').first();
    await canvas.waitFor({ state: 'visible' });
    const bounds = await canvas.boundingBox();
    if (!bounds || bounds.width < width - 40 || bounds.height < 300) throw new Error('Qt canvas does not fit viewport');
    const cdp = await page.context().newCDPSession(page);
    const shot = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    await writeFile(`${output}/${name}.png`, Buffer.from(shot.data, 'base64'));
    await cdp.detach();
    await page.mouse.click(170, 80);
    const afterClick = await page.context().newCDPSession(page);
    const navigationShot = await afterClick.send('Page.captureScreenshot', { format: 'png' });
    await writeFile(`${output}/${name}-installation.png`, Buffer.from(navigationShot.data, 'base64'));
    await afterClick.detach();
    evidence.push({ name, width, height, canvas: bounds, navigation: 'Installation' });
    await page.goto(`${url}/review.html`);
    if (await page.locator('section[id]').count() !== 6) throw new Error('Fallback must contain six sections');
    await page.close();
  }
  if (errors.length) throw new Error(errors.join('\n'));
  await writeFile(`${output}/verification.json`, JSON.stringify({ renderer: 'qt-quick-wasm', environment: receipt.environment, hostname: receipt.hostname, browser: await browser.version(), evidence, errors }, null, 2));
  console.log('Qt WebAssembly rendered at wide and narrow widths; six-section fallback verified.');
} finally { await browser.close(); }
