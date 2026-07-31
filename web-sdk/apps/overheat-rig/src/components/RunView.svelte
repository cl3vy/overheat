<script lang="ts">
	import { untrack } from 'svelte';
	import { stateBet, stateBetDerived } from 'state-shared';

	import { BOOK_AMOUNT_SCALE, RIG_MAP } from '../game/constants';
	import { getContext } from '../game/context';
	import { stateGame, resetRound } from '../game/stateGame.svelte';
	import { WIN_MILESTONES } from '../game/pacing';
	import { playMilestoneChirp, playCoinTick } from '../game/sound';

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
		fillFraction < 0.6 ? 'win' : fillFraction < 0.85 ? 'warn' : 'fault',
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

	// milestone ladder: round multipliers below target, capped by the target rung
	const ladder = $derived(
		[
			...WIN_MILESTONES.filter((m) => m < stateGame.targetTemp * 0.995),
			stateGame.targetTemp,
		].reverse(),
	);

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
				<div class="temp-giant {gaugeTone}">{stateGame.currentTemp.toFixed(2)}x</div>
				<div class="temp-sub dim">shutdown @ {stateGame.targetTemp.toFixed(2)}x</div>
				<div class="gauge-big {gaugeTone}">[{gaugeBar}]</div>
			</div>

			{#if stateGame.phase === 'heating' || stateGame.phase === 'banked'}
				<div
					class="yield-box"
					class:locked={stateGame.phase === 'banked'}
					style="--yglow: {(0.35 + fillFraction * 0.65).toFixed(3)}"
				>
					<div class="yield-label dim">
						{stateGame.phase === 'banked' ? 'BANKED YIELD' : 'UNBANKED YIELD'}
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
			{/if}

			{#if stateGame.phase === 'banked'}
				<div class="banner banked">** SHUTDOWN CLEAN -- PAYOUT {formatMW(winMW)} MW **</div>
				{#if stateGame.couldHaveReached > stateGame.targetTemp}
					<div class="log-line warn">
						&gt; the silicon had {stateGame.couldHaveReached.toFixed(2)}x in it. just saying.
					</div>
				{/if}
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
				{#each ladder as rung (rung)}
					<div
						class="rung"
						class:lit={peakTemp >= rung - 0.0001}
						class:target={rung === stateGame.targetTemp}
					>
						<span class="rung-mark">{peakTemp >= rung - 0.0001 ? '\u2588' : '\u2591'}</span>
						{rung === stateGame.targetTemp ? 'BANK ' : ''}{rung.toFixed(
							rung === stateGame.targetTemp ? 2 : 1,
						)}x
					</div>
				{/each}
			</div>
		</div>
	</div>
</div>
