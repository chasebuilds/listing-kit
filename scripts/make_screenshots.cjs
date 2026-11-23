// Takes the README screenshots from a built site. Usage: node scripts/make_screenshots.cjs <site-dir>
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require(process.env.PW_PATH || 'playwright');

const site = path.resolve(process.argv[2] || 'out');
const docs = path.resolve(__dirname, '..', 'docs');
const url = (p) => pathToFileURL(path.join(site, p)).href;

(async () => {
  const browser = await chromium.launch();
  const shot = async (rel, file, w, h, opts = {}) => {
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: opts.scale || 1 });
    await page.goto(url(rel));
    await page.waitForTimeout(800);
    if (opts.map) {
      await page.evaluate(() => document.getElementById('map').scrollIntoView({ block: 'center' }));
      await page.waitForSelector('#map .leaflet-tile-loaded', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(1500);
    }
    if (opts.scrollTo) await page.evaluate((y) => window.scrollTo(0, y), opts.scrollTo);
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(docs, file) });
    await page.close();
  };
  await shot('maple-court/index.html', 'preview.png', 1280, 860, { scrollTo: 0 });
  await shot('alder-street/index.html', 'heritage.png', 1280, 860);
  await shot('checker/index.html', 'checker.png', 1100, 1500);
  await shot('maple-court/index.html', 'map.png', 1280, 860, { map: true });
  await shot('maple-court/index.html', 'mobile.png', 390, 844, { scale: 2 });
  await shot('maple-court/flyer.html', 'flyer.png', 900, 1100);
  await shot('index.html', 'index.png', 1180, 1000);
  await browser.close();
})();
