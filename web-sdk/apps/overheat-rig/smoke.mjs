// Headless smoke test: load a Storybook story, run one round, report result.
// Usage: node smoke.mjs [storyId] [timeoutMs]
import { chromium } from 'playwright-core';

const storyId = process.argv[2] ?? 'mode-rigs-book--win-eco-1-5x';
const timeoutMs = Number(process.argv[3] ?? 60000);
const url = `http://localhost:6001/iframe.html?id=${storyId}&viewMode=story`;

const browser = await chromium.launch({
	channel: 'chrome',
	headless: true,
});
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on('console', (msg) => {
	if (msg.type() === 'error') console.log('[console error]', msg.text());
});
page.on('pageerror', (err) => console.log('[pageerror]', err.message));

try {
	await page.goto(url, { waitUntil: 'domcontentloaded' });

	// wait for the storybook Action button (drives the fixture book, no RGS needed)
	await page.waitForFunction(
		() => {
			const btn = document.querySelector('button.action');
			return btn && !btn.disabled;
		},
		{ timeout: 30000 },
	);
	console.log('story ready');

	await page.click('button.action');
	console.log('action clicked, waiting for round to settle...');

	// wait for the settled screen (BOOT AGAIN / RETURN buttons) or win overlay
	await page.waitForFunction(
		() => {
			const text = document.body.innerText;
			return (
				text.includes('BOOT AGAIN') ||
				text.includes('RETURN TO RIG SELECT') ||
				text.includes('MELTDOWN')
			);
		},
		{ timeout: timeoutMs },
	);

	const snippet = await page.evaluate(() =>
		document.body.innerText.replace(/\n{2,}/g, '\n').slice(0, 1500),
	);
	console.log('--- settled screen text ---');
	console.log(snippet);
	await page.screenshot({ path: '/tmp/overheat-smoke.png' });
	console.log('screenshot: /tmp/overheat-smoke.png');
	console.log('SMOKE OK');
} catch (err) {
	console.error('SMOKE FAILED:', err.message);
	try {
		await page.screenshot({ path: '/tmp/overheat-smoke-fail.png' });
		console.log('failure screenshot: /tmp/overheat-smoke-fail.png');
	} catch {}
	process.exitCode = 1;
} finally {
	await browser.close();
}
