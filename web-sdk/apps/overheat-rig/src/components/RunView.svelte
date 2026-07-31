<script lang="ts">
	import { untrack } from 'svelte';
	import { stateBet, stateBetDerived } from 'state-shared';
	import { waitForTimeout } from 'utils-shared/wait';

	import { BOOK_AMOUNT_SCALE, RIG_MAP, type WinTier } from '../game/constants';
	import { getContext } from '../game/context';
	import { stateGame, resetRound } from '../game/stateGame.svelte';
	import { WIN_MILESTONES } from '../game/pacing';
	import { playMilestoneChirp, playCoinTick, playWinFanfare } from '../game/sound';

	const context = getContext();

	const GAUGE_CELLS = 34;
	const HEX = '0123456789abcdef';

	let hashLines = $state([] as string[]);

	const randomHash = () => {
		let hash = '';
		for (let i = 0; i < 40; i += 1) hash += HEX[Math.floor(Math.random() * 16)];
		return hash;
	};

	// coin toasts: accepted hashes pop a small +MW that gets absorbed by the counter
	type CoinToast = { id: number; amount: number; offset: number };
	let coinToasts = $state([] as CoinToast[]);
	let toastId = 0;

	const spawnCoinToast = () => {
		const id = (toastId += 1);
		coinToasts.push({
			id,
			amount: stateBet.wageredBetAmount * (0.08 + Math.random() * 0.45),
			offset: -60 + Math.random() * 120,
		});
		playCoinTick();
		setTimeout(() => {
			const index = coinToasts.findIndex((toast) => toast.id === id);
			if (index >= 0) coinToasts.splice(index, 1);
		}, 1000);
	};

	$effect(() => {
		if (stateGame.phase !== 'heating') return;
		const interval = setInterval(() => {
			const accepted = Math.random() < 0.16;
			hashLines.push(`sha256: ${randomHash()} .. ${accepted ? 'ACCEPTED' : 'rejected'}`);
			if (hashLines.length > 7) hashLines.splice(0, hashLines.length - 7);
			if (accepted) spawnCoinToast();
		}, 380);
		return () => {
			clearInterval(interval);
			coinToasts.length = 0;
		};
	});

	// telemetry wobble tick (display only)
	let wobble = $state(0.5);
	$effect(() => {
		if (stateGame.phase !== 'heating') return;
		const interval = setInterval(() => {
			wobble = Math.random();
		}, 160);
		return () => clearInterval(interval);
	});

	// bank moment: measure the vector from the yield box to the header balance
	// so the winnings visibly fly into the PWR RESERVE
	let flyDelta = $state(null as null | { dx: number; dy: number });
	$effect(() => {
		const phase = stateGame.phase;
		untrack(() => {
			if (phase !== 'banked') {
				flyDelta = null;
				return;
			}
			requestAnimationFrame(() => {
				const fromEl = document.querySelector('.yield-box');
				const toEl = document.querySelector('.pwr-reserve');
				if (!fromEl || !toEl) return;
				const from = fromEl.getBoundingClientRect();
				const to = toEl.getBoundingClientRect();
				flyDelta = {
					dx: to.left + to.width / 2 - (from.left + from.width / 2),
					dy: to.top + to.height / 2 - (from.top + from.height / 2),
				};
			});
		});
	});

	// peak temp this round, latched so milestone rungs don't flicker on jitter dips
	let peakTemp = $state(1);
	$effect(() => {
		const temp = stateGame.currentTemp;
		const phase = stateGame.phase;
		untrack(() => {
			if (phase === 'booting') {
				peakTemp = 1;
				return;
			}
			if (temp <= peakTemp) return;
			// chirp for each milestone rung crossed by this tick (animated only)
			if (phase === 'heating') {
				WIN_MILESTONES.forEach((rung, index) => {
					if (peakTemp < rung && temp >= rung && rung < stateGame.targetTemp) {
						playMilestoneChirp(index);
					}
				});
				// overdrive rungs above the target get the highest chirps
				[1.5, 3, 10].forEach((mult, index) => {
					const rung = stateGame.targetTemp * mult;
					if (peakTemp < rung && temp >= rung) {
						playMilestoneChirp(WIN_MILESTONES.length + index);
					}
				});
			}
			peakTemp = temp;
		});
	});

	const rig = $derived(RIG_MAP[stateGame.rigTier]);
	const fillFraction = $derived(
		Math.min(
			Math.max((stateGame.currentTemp - 1) / Math.max(stateGame.targetTemp - 1, 0.0001), 0),
			1,
		),
	);
	const filledCells = $derived(Math.round(fillFraction * GAUGE_CELLS));
	const gaugeTone = $derived(
		// banked reads as safe again -- the red danger tone is for the climb
		stateGame.phase === 'banked'
			? 'win'
			: fillFraction < 0.6
				? 'win'
				: fillFraction < 0.85
					? 'warn'
					: 'fault',
	);
	const gaugeBar = $derived(
		'\u2588'.repeat(filledCells) + '\u2591'.repeat(GAUGE_CELLS - filledCells),
	);

	const formatMW = (value: number) =>
		value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

	// display-only estimate: coins accumulate as the temperature climbs
	const minedEstimate = $derived(stateBet.wageredBetAmount * stateGame.currentTemp);
	const winMW = $derived(
		(stateBet.winBookEventAmount / BOOK_AMOUNT_SCALE) * stateBet.wageredBetAmount,
	);

	// reactive rig telemetry (display only)
	const fanRpm = $derived(Math.round(2400 + fillFraction * 11200 + wobble * 340));
	const voltRail = $derived((11.86 + fillFraction * 0.92 + wobble * 0.09).toFixed(2));
	const coreClock = $derived(Math.round(1780 + fillFraction * 2650 + wobble * 70));

	// true while the limiter has slipped and the temp is past the bank target
	const inOverdrive = $derived(stateGame.currentTemp > stateGame.targetTemp + 1e-9);

	type Rung = { temp: number; kind: 'milestone' | 'bank' | 'od' | 'gold'; label: string };
	// milestone ladder: multipliers below target, the BANK rung, then the
	// overdrive zone above it (1.5x / 3x / 10x GOLDEN the target)
	const ladder = $derived.by((): Rung[] => {
		const target = stateGame.targetTemp;
		const rungs: Rung[] = [
			...WIN_MILESTONES.filter((m) => m < target * 0.995).map((m) => ({
				temp: m,
				kind: 'milestone' as const,
				label: `${m.toFixed(1)}x`,
			})),
			{ temp: target, kind: 'bank', label: `BANK ${target.toFixed(2)}x` },
			{ temp: target * 1.5, kind: 'od', label: `OD ${(target * 1.5).toFixed(2)}x` },
			{ temp: target * 3, kind: 'od', label: `OD ${(target * 3).toFixed(2)}x` },
			{ temp: target * 10, kind: 'gold', label: `GOLD ${(target * 10).toFixed(2)}x` },
		];
		return rungs.reverse();
	});

	const TIER_YIELD_LABELS = {
		clean: 'BANKED YIELD',
		overdrive: 'OVERDRIVE YIELD',
		critical: 'CRITICAL YIELD',
		golden: 'GOLDEN YIELD',
	} as const;
	const winTier = $derived(stateGame.winTier ?? 'clean');

	const salvageMW = $derived(stateGame.salvageMult * stateBet.wageredBetAmount);

	// ------------------------------------------------ win celebration (in-place)
	// the whole run screen becomes the congratulations: glyph rain behind the
	// dashboard, screen flash, and a huge payout count-up in the center stage --
	// no blocking popup, the BOOT AGAIN button stays reachable throughout

	type Celebration = {
		label: string;
		headline: string;
		level: number;
		golden: boolean;
		glyphCount: number;
	};

	const HEADLINES: Record<WinTier, string> = {
		clean: 'SHUTDOWN CLEAN',
		overdrive: 'THERMAL LIMITER SLIPPED -- 1.5x TARGET',
		critical: 'BREAKER SLAMMED -- 3x TARGET',
		golden: 'THE SILICON ASCENDED -- 10x TARGET',
	};

	// keyed off the payout multiple of the stake, not the rig target:
	// a golden shutdown on a small rig still gets the full treatment
	const celebrationFor = (payoutMultiple: number, tier: WinTier): Celebration => {
		const headline = HEADLINES[tier];
		const golden = tier === 'golden';
		if (golden || payoutMultiple >= 100)
			return {
				label: golden ? 'GOLDEN SHUTDOWN' : 'LEGENDARY RUN',
				headline,
				level: 5,
				golden,
				glyphCount: 110,
			};
		if (payoutMultiple >= 25)
			return { label: 'MASSIVE BANK', headline, level: 4, golden, glyphCount: 80 };
		if (payoutMultiple >= 10)
			return { label: 'HUGE BANK', headline, level: 3, golden, glyphCount: 60 };
		if (payoutMultiple >= 5)
			return { label: 'BIG BANK', headline, level: 2, golden, glyphCount: 45 };
		return { label: 'CLEAN BANK', headline, level: 1, golden, glyphCount: 30 };
	};

	const GLYPHS = '$¤01▓ΞÐ+';
	type RainGlyph = {
		char: string;
		left: number;
		delayMs: number;
		durationMs: number;
		fontSize: number;
	};

	const makeRain = (count: number): RainGlyph[] =>
		Array.from({ length: count }, () => ({
			char: GLYPHS[Math.floor(Math.random() * GLYPHS.length)],
			left: Math.random() * 100,
			delayMs: Math.random() * 1800,
			durationMs: 1600 + Math.random() * 1800,
			fontSize: 0.8 + Math.random() * 1.4,
		}));

	let celebration = $state<Celebration | null>(null);
	let rain = $state<RainGlyph[]>([]);
	let displayedWin = $state(0);
	let celebrationId = 0;

	$effect(() => {
		const phase = stateGame.phase;
		// untrack: the effect keys off the phase only, not the celebration
		// state it writes
		untrack(() => {
			const id = ++celebrationId;
			if (phase !== 'banked') {
				celebration = null;
				rain = [];
				return;
			}
			(async () => {
				// let the bank moment land first: LOCKED stamp, fly-to-balance,
				// header count-up -- then the congratulations takes the stage
				await waitForTimeout(stateBet.isTurbo ? 200 : 1100);
				if (id !== celebrationId || stateGame.phase !== 'banked') return;
				const payoutMultiple = stateBet.winBookEventAmount / BOOK_AMOUNT_SCALE;
				const tier = celebrationFor(payoutMultiple, stateGame.winTier ?? 'clean');
				celebration = tier;
				rain = makeRain(stateBet.isTurbo ? 24 : tier.glyphCount);
				displayedWin = 0;
				playWinFanfare(tier.level);

				// count the payout up from zero, easing out into the final figure
				const target = winMW;
				const countMs = stateBet.isTurbo ? 500 : 1400;
				const startedAt = performance.now();
				while (performance.now() - startedAt < countMs) {
					if (id !== celebrationId) return;
					const t = (performance.now() - startedAt) / countMs;
					displayedWin = target * (1 - (1 - t) ** 3);
					await waitForTimeout(33);
				}
				displayedWin = target;
			})();
		});
	});

	const isSettled = $derived(
		(stateGame.phase === 'banked' || stateGame.phase === 'fried') &&
			context.stateXstateDerived.isIdle(),
	);

	const canRebet = $derived(stateBetDerived.isBetCostAvailable());

	const bootAgain = () => {
		if (!canRebet) return;
		context.eventEmitter.broadcast({ type: 'bet' });
	};
</script>

<div class="run-dash">
	{#if celebration}
		<div class="win-flash-layer" aria-hidden="true"></div>
		<div class="run-rain" class:golden={celebration.golden} aria-hidden="true">
			{#each rain as glyph, index (index)}
				<span
					class="rain-glyph"
					style="left: {glyph.left}%; animation-delay: {glyph.delayMs}ms; animation-duration: {glyph.durationMs}ms; font-size: {glyph.fontSize}em;"
				>
					{glyph.char}
				</span>
			{/each}
		</div>
	{/if}

	<div class="run-topline dim">
		RIG: <span class="win">{rig?.name ?? stateGame.rigTier}</span>
		| HASHRATE: {stateGame.hashrate} MH/s
		| STAKE: {formatMW(stateBet.wageredBetAmount)} MW
	</div>

	<div class="run-grid">
		<div class="run-col run-left">
			<div class="col-title dim">// SYS LOG</div>
			{#each stateGame.logs as line, index (index)}
				<div class="log-line {line.tone === 'normal' ? '' : line.tone}">{line.text}</div>
			{/each}
			{#if stateGame.phase === 'heating'}
				{#each hashLines as hashLine, index (index)}
					<div class="hash-line">{hashLine}</div>
				{/each}
			{/if}
			<div class="log-line cursor"></div>
		</div>

		<div class="run-center">
			<div class="temp-block">
				<div class="temp-label dim">CORE TEMP</div>
				<div class="temp-giant {gaugeTone}" class:overdrive={inOverdrive}>
					{stateGame.currentTemp.toFixed(2)}x
				</div>
				{#if inOverdrive && stateGame.phase === 'heating'}
					<div class="temp-sub overdrive-tag">!! LIMITER SLIPPED -- OVERDRIVE !!</div>
				{:else}
					<div class="temp-sub dim">shutdown @ {stateGame.targetTemp.toFixed(2)}x</div>
				{/if}
				<div class="gauge-big {gaugeTone}">[{gaugeBar}]</div>
			</div>

			{#if stateGame.phase === 'heating' || (stateGame.phase === 'banked' && !celebration)}
				<div
					class="yield-box"
					class:locked={stateGame.phase === 'banked'}
					class:golden={stateGame.phase === 'banked' && winTier === 'golden'}
					style="--yglow: {(0.35 + fillFraction * 0.65).toFixed(3)}"
				>
					<div class="yield-label dim">
						{stateGame.phase === 'banked' ? TIER_YIELD_LABELS[winTier] : 'UNBANKED YIELD'}
					</div>
					<div class="yield-amount">
						{formatMW(stateGame.phase === 'banked' ? winMW : minedEstimate)} MW
					</div>
					{#if stateGame.phase === 'banked'}
						<div class="locked-stamp">LOCKED</div>
						{#if flyDelta}
							<div class="fly-amount" style="--fdx: {flyDelta.dx}px; --fdy: {flyDelta.dy}px">
								+{formatMW(winMW)} MW
							</div>
						{/if}
					{:else}
						<div class="yield-caption dim">banks only at shutdown</div>
						{#each coinToasts as toast (toast.id)}
							<div class="coin-toast" style="--tx: {toast.offset}px">
								+{formatMW(toast.amount)} MW
							</div>
						{/each}
					{/if}
				</div>
			{/if}

			{#if stateGame.phase === 'fried'}
				<div class="banner fried">
					** MELTDOWN @ {stateGame.crashTemp.toFixed(2)}x -- STAKE LOST **
				</div>
				{#if stateGame.salvageMult > 0}
					<!-- consolation, not a win: salvage pays back less than the stake -->
					<div class="salvage-line warn">
						&gt;&gt; SCRAP SALVAGE: +{formatMW(salvageMW)} MW pulled from the slag
						({stateGame.salvageMult.toFixed(2)}x stake)
					</div>
				{/if}
			{/if}

			{#if stateGame.phase === 'banked' && celebration}
				<div class="win-stage level-{celebration.level}" class:golden={celebration.golden}>
					<div class="win-tier">&gt;&gt;&gt; {celebration.label} &lt;&lt;&lt;</div>
					<div class="win-amount">+{formatMW(displayedWin)} MW</div>
					<div class="win-headline">{celebration.headline}</div>
					<div class="win-sub dim">
						{stateGame.currentTemp.toFixed(2)}x survived
						{#if stateGame.couldHaveReached > stateGame.currentTemp}
							&nbsp;|&nbsp; silicon had {stateGame.couldHaveReached.toFixed(2)}x in it
						{/if}
					</div>
				</div>
			{/if}

			{#if isSettled}
				<div class="settled-actions">
					<button class="term-btn rebet-btn" onclick={bootAgain} disabled={!canRebet}>
						&gt;&gt; BOOT AGAIN &lt;&lt; <span class="key-hint">[SPACE]</span>
					</button>
					<button class="term-btn" onclick={() => resetRound()}>RETURN TO RIG SELECT</button>
					{#if !canRebet}
						<span class="fault">insufficient power reserve</span>
					{/if}
				</div>
			{:else if stateGame.phase === 'banked' || stateGame.phase === 'fried'}
				<div class="log-line dim settling">settling round...</div>
			{/if}
		</div>

		<div class="run-col run-right">
			<div class="col-title dim">// TELEMETRY</div>
			<div class="tele-row">
				<span class="dim">FAN</span>
				<span class={fillFraction > 0.85 ? 'fault' : fillFraction > 0.6 ? 'warn' : ''}>
					{fanRpm.toLocaleString('en-US')} RPM
				</span>
			</div>
			<div class="tele-row">
				<span class="dim">12V RAIL</span>
				<span>{voltRail} V</span>
			</div>
			<div class="tele-row">
				<span class="dim">CORE CLK</span>
				<span>{coreClock} MHz</span>
			</div>

			<div class="col-title dim ladder-title">// MILESTONES</div>
			<div class="ladder">
				{#each ladder as rung (rung.label)}
					<div
						class="rung"
						class:lit={peakTemp >= rung.temp - 0.0001}
						class:target={rung.kind === 'bank'}
						class:od={rung.kind === 'od'}
						class:gold={rung.kind === 'gold'}
					>
						<span class="rung-mark">{peakTemp >= rung.temp - 0.0001 ? '\u2588' : '\u2591'}</span>
						{rung.label}
					</div>
				{/each}
			</div>
		</div>
	</div>
</div>
