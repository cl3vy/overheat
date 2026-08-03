// CONFIG fits short viewports with BOOT RIG fully visible and no scrollbar.
// Checks desktop short (1280x600) and mobile S (320x568) after a round so
// the config screen carries its worst-case furniture (HOTTEST / BEST BANK).
import { chromium } from 'playwright-core';

const url =
	'http://localhost:6001/iframe.html?id=mode-rigs-book--win-overclock-5-x&viewMode=story';

const viewports = [
	{ name: 'desktop-short', width: 1280, height: 600 },
	{ name: 'mobile-s', width: 320, height: 568 },
];

const browser = await chromium.launch({ channel: 'chrome', headless: true });

const measure = (page) =>
	page.evaluate(() => {
		const boot = document.querySelector('.boot-btn');
		const rect = boot?.getBoundingClientRect();
		const scroller = document.scrollingElement;
		return {
			bootVisible: rect
				? rect.top >= 0 && rect.bottom <= window.innerHeight
				: false,
			bootBottom: rect ? Math.round(rect.bottom) : null,
			innerHeight: window.innerHeight,
			overflow: scroller ? scroller.scrollHeight - scroller.clientHeight : null,
		};
	});

let failed = false;

try {
	// warm a post-run config once at desktop size, then resize for each check
	const page = await browser.newPage({ viewport: viewports[0] });
	page.on('pageerror', (err) => console.log('[pageerror]', err.message));

	await page.goto(url, { waitUntil: 'domcontentloaded' });
	await page.waitForFunction(() => {
		const btn = document.querySelector('button.action');
		return btn && !btn.disabled;
	});
	await page.waitForTimeout(300);

	console.log('--- first-run desktop-short ---', await measure(page));

	await page.click('.turbo-btn');
	await page.click('button.action');
	await page.waitForFunction(() => document.body.innerText.includes('BOOT AGAIN'), {
		timeout: 60000,
	});
	await page.click('text=RETURN TO RIG SELECT');
	await page.waitForFunction(() => document.body.innerText.includes('CASH OUT TARGET'));
	await page.waitForTimeout(300);

	for (const viewport of viewports) {
		await page.setViewportSize({ width: viewport.width, height: viewport.height });
		await page.waitForTimeout(200);
		const result = await measure(page);
		console.log(`--- post-run ${viewport.name} ---`, result);
		await page.screenshot({ path: `/tmp/overheat-fit-${viewport.name}.png` });
		if (!result.bootVisible || (result.overflow ?? 0) > 0) {
			console.log(`FIT SMOKE FAILED at ${viewport.name}: boot clipped or page scrolls`);
			failed = true;
		}
	}

	await page.close();
	if (failed) {
		process.exitCode = 1;
	} else {
		console.log('FIT SMOKE OK');
	}
} catch (err) {
	console.error('FIT SMOKE FAILED:', err.message);
	process.exitCode = 1;
} finally {
	await browser.close();
}
