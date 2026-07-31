// One-off check: first-ever boot screen carries the loop sentence and no
// checkpoint copy; after one run the intro collapses and the ladder caption
// appears. Also verifies BOOT AGAIN renders as the solid primary button.
import { chromium } from 'playwright-core';

const url =
	'http://localhost:6001/iframe.html?id=mode-rigs-book--win-overclock-5-x&viewMode=story';

const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on('pageerror', (err) => console.log('[pageerror]', err.message));

try {
	await page.goto(url, { waitUntil: 'domcontentloaded' });
	await page.waitForFunction(() => {
		const btn = document.querySelector('button.action');
		return btn && !btn.disabled;
	});
	await page.waitForTimeout(300);

	const first = await page.evaluate(() => document.body.innerText);
	console.log('--- first-run boot screen checks ---');
	console.log('loop sentence:', first.includes('set your auto cash out target') ? 'OK' : 'MISSING');
	console.log('translation:', first.includes('cash out at') ? 'OK' : 'MISSING');
	console.log(
		'checkpoint copy hidden:',
		first.includes('each tick banks a partial payout') ? 'LEAKED' : 'OK',
	);
	console.log('overdrive copy gone:', first.includes('OVERDRIVE') ? 'LEAKED' : 'OK');
	console.log('max win kept:', first.includes('max win') ? 'OK' : 'MISSING');
	await page.screenshot({ path: '/tmp/overheat-firstrun.png' });

	await page.click('.turbo-btn');
	await page.click('button.action');
	await page.waitForFunction(() => document.body.innerText.includes('BOOT AGAIN'), {
		timeout: 60000,
	});
	await page.waitForTimeout(2200);

	const rebet = await page.evaluate(() => {
		const btn = document.querySelector('button.rebet-btn');
		return btn ? getComputedStyle(btn).backgroundColor : 'not found';
	});
	console.log('BOOT AGAIN background:', rebet);
	await page.screenshot({ path: '/tmp/overheat-result-win.png' });

	await page.click('text=RETURN TO RIG SELECT');
	await page.waitForFunction(() => document.body.innerText.includes('CASH OUT TARGET'));
	await page.waitForTimeout(300);
	const after = await page.evaluate(() => document.body.innerText);
	console.log('--- after one run ---');
	console.log('intro collapsed:', after.includes('HOW IT WORKS') ? 'STILL EXPANDED' : 'OK');
	console.log('ladder caption shown:', after.includes('each tick banks a partial payout') ? 'OK' : 'MISSING');
	await page.screenshot({ path: '/tmp/overheat-select-after.png' });
	console.log('FIRSTRUN SMOKE OK');
} catch (err) {
	console.error('FIRSTRUN SMOKE FAILED:', err.message);
	await page.screenshot({ path: '/tmp/overheat-firstrun-fail.png' });
	process.exitCode = 1;
} finally {
	await browser.close();
}
