// Captures the gallery images from real outputs in data/ (run the watcher first, and save
// its output and the test output as data/run-2.log and data/pytest.log).
//   npm install && node scripts/gallery.js ../raw ../
// raw/ gets the inputs for the shared hero/deliverables renderer; the second
// folder gets shot1-3 (1280x769 raw captures).
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
const LIGHT = { bg: "#F6F3EE", card: "#FFFFFF", raised: "#F1EDE6", line: "#E4DED4", ink: "#1B1A17", muted: "#6E6A62", faint: "#9A958C", ok: "#3F8A55", bad: "#C2543F", acc: "#D9782A" };
const DARK = { bg: "#15171B", card: "#1E2126", raised: "#262A30", line: "#2F333A", ink: "#F3EFE7", muted: "#A7A39B", faint: "#77736C", ok: "#7CBA8C", bad: "#E8806E", acc: "#F2994A" };

function shell(T, inner, width) {
  return `<!doctype html><html><head><style>
@font-face{font-family:Mono;src:url(${font("mono-500.woff2")})}
@font-face{font-family:Plex;font-weight:400;src:url(${font("plex-400.woff2")})}
@font-face{font-family:Plex;font-weight:600;src:url(${font("plex-600.woff2")})}
@font-face{font-family:Brico;src:url(${font("bricolage-700.woff2")})}
body{margin:0;background:${T.bg};padding:32px;font-family:Plex;color:${T.ink}}
.card{width:${width}px;background:${T.card};border:1px solid ${T.line};border-radius:10px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.06),0 12px 32px rgba(0,0,0,.08)}
.bar{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid ${T.line};font-size:13px;color:${T.muted}}
.bar i{width:11px;height:11px;border-radius:50%;background:${T.line}}
.bar span{margin-left:8px}
pre{margin:0;padding:20px 24px 24px;font-family:Mono;font-size:15px;line-height:1.75;white-space:pre-wrap}
.cmd{color:${T.acc}}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:10px 14px;border-bottom:1px solid ${T.line};border-right:1px solid ${T.line};text-align:left;white-space:nowrap}
th{font-family:Mono;font-weight:500;font-size:12px;color:${T.muted};background:${T.raised}}
td.n{font-family:Mono;text-align:right}
td.rowno{font-family:Mono;color:${T.faint};background:${T.raised};text-align:center;width:36px}
</style></head><body>${inner}</body></html>`;
}

function terminalCard(T, command, text, title = "Terminal", width = 880) {
  const lines = text.split("\n").filter((l, i, a) => !(l.trim() === "" && i === a.length - 1)).map((l) => {
    let h = esc(l);
    h = h.replace(/(page \d+)/, `<span style="color:${T.ok}">$1</span>`);
    h = h.replace(/(\d+ changes against run \d+, including \d+ price drops)/, `<span style="color:${T.acc}">$1</span>`);
    h = h.replace(/(PASSED)/, `<b style="color:${T.ok}">$1</b>`).replace(/(\d+ passed[^\n]*)/, `<b style="color:${T.ok}">$1</b>`);
    return h;
  }).join("\n");
  return shell(T, `<div class="card"><div class="bar"><i></i><i></i><i></i><span>${esc(title)}</span></div><pre><span class="cmd">$ ${esc(command)}</span>\n${lines}</pre></div>`, width);
}

function csvCard(T, file, rows = 11, width = 1060) {
  const [head, ...body] = fs.readFileSync(path.join(DATA, file), "utf8").trim().split("\n").map((l) => {
    const out = []; let cur = "", q = false;
    for (const ch of l) { if (ch === '"') q = !q; else if (ch === "," && !q) { out.push(cur); cur = ""; } else cur += ch; }
    out.push(cur); return out;
  });
  const keep = ["title", "price", "currency", "rating", "in_stock", "category"];
  const idx = keep.map((k) => head.indexOf(k));
  const cols = "ABCDEF".split("");
  let html = `<div class="card"><div class="bar"><span style="margin:0;font-family:Mono">${esc(file)}</span><span style="margin-left:auto">${body.length} rows</span></div><table><thead><tr><th></th>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>`;
  html += `<tr><td class="rowno">1</td>${keep.map((k) => `<td style="font-weight:600">${k}</td>`).join("")}</tr>`;
  body.slice(0, rows).forEach((r, i) => {
    html += `<tr><td class="rowno">${i + 2}</td>${idx.map((j, c) => {
      const v = r[j]; const num = c === 1 || c === 3;
      const t = c === 0 && v.length > 44 ? v.slice(0, 44) + "..." : v;
      return `<td class="${num ? "n" : ""}">${esc(t)}</td>`;
    }).join("")}</tr>`;
  });
  return shell(T, html + "</tbody></table></div>", width);
}

(async () => {
  const b = await chromium.launch({ channel: "chromium" });
  const page = async (w, h) => b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  const report = (n, theme) => "file://" + path.join(DATA, `report-${n}.html`) + (theme ? "" : "");

  // hero: dark report, KPIs and the change table
  let p = await page(1440, 1000);
  await p.goto(report(2));
  // the gallery frame bleeds off the right edge, so dock the report column left for this capture
  await p.evaluate(() => {
    document.documentElement.dataset.theme = "dark";
    const w = document.querySelector(".wrap"); w.style.margin = "0 0 0 24px"; w.style.maxWidth = "1100px";
  });
  await p.waitForTimeout(400);
  await p.screenshot({ path: path.join(RAW, "hero_dark.png") });
  await p.close();

  // raw gallery shots, dark
  p = await page(1280, 769);
  await p.goto(report(2));
  await p.evaluate(() => { document.documentElement.dataset.theme = "dark"; });
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(SHOTS, "shot1.png") });
  await p.evaluate(() => { document.querySelector(".grid2").scrollIntoView({ block: "start" }); window.scrollBy(0, -32); });
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(SHOTS, "shot2.png") });
  await p.goto(report(3));
  await p.evaluate(() => { document.documentElement.dataset.theme = "dark"; });
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(RAW, "empty_dark.png") });

  // light tiles for the deliverables image
  await p.goto(report(2));
  await p.evaluate(() => { document.documentElement.dataset.theme = "light"; });
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(RAW, "report_light.png") });
  await p.close();

  const card = async (html, out) => {
    const q = await page(1200, 400);
    await q.setContent(html);
    await q.waitForTimeout(200);
    await q.locator(".card").screenshot({ path: path.join(RAW, out) });
    await q.close();
  };
  await card(csvCard(LIGHT, "run-2.csv"), "csv_light.png");
  await card(terminalCard(LIGHT, "python -m watcher.cli run --max-pages 2", fs.readFileSync(path.join(DATA, "run-2.log"), "utf8")), "terminal_light.png");
  await card(terminalCard(LIGHT, "python -m pytest tests -v", fs.readFileSync(path.join(DATA, "pytest.log"), "utf8"), "Terminal", 980), "tests_light.png");

  // shot3: the real run output and the exported spreadsheet, dark
  await card(terminalCard(DARK, "python -m watcher.cli run --max-pages 2", fs.readFileSync(path.join(DATA, "run-2.log"), "utf8"), "Terminal", 640), "terminal_dark.png");
  await card(csvCard(DARK, "run-2.csv", 9, 760), "csv_dark.png");
  await b.close();
  console.log("gallery captures written to", RAW, "and", SHOTS);
})();
