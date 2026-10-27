// הרצה מקומית: npm i playwright && npx playwright install chromium && node scripts/capture.mjs [דקות בין סבבים, ברירת מחדל 5]
// פותח את מפת ההצבעות, שומר כל תגובת JSON שהאתר מושך, ודוחף לענף כדי שאוכל לנתח.
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";

const URL = "https://mapvotes.bechirot.gov.il/";
const EVERY_MIN = +(process.argv[2] || 5);
const BRANCH = "claude/friendly-fermat-l8pz9n";

async function capture() {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const dir = `data/live/${stamp}`;
  mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage();
  let n = 0;
  const index = [];
  page.on("response", async r => {
    try {
      const type = r.headers()["content-type"] || "";
      if (!/json/.test(type) && !/\.(json|geojson)(\?|$)/.test(r.url())) return;
      const body = await r.text();
      const file = `${String(++n).padStart(3, "0")}.json`;
      writeFileSync(`${dir}/${file}`, body);
      index.push({ file, url: r.url(), bytes: body.length });
    } catch {}
  });
  await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(5000);
  writeFileSync(`${dir}/index.json`, JSON.stringify(index, null, 2));
  await page.screenshot({ path: `${dir}/screen.png` });
  await browser.close();
  console.log(`${stamp}: נשמרו ${n} קבצים`);
  try {
    execSync(`git add data/live && git commit -qm "live capture ${stamp}" && git push -q origin HEAD:${BRANCH}`, { stdio: "inherit" });
  } catch (e) { console.error("דחיפה נכשלה:", e.message); }
}

while (true) {
  try { await capture(); } catch (e) { console.error(e.message); }
  await new Promise(r => setTimeout(r, EVERY_MIN * 60000));
}
