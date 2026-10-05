// Captures the gallery inputs from real outputs in data/ (run fixtures/make_history.py first).
//   npm install && node scripts/gallery.js ../raw ..
// raw/ gets the inputs for the shared cover renderer; the second folder gets shot1-3.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const CODE = path.resolve(__dirname, "..");
const RAW = path.resolve(process.argv[2] || path.join(CODE, "..", "raw"));
const SHOTS = path.resolve(process.argv[3] || path.join(CODE, ".."));
const DATA = path.join(CODE, "data");
const FONTS = path.join(CODE, "watcher", "assets", "fonts");
fs.mkdirSync(RAW, { recursive: true });
const font = (f) => "data:font/woff2;base64," + fs.readFileSync(path.join(FONTS, f)).toString("base64");
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const reports = fs.readdirSync(DATA).filter((f) => /^report-\d+\.html$/.test(f)).map((f) => +f.match(/\d+/)[0]).sort((a, b) => b - a);
const latest = reports[0];

function csvSheet(file, rows = 12) {
  const lines = fs.readFileSync(path.join(DATA, file), "utf8").trim().split("\n");
  const parse = (l) => { const o = []; let c = "", q = false; for (const ch of l) { if (ch === '"') q = !q; else if (ch === "," && !q) { o.push(c); c = ""; } else c += ch; } o.push(c); return o; };
  const head = parse(lines[0]);
  const keep = ["sku", "title", "price", "rating", "in_stock"];
  const idx = keep.map((k) => head.indexOf(k));
  const body = lines.slice(1, rows + 1).map(parse);
  return `<!doctype html><html><head><style>
@font-face{font-family:Karla;font-weight:400;src:url(${font("karla-400.woff2")})}
@font-face{font-family:Karla;font-weight:700;src:url(${font("karla-700.woff2")})}
body{margin:0;background:#F3EFE6;padding:28px;font-family:Karla;color:#1A1A1A;font-variant-numeric:tabular-nums}
.card{width:880px;background:#FBF9F4;border:1px solid #DCD5C8}
.bar{padding:12px 16px;border-bottom:1px solid #DCD5C8;font-size:14px;color:#5B574F;display:flex;justify-content:space-between}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:8px 12px;border-bottom:1px solid #E7E1D5;border-right:1px solid #E7E1D5;text-align:left;white-space:nowrap}
th{font-weight:700;background:#F3EFE6}
td.n{text-align:right}
td.row{color:#8A857B;text-align:center;width:34px;background:#F3EFE6}
</style></head><body><div class="card"><div class="bar"><span>${esc(file)}, opened in a spreadsheet</span><span>${lines.length - 1} rows</span></div>
<table><tr><th></th>${keep.map((k) => `<th>${k}</th>`).join("")}</tr>
${body.map((r, i) => `<tr><td class="row">${i + 1}</td>${idx.map((j, c) => { let v = r[j]; if (c === 1 && v.length > 40) v = v.slice(0, 40) + "..."; return `<td class="${c === 2 || c === 3 ? "n" : ""}">${esc(v)}</td>`; }).join("")}</tr>`).join("")}
</table></div></body></html>`;
}

(async () => {
  const b = await chromium.launch({ channel: "chromium" });
  const open = async (w, h, file, scale = 2) => {
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: scale });
    await p.goto("file://" + path.join(DATA, file));
    await p.waitForTimeout(1100); // the strike and sparkline animations finish
    return p;
  };

  // cover: the catalog page with today's strikes, as a flat artifact
  let p = await open(1200, 1000, `report-${latest}.html`);
  const sheet = await p.locator(".sheet").boundingBox();
  await p.screenshot({ path: `${RAW}/catalog_page.png`, clip: { x: sheet.x, y: 0, width: sheet.width, height: 900 } });
  const runs = await p.locator("table.runs").boundingBox();
  await p.screenshot({ path: `${RAW}/run_history.png`, fullPage: true, clip: { x: runs.x - 24, y: runs.y - 80, width: runs.width + 48, height: Math.min(runs.height + 104, 820) } });
  await p.close();

  p = await open(1280, 769, `report-${latest}.html`, 1);
  await p.screenshot({ path: path.join(SHOTS, "shot1.png") });
  await p.evaluate(() => document.querySelector(".list").scrollIntoView({ block: "center" }));
  await p.screenshot({ path: path.join(SHOTS, "shot2.png") });
  await p.close();

  // quiet day: the empty state
  const quiet = reports.find((n) => fs.readFileSync(path.join(DATA, `report-${n}.html`), "utf8").includes("Nothing moved since yesterday."));
  p = await open(1200, 760, `report-${quiet}.html`);
  await p.screenshot({ path: `${RAW}/no_changes.png` });
  await p.close();

  // failed day
  const failed = reports.find((n) => fs.readFileSync(path.join(DATA, `report-${n}.html`), "utf8").includes("check failed."));
  if (failed) {
    p = await open(1280, 769, `report-${failed}.html`, 1);
    await p.screenshot({ path: path.join(SHOTS, "shot3.png") });
    await p.close();
  }

  // the alert email
  p = await open(760, 520, `alerts/run-${latest}.html`);
  const mail = await p.locator("table").first().boundingBox();
  await p.screenshot({ path: `${RAW}/alert_email.png`, clip: { x: mail.x - 28, y: mail.y - 28, width: mail.width + 56, height: mail.height + 56 } });
  await p.close();

  // the CSV
  p = await b.newPage({ viewport: { width: 960, height: 600 }, deviceScaleFactor: 2 });
  await p.setContent(csvSheet(`run-${latest}.csv`));
  await p.locator(".card").screenshot({ path: `${RAW}/csv.png` });
  await p.close();
  await b.close();
  console.log("captured from run", latest, "quiet run", quiet, "failed run", failed);
})();
