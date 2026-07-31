<script lang="ts">
	import { untrack } from 'svelte';

	import { stateBet } from 'state-shared';
	import { waitForTimeout } from 'utils-shared/wait';

	import { BOOK_AMOUNT_SCALE } from '../game/constants';
	import { stateGame } from '../game/stateGame.svelte';
	import { playWinFanfare } from '../game/sound';

	type Tier = {
		label: string;
		durationMs: number;
		glyphCount: number;
		level: number;
	};

	const tierFor = (target: number): Tier => {
		if (target >= 100) return { label: 'LEGENDARY RUN', durationMs: 6500, glyphCount: 110, level: 5 };
		if (target >= 25) return { label: 'MASSIVE BANK', durationMs: 5000, glyphCount: 80, level: 4 };
		if (target >= 10) return { label: 'HUGE BANK', durationMs: 4200, glyphCount: 60, level: 3 };
		if (target >= 5) return { label: 'BIG BANK', durationMs: 3600, glyphCount: 45, level: 2 };
		return { label: 'CLEAN BANK', durationMs: 2800, glyphCount: 30, level: 1 };
	};

	const GLYPHS = '$¤01▓ΞÐ+';

	type RainGlyph = {
		char: string;
		left: number;
		delayMs: number;
		durationMs: number;
		fontSize: number;
	};

	let visible = $state(false);
	let tier = $state<Tier>(tierFor(1.5));
	let displayedMW = $state(0);
	let rain = $state<RainGlyph[]>([]);
	let runId = 0;

	const finalWinMW = () =>
		(stateBet.winBookEventAmount / BOOK_AMOUNT_SCALE) * stateBet.wageredBetAmount;

	const formatMW = (value: number) =>
		value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

	const makeRain = (count: number): RainGlyph[] =>
		Array.from({ length: count }, () => ({
			char: GLYPHS[Math.floor(Math.random() * GLYPHS.length)],
			left: Math.random() * 100,
			delayMs: Math.random() * 1800,
			durationMs: 1600 + Math.random() * 1800,
			fontSize: 0.8 + Math.random() * 1.4,
		}));

	const dismiss = () => {
		visible = false;
		runId += 1;
	};

	const celebrate = async () => {
		const id = ++runId;
		// let the bank moment land first: LOCKED stamp, fly-to-balance,
		// header count-up -- then take over the screen
		await waitForTimeout(stateBet.isTurbo ? 250 : 1400);
		if (runId !== id || stateGame.phase !== 'banked') return;
		tier = tierFor(stateGame.targetTemp);
		const durationMs = stateBet.isTurbo ? 1300 : tier.durationMs;

		rain = makeRain(stateBet.isTurbo ? 20 : tier.glyphCount);
		displayedMW = 0;
		visible = true;
		playWinFanfare(tier.level);

		// count the payout up from zero
		const target = finalWinMW();
		const countMs = Math.min(durationMs * 0.45, 1600);
		const startedAt = performance.now();
		while (performance.now() - startedAt < countMs) {
			if (runId !== id) return;
			const t = (performance.now() - startedAt) / countMs;
			displayedMW = target * (1 - (1 - t) * (1 - t));
			await waitForTimeout(33);
		}
		displayedMW = target;

		await waitForTimeout(durationMs - countMs);
		if (runId === id) visible = false;
	};

	$effect(() => {
		const phase = stateGame.phase;
		// untrack so the effect depends only on the phase, not on the
		// celebration state it writes (tier, rain, visible, ...)
		untrack(() => {
			if (phase === 'banked') {
				celebrate();
			} else if (visible) {
				dismiss();
			}
		});
	});
</script>

{#if visible}
	<button class="win-celebration level-{tier.level}" onclick={dismiss} aria-label="dismiss">
		<div class="rain" aria-hidden="true">
			{#each rain as glyph, index (index)}
				<span
					class="rain-glyph"
					style="left: {glyph.left}%; animation-delay: {glyph.delayMs}ms; animation-duration: {glyph.durationMs}ms; font-size: {glyph.fontSize}em;"
				>
					{glyph.char}
				</span>
			{/each}
		</div>
		<div class="win-panel">
			<div class="win-tier">&gt;&gt;&gt; {tier.label} &lt;&lt;&lt;</div>
			<div class="win-headline">SHUTDOWN CLEAN</div>
			<div class="win-amount">+{formatMW(displayedMW)} MW</div>
			<div class="win-sub dim">
				{stateGame.targetTemp.toFixed(2)}x survived
				{#if stateGame.couldHaveReached > stateGame.targetTemp}
					&nbsp;|&nbsp; silicon had {stateGame.couldHaveReached.toFixed(2)}x in it
				{/if}
			</div>
			<div class="win-hint dim">[ click to continue ]</div>
		</div>
	</button>
{/if}
