// Screenshot helper. Run the scraper first so data/ has a report, then:
//   npm i playwright && npx playwright install chromium
//   OUT=../ node scripts/screenshots.js
const { chromium } = require("playwright");
const path = require("path");

const CODE = path.resolve(__dirname, "..");
const OUT = process.env.OUT || path.resolve(CODE, "..");
const SIZE = { width: 1280, height: 769 };

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: SIZE, deviceScaleFactor: 2 });

  const report = await ctx.newPage();
  await report.goto("file://" + path.join(CODE, "data", "report-2.html"), { waitUntil: "networkidle" });
  await report.waitForTimeout(1200);
  await report.screenshot({ path: `${OUT}/shot1.png` });
  console.log("shot1 done");

  const view = await ctx.newPage();
  await view.goto("file://" + path.join(CODE, "data", "run-view.html"), { waitUntil: "networkidle" });
  await view.waitForTimeout(1200);
  await view.screenshot({ path: `${OUT}/shot2.png` });
  console.log("shot2 done");

  const latest = await ctx.newPage();
  await latest.goto("file://" + path.join(CODE, "data", "report-3.html"), { waitUntil: "networkidle" });
  await latest.waitForTimeout(900);
  await latest.evaluate(() => {
    const el = document.querySelectorAll("section")[1];
    if (el) el.scrollIntoView({ block: "start" });
    window.scrollBy(0, -18);
  });
  await latest.waitForTimeout(600);
  await latest.screenshot({ path: `${OUT}/shot3.png` });
  console.log("shot3 done");

  await ctx.close();
  await browser.close();
})();
