// One-off check: run a round, return to rig select, verify the retention
// strip (peaks/rank/no P-L) and the fairness panel render.
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
	await page.click('.turbo-btn');
	await page.click('button.action');
	await page.waitForFunction(() => document.body.innerText.includes('RETURN TO RIG SELECT'), {
		timeout: 60000,
	});
	await page.click('text=RETURN TO RIG SELECT');
	await page.waitForFunction(() => document.body.innerText.includes('CASH OUT TARGET'));
	await page.waitForTimeout(400);

	const text = await page.evaluate(() =>
		document.body.innerText.replace(/\n{2,}/g, '\n').slice(0, 2000),
	);
	console.log('--- rig select ---');
	console.log(text);
	await page.screenshot({ path: '/tmp/overheat-select.png' });

	const banned = ['session ±', 'wins ', 'full-send odds', 'profit ~1 in', 'OPERATOR RECORD'];
	const leaks = banned.filter((phrase) => text.includes(phrase));
	console.log(leaks.length ? `EV LEAKS FOUND: ${leaks.join(', ')}` : 'no EV leak strings');

	await page.click('text=[FAIRNESS]');
	await page.waitForFunction(() => document.body.innerText.includes('PROVABLY FAIR'));
	const fair = await page.evaluate(() => document.querySelector('.fairness-pop')?.innerText);
	console.log('--- fairness panel ---');
	console.log(fair);
	await page.screenshot({ path: '/tmp/overheat-fairness.png' });
	console.log('SELECT SMOKE OK');
} catch (err) {
	console.error('SELECT SMOKE FAILED:', err.message);
	await page.screenshot({ path: '/tmp/overheat-select-fail.png' });
	process.exitCode = 1;
} finally {
	await browser.close();
}
