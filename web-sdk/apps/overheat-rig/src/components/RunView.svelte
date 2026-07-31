<script lang="ts">
	import { stateBet, stateBetDerived } from 'state-shared';

	import { BOOK_AMOUNT_SCALE, RIG_MAP } from '../game/constants';
	import { getContext } from '../game/context';
	import { stateGame, resetRound } from '../game/stateGame.svelte';

	const context = getContext();

	const GAUGE_CELLS = 26;
	const HEX = '0123456789abcdef';

	let hashLines = $state([] as string[]);

	const randomHash = () => {
		let hash = '';
		for (let i = 0; i < 48; i += 1) hash += HEX[Math.floor(Math.random() * 16)];
		return hash;
	};

	$effect(() => {
		if (stateGame.phase !== 'heating') return;
		const interval = setInterval(() => {
			hashLines.push(
				`sha256: ${randomHash()} .. ${Math.random() < 0.12 ? 'ACCEPTED' : 'rejected'}`,
			);
			if (hashLines.length > 3) hashLines.splice(0, hashLines.length - 3);
		}, 380);
		return () => clearInterval(interval);
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

<div class="log-line dim">
	RIG: <span class="win">{rig?.name ?? stateGame.rigTier}</span>
	| HASHRATE: {stateGame.hashrate} MH/s
	| STAKE: {formatMW(stateBet.wageredBetAmount)} MW
</div>

{#each stateGame.logs as line, index (index)}
	<div class="log-line {line.tone === 'normal' ? '' : line.tone}">{line.text}</div>
{/each}

{#if stateGame.phase === 'heating'}
	{#each hashLines as hashLine, index (index)}
		<div class="hash-line">{hashLine}</div>
	{/each}
{/if}

{#if stateGame.phase === 'heating' || stateGame.phase === 'banked' || stateGame.phase === 'fried'}
	<div class="gauge-row">
		<span class="dim">CORE TEMP </span><span class={gaugeTone}>[{gaugeBar}]</span>
		<span class={gaugeTone}> {stateGame.currentTemp.toFixed(2)}x</span>
		<span class="dim"> / shutdown @ {stateGame.targetTemp.toFixed(2)}x</span>
	</div>
	{#if stateGame.phase === 'heating'}
		<div class="log-line dim">
			est. yield: {formatMW(minedEstimate)} MW <span class="dim">(banks only at shutdown)</span>
		</div>
	{/if}
{/if}

{#if stateGame.phase === 'fried'}
	<div>
		<div class="banner fried">** MELTDOWN @ {stateGame.crashTemp.toFixed(2)}x -- STAKE LOST **</div>
	</div>
{/if}

{#if stateGame.phase === 'banked'}
	<div>
		<div class="banner banked">** SHUTDOWN CLEAN -- PAYOUT {formatMW(winMW)} MW **</div>
	</div>
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
	<div class="log-line dim">settling round...</div>
{/if}

<div class="log-line cursor"></div>
