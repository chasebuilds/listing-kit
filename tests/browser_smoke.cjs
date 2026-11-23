// Real-browser check of the built demo site. Usage: node tests/browser_smoke.cjs <site-dir>
// Needs Playwright (PW_PATH can point at an existing install) and a built site (see README).
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require(process.env.PW_PATH || 'playwright');

const site = path.resolve(process.argv[2] || 'out');
const url = (p) => pathToFileURL(path.join(site, p)).href;
let failed = 0;
const check = (ok, name) => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}`); if (!ok) failed++; };

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => {
    if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text());
  });

  await page.goto(url('maple-court/index.html'));
  check((await page.textContent('#gal-count')).trim() === '1 / 6', 'gallery starts at 1 / 6');
  await page.click('#gal-next');
  await page.waitForFunction(() => document.getElementById('gal-count').textContent.trim() === '2 / 6', null, { timeout: 5000 })
    .then(() => check(true, 'next button moves to photo 2'), () => check(false, 'next button moves to photo 2'));

  await page.click('#track figure:nth-child(2) button.open');
  check(await page.evaluate(() => document.getElementById('lightbox').open), 'lightbox opens');
  const cap1 = await page.textContent('#lb-cap');
  await page.keyboard.press('ArrowRight');
  check((await page.textContent('#lb-cap')) !== cap1, 'arrow key changes lightbox photo');
  await page.keyboard.press('Escape');
  check(!(await page.evaluate(() => document.getElementById('lightbox').open)), 'Escape closes lightbox');

  const before = await page.textContent('#m-total');
  await page.fill('#m-down', '50');
  const after = await page.textContent('#m-total');
  check(before !== after && /\$[\d,]+ \/ month/.test(after), `payment estimate updates (${before} -> ${after})`);

  await page.fill('#f-name', 'Test Person');
  await page.fill('#f-email', 'test@example.com');
  await page.click('#lead-form button[type=submit]');
  check(/email app/.test(await page.textContent('#lead-status')), 'lead form reports mailto hand-off');

  check((await page.getAttribute('#share-email', 'href')).startsWith('mailto:?subject='), 'share email link is set');
  check((await page.getAttribute('#share-x', 'href')).includes('twitter.com/intent/tweet'), 'share X link is set');

  await page.evaluate(() => document.getElementById('map').scrollIntoView());
  await page.waitForSelector('#map.leaflet-container', { timeout: 10000 })
    .then(() => check(true, 'map loads when scrolled into view'), () => check(false, 'map loads when scrolled into view'));
  check((await page.textContent('.leaflet-control-attribution')).includes('OpenStreetMap'), 'map shows OpenStreetMap attribution');

  await page.goto(url('maple-court/flyer.html'));
  check(await page.isVisible('#print'), 'flyer page has a print button');

  await page.goto(url('checker/index.html'));
  const n = await page.locator('#findings li').count();
  check(n >= 6, `checker lists findings for the sample (${n})`);
  await page.fill('#text', 'Three bedrooms, a deck and a two car garage.');
  await page.waitForTimeout(400);
  check(/No marked wording/.test(await page.textContent('#summary')), 'checker is quiet on clean text');
  await page.fill('#text', 'No kids.');
  await page.waitForTimeout(400);
  check((await page.locator('mark.avoid').count()) === 1, 'checker marks "no kids" as avoid');

  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto(url('alder-street/index.html'));
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check(overflow <= 0, `no horizontal scroll at 360px wide (overflow ${overflow})`);

  check(errors.length === 0, `no page errors${errors.length ? ': ' + errors.join(' | ') : ''}`);
  await browser.close();
  process.exit(failed ? 1 : 0);
})();
