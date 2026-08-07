<script lang="ts">
	import { untrack } from 'svelte';
	import { stateBet, stateBetDerived, stateUrlDerived } from 'state-shared';
	import { waitForTimeout } from 'utils-shared/wait';

	import { BOOK_AMOUNT_SCALE, LADDERS, RIG_MAP, type WinTier } from '../game/constants';
	import { getContext } from '../game/context';
	import { bookPayoutBase, formatMoney, formatMW, toBaseUnits } from '../game/money';
	import { prefersReducedMotion } from '../game/motion';
	import { labelStake, wordCashOut, wordPayout, wordStake } from '../game/socialCopy';
	import { stateGame, resetRound } from '../game/stateGame.svelte';
	import { stateSession } from '../game/stateSession.svelte';
	import { playMilestoneChirp, playCoinTick, playWinFanfare } from '../game/sound';
	import { rigName, t } from '../game/t';
	import { replayLastBet, requestBoot } from '../game/utils';

	const context = getContext();

	// read-only replay window: replay controls only, no wallet UI (QA phase 3)
	const isReplay = stateUrlDerived.replay();

	// checkpoint lock hits: discrete reward pulses (not random garnish)
	// `amount` is RGS integer base units for formatMoney
	type CoinToast = { id: number; amount: number; offset: number };
	type LockBurst = { id: number; sparks: { sx: number; sy: number }[] };
	let coinToasts = $state([] as CoinToast[]);
	let lockBursts = $state([] as LockBurst[]);
	let toastId = 0;
	let lockPulse = $state(false);
	let lastSecuredBook = 0;

	const spawnLockHit = (deltaBook: number) => {
		const id = (toastId += 1);
		coinToasts.push({
			id,
			amount: bookPayoutBase(deltaBook, stateBet.wageredBetAmount),
			offset: -50 + Math.random() * 100,
		});
		lockPulse = true;
		setTimeout(() => {
			lockPulse = false;
		}, 380);
		if (!prefersReducedMotion()) {
			const burstId = id;
			lockBursts.push({
				id: burstId,
				sparks: Array.from({ length: 6 }, () => ({
					sx: -40 + Math.random() * 80,
					sy: -50 + Math.random() * 20,
				})),
			});
			setTimeout(() => {
				const index = lockBursts.findIndex((burst) => burst.id === burstId);
				if (index >= 0) lockBursts.splice(index, 1);
			}, 450);
		}
		playCoinTick();
		setTimeout(() => {
			const index = coinToasts.findIndex((toast) => toast.id === id);
			if (index >= 0) coinToasts.splice(index, 1);
		}, 900);
	};

	$effect(() => {
		const securedBook = stateGame.securedBook;
		const phase = stateGame.phase;
		untrack(() => {
			if (phase !== 'heating') {
				lastSecuredBook = securedBook;
				return;
			}
			if (securedBook > lastSecuredBook) {
				spawnLockHit(securedBook - lastSecuredBook);
			}
			lastSecuredBook = securedBook;
		});
	});

	// eased display temp so digits never hard-snap between climb segments
	let displayTemp = $state(1);
	let digitFlicker = $state(false);
	let settleClass = $state('' as '' | 'settle-win' | 'settle-melt');
	let tempAnimId = 0;
	$effect(() => {
		const target = stateGame.currentTemp;
		const phase = stateGame.phase;
		untrack(() => {
			if (phase === 'booting') {
				displayTemp = 1;
				settleClass = '';
				return;
			}
			if (phase === 'fried') {
				displayTemp = target;
				settleClass = 'settle-melt';
				return;
			}
			if (phase === 'banked') {
				displayTemp = target;
				settleClass = 'settle-win';
				return;
			}
			if (prefersReducedMotion()) {
				displayTemp = target;
				return;
			}
			const id = ++tempAnimId;
			const from = displayTemp;
			const startedAt = performance.now();
			const durationMs = stateBet.isTurbo ? 90 : 180;
			digitFlicker = true;
			setTimeout(() => {
				if (id === tempAnimId) digitFlicker = false;
			}, 120);
			const step = () => {
				if (id !== tempAnimId) return;
				const t = Math.min((performance.now() - startedAt) / durationMs, 1);
				const eased = 1 - (1 - t) * (1 - t);
				displayTemp = from + (target - from) * eased;
				if (t < 1) requestAnimationFrame(step);
				else displayTemp = target;
			};
			requestAnimationFrame(step);
		});
	});

	// peak temp this round, latched so ladder rungs don't flicker on jitter dips
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
			// checkpoint ticks fire from the book handler; overdrive rungs above
			// the target get the highest chirps here
			if (phase === 'heating') {
				[1.5, 3, 10].forEach((mult, index) => {
					const rung = stateGame.targetTemp * mult;
					if (peakTemp < rung && temp >= rung) {
						playMilestoneChirp(10 + index);
					}
				});
			}
			peakTemp = temp;
		});
	});

	const rig = $derived(RIG_MAP[stateGame.rigTier]);
	const rigLadder = $derived(LADDERS[stateGame.rigTier]);
	const fillFraction = $derived(
		Math.min(
			Math.max((stateGame.currentTemp - 1) / Math.max(stateGame.targetTemp - 1, 0.0001), 0),
			1,
		),
	);
	const gaugeTone = $derived(
		// red is reserved for the meltdown moment itself (brief 7): the climb
		// runs green into amber, and only an actual fry turns anything red
		stateGame.phase === 'fried'
			? 'fault'
			: stateGame.phase === 'banked' || fillFraction < 0.6
				? 'win'
				: 'warn',
	);

	// one shared money path: payouts as RGS base-unit integers from book-unit
	// multipliers × stake (API scale), never cents / float×100 display paths
	const securedBase = $derived(
		bookPayoutBase(stateGame.securedBook, stateBet.wageredBetAmount),
	);
	const winBase = $derived(
		bookPayoutBase(stateBet.winBookEventAmount, stateBet.wageredBetAmount),
	);

	// the next checkpoint the climb is reaching for (null once all are crossed)
	const nextRung = $derived(rigLadder.rungs[stateGame.rungsCrossed] ?? null);

	// near-miss readout on a fry: how close was the next lock-in? this is the
	// hero of the loss screen (brief 5), so the threshold is generous -- any
	// death in the closer half of the gap gets the "so close" line
	const nearMiss = $derived.by(() => {
		if (stateGame.phase !== 'fried' || stateGame.crashTemp <= 1.005) return null;
		const next = rigLadder.rungs.find((rung) => rung.temp > stateGame.crashTemp + 1e-9);
		const nextTemp = next ? next.temp : stateGame.targetTemp;
		const nextValue = next ? next.bank : stateGame.targetTemp;
		const prevTemp =
			stateGame.rungsCrossed > 0 ? rigLadder.rungs[stateGame.rungsCrossed - 1].temp : 1;
		const gap = Math.max(nextTemp - prevTemp, 0.0001);
		const shortBy = nextTemp - stateGame.crashTemp;
		if (shortBy / gap >= 0.5) return null;
		return { shortBy, nextTemp, nextValue };
	});


	// true while the limiter has slipped and the temp is past the bank target
	const inOverdrive = $derived(stateGame.currentTemp > stateGame.targetTemp + 1e-9);

	// simple checkpoint ladder for the right column: just the banking rungs and
	// the target on top, lighting up as the climb crosses them -- no overdrive
	// tiers, no probabilities, no collapsed variants
	type LadderRow = { temp: number; value: string; target: boolean };
	const simpleLadder = $derived.by((): LadderRow[] => [
		{
			temp: stateGame.targetTemp,
			value: t('ladder_full', { mult: stateGame.targetTemp.toFixed(2) }),
			target: true,
		},
		...rigLadder.rungs
			.map((rung) => ({ temp: rung.temp, value: `${rung.bank.toFixed(2)}x`, target: false }))
			.reverse(),
	]);

	const winTier = $derived(stateGame.winTier ?? 'clean');

	// ------------------------------------------------ win celebration (in-place)
	// single win presentation: CLEAN BANK / tier label + payout. no amber
	// LOCKED / BANKED YIELD intermediate before it.

	type Celebration = {
		label: string;
		headline: string;
		level: number;
		golden: boolean;
		glyphCount: number;
	};

	const HEADLINES: Record<WinTier, () => string> = {
		clean: () => t('win_headline_clean'),
		overdrive: () => t('win_headline_overdrive'),
		critical: () => t('win_headline_critical'),
		golden: () => t('win_headline_golden'),
	};

	// keyed off the payout multiple of the stake, not the rig target:
	// a golden shutdown on a small rig still gets the full treatment
	const celebrationFor = (payoutMultiple: number, tier: WinTier): Celebration => {
		const headline = HEADLINES[tier]();
		const golden = tier === 'golden';
		if (golden || payoutMultiple >= 100)
			return {
				label: golden ? t('win_label_golden') : t('win_label_legendary'),
				headline,
				level: 5,
				golden,
				glyphCount: 110,
			};
		if (payoutMultiple >= 25)
			return { label: t('win_label_massive'), headline, level: 4, golden, glyphCount: 80 };
		if (payoutMultiple >= 10)
			return { label: t('win_label_huge'), headline, level: 3, golden, glyphCount: 60 };
		if (payoutMultiple >= 5)
			return { label: t('win_label_big'), headline, level: 2, golden, glyphCount: 45 };
		return { label: t('win_label_clean'), headline, level: 1, golden, glyphCount: 30 };
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
	/** win count-up in RGS base units */
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
				if (id !== celebrationId || stateGame.phase !== 'banked') return;
				const payoutMultiple = stateBet.winBookEventAmount / BOOK_AMOUNT_SCALE;
				const tier = celebrationFor(payoutMultiple, stateGame.winTier ?? 'clean');
				celebration = tier;
				rain = makeRain(stateBet.isTurbo ? 24 : tier.glyphCount);
				displayedWin = 0;
				playWinFanfare(tier.level);

				// count the payout up from zero, easing out into the final figure
				const target = winBase;
				const countMs = stateBet.isTurbo ? 500 : 1400;
				const startedAt = performance.now();
				while (performance.now() - startedAt < countMs) {
					if (id !== celebrationId) return;
					const t = (performance.now() - startedAt) / countMs;
					displayedWin = Math.round(target * (1 - (1 - t) ** 3));
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
	const stakeLabel = $derived(labelStake());
	const stakeWord = $derived(wordStake());
	const cashOut = $derived(wordCashOut());
	const payoutWord = $derived(wordPayout());

	const bootAgain = () => {
		requestBoot(context);
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
		{t('run_topline', {
			rig: rig ? rigName(rig.id) : stateGame.rigTier,
			stakeLabel,
			amount: formatMoney(toBaseUnits(stateBet.wageredBetAmount)),
		})}
	</div>

	<div class="run-grid">
		<div class="run-col run-left sys-log-ambient">
			<!-- ambient boot flavor only (R2 1.3/1.4): banked progress lives in
			     the SECURED YIELD box -->
			<div class="col-title dim">{t('col_sys_log')}</div>
			{#each stateGame.logs as line, index (index)}
				<div class="log-line dim">{line.text}</div>
			{/each}
			<div class="log-line cursor"></div>
		</div>

		<div class="run-center">
			<div class="temp-block">
				<div class="temp-label dim">{t('label_core_temp')}</div>
				<div
					class="temp-giant {gaugeTone} {settleClass}"
					class:overdrive={inOverdrive}
					class:shimmer={stateGame.phase === 'heating' && fillFraction > 0.55 && !prefersReducedMotion()}
					class:flicker-digit={digitFlicker}
					style="--heat: {fillFraction.toFixed(3)}"
				>
					{displayTemp.toFixed(2)}x
				</div>
				{#if inOverdrive && stateGame.phase === 'heating'}
					<div class="temp-sub overdrive-tag">{t('tag_limiter_slipped')}</div>
				{:else}
					<!-- the target line, in plain language, always visible (brief 4) -->
					<div class="temp-sub dim">
						{t('run_cashout_at', { cashOut, mult: stateGame.targetTemp.toFixed(2) })}
					</div>
				{/if}
				<div class="gauge-big {gaugeTone}">
					<div class="gauge-track-row">
						<span class="gauge-bracket" aria-hidden="true">[</span>
						<div class="gauge-track" aria-hidden="true">
							<div
								class="gauge-fill"
								style="width: {(Math.min(fillFraction, 1) * 100).toFixed(1)}%"
							></div>
						</div>
						<span class="gauge-bracket" aria-hidden="true">]</span>
					</div>
					<span class="gauge-target">{stateGame.targetTemp.toFixed(2)}x</span>
				</div>
			</div>

			{#if stateGame.phase === 'heating'}
				<div class="yield-box" style="--yglow: {(0.35 + fillFraction * 0.65).toFixed(3)}">
					<div class="yield-label dim">{t('label_secured_yield')}</div>
					<div class="yield-amount" class:lock-hit={lockPulse}>
						{formatMoney(securedBase)}
					</div>
					<div class="mw-garnish dim">{formatMW(securedBase)}</div>
					{#each lockBursts as burst (burst.id)}
						<div class="lock-burst" aria-hidden="true">
							{#each burst.sparks as spark, index (index)}
								<span style="--sx: {spark.sx}px; --sy: {spark.sy}px"></span>
							{/each}
						</div>
					{/each}
					<div class="yield-caption dim">
						{#if nextRung}
							{t('yield_next_lock', {
								nextMult: nextRung.temp.toFixed(2),
								bankMult: nextRung.bank.toFixed(2),
							})}
						{:else}
							{t('yield_all_locked')}
						{/if}
					</div>
					{#each coinToasts as toast (toast.id)}
						<div class="coin-toast" style="--tx: {toast.offset}px">
							+{formatMoney(toast.amount)}
						</div>
					{/each}
				</div>
			{/if}

			{#if stateGame.phase === 'fried'}
				<!-- loss screen hero: the near miss and the target aimed for,
				     pointed at BOOT AGAIN -- never a funeral (brief 5) -->
				<div class="banner fried">
					{t('result_meltdown', { mult: stateGame.crashTemp.toFixed(2) })}
				</div>
				{#if nearMiss}
					<div class="near-miss-hero warn">
						{t('result_near_miss', {
							delta: nearMiss.shortBy.toFixed(2),
							checkpoint: nearMiss.nextTemp.toFixed(2),
						})}
					</div>
				{/if}
				<div class="aimed-line dim">
					{t('result_aimed_for', { mult: stateGame.targetTemp.toFixed(2) })}
				</div>
				{#if stateGame.securedBook > 0}
					<!-- the checkpoints held: part of the climb survived the fry -->
					<div class="secured-line warn">
						{t('result_checkpoints_held', { amount: formatMoney(securedBase) })}
					</div>
				{/if}
			{/if}

			{#if stateGame.phase === 'banked' && celebration}
				<div class="win-stage level-{celebration.level}" class:golden={celebration.golden}>
					<div class="win-tier">{t('win_banner', { label: celebration.label })}</div>
					<div class="win-amount">+{formatMoney(displayedWin)}</div>
					<div class="mw-garnish dim">{formatMW(displayedWin)}</div>
					{#if winTier !== 'clean'}
						<!-- clean wins: CLEAN BANK is the whole story, no second
						     "clean" line -- special tiers keep their explainer -->
						<div class="win-headline">{celebration.headline}</div>
					{/if}
					{#if winTier !== 'clean'}
						<!-- overdrive/golden taught the moment one lands (brief 2 / 8) -->
						<div class="win-translate dim">
							{t('win_bonus_mult', {
								mult: winTier === 'golden' ? '10' : winTier === 'critical' ? '3' : '1.5',
								payout: payoutWord,
							})}
						</div>
					{/if}
					<!-- neutral crash-point reveal on wins (QA 6.4): honest tease,
					     never "you left money on the table" framing -->
					<div class="win-sub dim">
						{#if stateGame.couldHaveReached > stateGame.currentTemp}
							{t('win_peaked', { mult: stateGame.couldHaveReached.toFixed(2) })}
						{:else}
							{t('win_survived', { mult: stateGame.currentTemp.toFixed(2) })}
						{/if}
					</div>
					{#if stateSession.newBest?.rigTier === stateGame.rigTier}
						<div class="new-best warn">{t('badge_personal_best')}</div>
					{/if}
				</div>
			{/if}

			{#if isSettled}
				<div class="settled-actions">
					{#if isReplay}
						<!-- read-only replay window (QA phase 3): replay the same
						     round, no wallet UI, no live betting entry -->
						<div class="settled-buttons">
							<button class="term-btn rebet-btn" onclick={() => replayLastBet()}>
								{t('btn_replay_again')}
							</button>
						</div>
					{:else}
						{#if stateGame.phase === 'fried' && stateSession.newBest?.rigTier === stateGame.rigTier}
							<div class="new-best">{t('badge_personal_best_run')}</div>
						{/if}
						<div class="settled-buttons">
							<button class="term-btn rebet-btn" onclick={bootAgain} disabled={!canRebet}>
								{t('btn_boot_again')}
							</button>
							<button class="term-btn settled-secondary" onclick={() => resetRound()}>
								<span class="settled-return-full">{t('btn_return_rig_select')}</span>
								<span class="settled-return-mini">{t('btn_return_rig_select_mini')}</span>
							</button>
						</div>
						{#if !canRebet}
							<div class="settled-note warn">
								{t('warn_insufficient_pwr', { stake: stakeWord })}
							</div>
						{/if}
					{/if}
					{#if stateSession.lastRoundID != null}
						<div class="round-id-line dim">
							{t('label_round_id', { id: stateSession.lastRoundID })}
						</div>
					{/if}
				</div>
			{:else if stateGame.phase === 'banked' || stateGame.phase === 'fried'}
				<div class="log-line dim settling">{t('status_settling')}</div>
			{/if}
		</div>

		<div class="run-col run-right">
			{#if stateGame.phase === 'booting' || stateGame.phase === 'heating'}
				<!-- live climb companion only: once the round settles the center
				     summary is the single readout, never the full paytable -->
				<div class="col-title dim">{t('col_checkpoints')}</div>
				<div class="ladder">
					{#each simpleLadder as row (row.temp)}
						<div class="rung" class:lit={peakTemp >= row.temp - 0.0001} class:target={row.target}>
							<span class="rung-mark">{peakTemp >= row.temp - 0.0001 ? '\u2588' : '\u2591'}</span>
							<span class="rung-temp">{row.temp.toFixed(2)}x</span>
							<span class="rung-value">{row.value}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>
