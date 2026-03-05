const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });

  const outDir = path.join(__dirname, '..', 'docs', 'screenshots');

  // 1. Main Pipeline Console (Next.js web app)
  console.log('Capturing pipeline console...');
  const page1 = await context.newPage();
  await page1.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 30000 });
  await page1.waitForTimeout(3000);
  await page1.screenshot({ path: path.join(outDir, '01-dashboard.png'), fullPage: true });
  console.log('  -> 01-dashboard.png saved');

  // 2. Dashboard (Neural Network + Metrics)
  try {
    console.log('Capturing /dashboard page...');
    await page1.goto('http://localhost:3000/dashboard', { waitUntil: 'networkidle', timeout: 30000 });
    // Wait for metrics to load (spinner disappears, metrics cards appear)
    await page1.waitForSelector('text=Calories', { timeout: 15000 }).catch(() => {});
    await page1.waitForTimeout(3000);
    await page1.screenshot({ path: path.join(outDir, '02-dashboard-detail.png'), fullPage: true });
    console.log('  -> 02-dashboard-detail.png saved');
  } catch (e) {
    console.log('  -> /dashboard error:', e.message);
  }

  // 3. FastAPI Swagger UI
  console.log('Capturing API docs...');
  const page2 = await context.newPage();
  await page2.goto('http://localhost:8000/docs', { waitUntil: 'networkidle', timeout: 30000 });
  await page2.waitForTimeout(3000);
  await page2.screenshot({ path: path.join(outDir, '03-api-docs.png'), fullPage: true });
  console.log('  -> 03-api-docs.png saved');

  // 4. API Root endpoint
  console.log('Capturing API root...');
  const page3 = await context.newPage();
  await page3.goto('http://localhost:8000/', { waitUntil: 'networkidle', timeout: 15000 });
  await page3.waitForTimeout(1000);
  await page3.screenshot({ path: path.join(outDir, '04-api-health.png') });
  console.log('  -> 04-api-health.png saved');

  // 5. Account & Privacy page
  try {
    console.log('Capturing /account page...');
    await page1.goto('http://localhost:3000/account', { waitUntil: 'networkidle', timeout: 15000 });
    await page1.waitForTimeout(2000);
    await page1.screenshot({ path: path.join(outDir, '05-account-privacy.png'), fullPage: true });
    console.log('  -> 05-account-privacy.png saved');
  } catch (e) {
    console.log('  -> /account not available, skipping');
  }

  await browser.close();
  console.log('\nAll screenshots captured successfully!');
})();
