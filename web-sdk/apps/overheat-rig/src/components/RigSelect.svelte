<script lang="ts">
	import { onMount } from 'svelte';

	import { stateBet, stateBetDerived, stateConfig } from 'state-shared';

	import { LADDERS, MAX_WIN_MULT, RIGS } from '../game/constants';
	import { getContext } from '../game/context';
	import { stateSession, sessionStats } from '../game/stateSession.svelte';
	import { requestBoot } from '../game/utils';
	import FairnessPanel from './FairnessPanel.svelte';
	import TurboToggle from './TurboToggle.svelte';

	type Props = { scanlines: boolean; flicker: boolean };

	let { scanlines = $bindable(), flicker = $bindable() }: Props = $props();

	const context = getContext();

	let settingsOpen = $state(false);
	let fairnessOpen = $state(false);

	const betOptions = $derived(stateConfig.betAmountOptions ?? []);

	const formatMW = (value: number) =>
		value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

	let stakeText = $state('');

	// reflect external stake changes (steppers, seeding, balance clamps) in the field
	$effect(() => {
		stakeText = stateBet.betAmount.toFixed(2);
	});

	/** Parse the typed stake, clamp to RGS limits, snap to the bet step grid. */
	const commitStake = () => {
		const raw = Number(stakeText.replace(/,/g, ''));
		if (!Number.isFinite(raw) || raw <= 0) {
			stakeText = stateBet.betAmount.toFixed(2);
			return;
		}
		const step = stateConfig.stepBet > 0 ? stateConfig.stepBet : 0.1;
		const clamped = Math.min(Math.max(raw, stateConfig.minBet), stateConfig.maxBet);
		const snapped = Number((Math.round(clamped / step) * step).toFixed(6));
		stateBetDerived.setBetAmount(snapped);
		stakeText = stateBet.betAmount.toFixed(2);
	};

	const rigIndex = $derived(
		Math.max(
			0,
			RIGS.findIndex((rig) => rig.id === stateBet.activeBetModeKey),
		),
	);
	const rig = $derived(RIGS[rigIndex]);
	const rigLadder = $derived(LADDERS[rig.id]);

	// progressive disclosure: the boot screen for a first-ever run carries
	// only the loop sentence, the target + translation, stake and boot.
	// checkpoint copy appears once there is a run to hang it on.
	const hasPlayed = $derived(stateSession.meta.lifetimeRounds > 0);

	// meltdown clause gated on whether the active mode banks checkpoints
	// (all current rigs do; the gate keeps the copy honest if one ever doesn't)
	const meltdownClause = $derived(
		(LADDERS[rig.id]?.rungs.length ?? 0) > 0
			? 'if it melts down first, you keep only what the checkpoints banked.'
			: 'if it melts down first, you lose the stake.',
	);

	// hit frequency stays as a standalone mode descriptor -- never rendered
	// on the same line as any payout, odds-for-payout, or profit figure
	const anyPayout = $derived(rigLadder.anyPayoutProb * 100);
	const winPays = $derived(stateBet.betAmount * rig.targetTemp);
	const maxPays = $derived(stateBet.betAmount * rig.targetTemp * MAX_WIN_MULT);
	// mode personality in two words (R2 3.2)
	const profileLabel = $derived(
		rigLadder.profile === 'drip'
			? 'frequent, small'
			: rigLadder.profile === 'balanced'
				? 'steady'
				: 'rare, big',
	);

	// mini ladder preview: rung positions on a log scale up to the target
	// (shape only -- no values, no probabilities)
	const previewTicks = $derived.by(() => {
		const logTarget = Math.log(rig.targetTemp);
		return rigLadder.rungs.map((rung) => ({
			pos: (Math.log(rung.temp) / logTarget) * 100,
			aboveStake: rung.bank >= 1,
		}));
	});

	// 0..1 along the ladder, drives the heat colors
	const heat = $derived(rigIndex / (RIGS.length - 1));
	const heatClass = $derived(heat < 0.35 ? 'heat-low' : heat < 0.7 ? 'heat-mid' : 'heat-high');

	// ---------------------------------------------------------- stats strip
	// peaks first and loudest; no net P/L, no attempt tallies, no loss rates

	const rigBest = $derived(sessionStats.bestFor(rig.id));
	const hottest = $derived(sessionStats.hottestRun());
	const bestBank = $derived(sessionStats.bestBankMW());
	const hasPeaks = $derived(hottest > 0 || bestBank > 0 || rigBest.bestMult > 0);

	// recent chips, reweighted: the eye should land on the wins
	const chipClass = (round: (typeof stateSession.rounds)[number]) => {
		if (round.tier === 'golden') return 'chip-golden chip-big';
		if (round.payoutMult >= 1) return 'chip-win chip-big';
		if (round.payoutMult > 0) return 'chip-part chip-mid';
		return 'chip-bust chip-low';
	};

	const setRigIndex = (index: number) => {
		const clamped = Math.min(Math.max(index, 0), RIGS.length - 1);
		stateBet.activeBetModeKey = RIGS[clamped].id;
	};

	// steppers jump to the nearest configured bet level above/below the
	// current amount, so they still work from a hand-typed stake
	const stepBet = (direction: 1 | -1) => {
		if (!betOptions.length) return;
		const amount = stateBet.betAmount;
		const next =
			direction === 1
				? betOptions.find((option) => option > amount + 1e-9)
				: [...betOptions].reverse().find((option) => option < amount - 1e-9);
		if (next !== undefined) stateBetDerived.setBetAmount(next);
	};

	const atMinLevel = $derived(!betOptions.length || stateBet.betAmount <= betOptions[0] + 1e-9);
	const atMaxLevel = $derived(
		!betOptions.length || stateBet.betAmount >= betOptions[betOptions.length - 1] - 1e-9,
	);

	const canBoot = $derived(
		context.stateXstateDerived.isIdle() &&
			stateBetDerived.isBetCostAvailable() &&
			RIGS.some((r) => r.id === stateBet.activeBetModeKey),
	);

	const boot = () => {
		requestBoot(context);
	};

	onMount(() => {
		// seed the stake from betLevels if the current amount is not a valid level
		if (betOptions.length && !betOptions.includes(stateBet.betAmount)) {
			const closest = betOptions.reduce((best, option) =>
				Math.abs(option - stateBet.betAmount) < Math.abs(best - stateBet.betAmount)
					? option
					: best,
			);
			stateBetDerived.setBetAmount(closest);
		}
		// default rig if the mode key is not one of ours (e.g. initial 'BASE')
		if (!RIGS.some((r) => r.id === stateBet.activeBetModeKey)) {
			stateBet.activeBetModeKey = 'standard';
		}
	});
</script>

<div class="select-screen">
<div class="select-col">
{#if !hasPlayed}
	<!-- the loop, in one plain sentence -- honest: there is no mid-round
	     action, the rig stops at the preset target on its own (R2 P0) -->
	<div class="loop-callout">
		<div class="loop-title dim">// HOW IT WORKS</div>
		<div class="loop-text">
			set your auto cash out target. boot the rig. it climbs on its own and
			stops there automatically. {meltdownClause}
		</div>
	</div>
{:else}
	<div class="log-line dim">
		&gt; set your auto cash out target -- the rig climbs on its own and stops there
		automatically. {meltdownClause}
	</div>
{/if}

{#if hasPeaks}
	<!-- personal peaks lead the strip: biggest, brightest, first -->
	<div class="peak-strip">
		{#if hottest > 0}
			<span class="peak">HOTTEST <span class="peak-value">{hottest.toFixed(2)}x</span></span>
		{/if}
		{#if bestBank > 0}
			<span class="peak amber">BEST BANK <span class="peak-value">{bestBank.toFixed(2)} MW</span></span>
		{/if}
		{#if rigBest.bestMult > 0}
			<span class="peak">{rig.name} BEST <span class="peak-value">{rigBest.bestMult.toFixed(2)}x</span></span>
		{/if}
	</div>
{/if}

{#if stateSession.rounds.length > 0}
	<div class="history-strip">
		<span class="dim">RECENT:</span>
		{#each stateSession.rounds.slice(-14) as round, index (index)}
			<span class="history-chip {chipClass(round)}">
				{round.crashTemp.toFixed(2)}x
			</span>
		{/each}
	</div>
{/if}

{#if stateSession.heatStreak >= 1 || stateSession.meta.bestStreak >= 2}
	<!-- the live streak is the sticky element; the rank ladder is gone (R2 P2) -->
	<div class="record-strip dim">
		STREAK <span class="warn">{stateSession.heatStreak}</span>
		(BEST <span class="warn">{stateSession.meta.bestStreak}</span>)
	</div>
{/if}

<div class="dial-panel {heatClass}">
	<div class="dial-header">
		<!-- plain meaning is the primary label; the themed name is flavor (R2 3.1) -->
		<span class="dial-title">CASH OUT TARGET</span>
		<span class="dial-rig-name">[ {rig.name} ]</span>
	</div>
	<div class="dial-subtitle dim">shutdown temp</div>

	<div class="dial-readout">
		<span class="dial-mult">{rig.targetTemp.toFixed(2)}x</span>
		<!-- inline translation: themed label above, plain meaning here (brief 3) -->
		<span class="dial-translate">cash out at {rig.targetTemp.toFixed(2)}x</span>
		<span class="dial-flavor dim">{rig.flavor}</span>
	</div>

	<div class="dial-slider-row">
		<button class="term-btn" onclick={() => setRigIndex(rigIndex - 1)} disabled={rigIndex <= 0}>
			-
		</button>
		<div class="dial-slider-track">
			<input
				class="dial-slider"
				type="range"
				min="0"
				max={RIGS.length - 1}
				step="1"
				value={rigIndex}
				oninput={(event) => setRigIndex(Number(event.currentTarget.value))}
				aria-label="shutdown temperature"
			/>
			<div class="dial-heatbar" aria-hidden="true">
				<div class="dial-heatbar-fill" style="width: {heat * 100}%"></div>
			</div>
			<div class="dial-scale dim" aria-hidden="true">
				<span>1.20x</span>
				<span>safe</span>
				<span>spicy</span>
				<span>100.00x</span>
			</div>
		</div>
		<button
			class="term-btn"
			onclick={() => setRigIndex(rigIndex + 1)}
			disabled={rigIndex >= RIGS.length - 1}
		>
			+
		</button>
	</div>

	{#if hasPlayed}
		<!-- checkpoint ladder preview: shape of the climb, no numbers.
		     hidden on a first-ever run -- checkpoints are taught by watching
		     the reveal, not by boot copy (brief 4 / 8) -->
		<div class="ladder-preview">
			<div class="ladder-preview-track" aria-hidden="true">
				{#each previewTicks as tick, index (index)}
					<span
						class="ladder-tick {tick.aboveStake ? 'tick-profit' : 'tick-scrap'}"
						style="left: {tick.pos}%"
					></span>
				{/each}
				<span class="ladder-tick tick-target" style="left: 100%"></span>
			</div>
			<div class="ladder-preview-caption dim">
				each tick banks a partial payout as the rig climbs
				&nbsp;|&nbsp; this mode: <span class="profile-tag">{profileLabel}</span>
			</div>
		</div>
	{/if}

	<!-- standalone mode descriptor: never shares a line with any other figure -->
	<div class="dial-facts">
		<span>
			pays something: <span class="dial-odds">{anyPayout.toFixed(1)}%</span> of runs
		</span>
	</div>

	<div class="dial-facts">
		<span>
			stake:
			<button class="term-btn" onclick={() => stepBet(-1)} disabled={atMinLevel}>-</button>
			<input
				class="stake-input"
				type="text"
				inputmode="decimal"
				bind:value={stakeText}
				onblur={commitStake}
				onkeydown={(event) => event.key === 'Enter' && event.currentTarget.blur()}
				aria-label="stake amount in MW"
			/>
			<span class="dim">MW</span>
			<button class="term-btn" onclick={() => stepBet(1)} disabled={atMaxLevel}>+</button>
		</span>
		<span class="dial-fact-sep dim">|</span>
		<span>
			full send pays: <span class="win">{formatMW(winPays)} MW</span>
		</span>
	</div>

	<!-- overdrive/golden copy lives on the result screen the first time one
	     lands (brief 3 / 8); the boot screen keeps only the max win callout -->
	<div class="dial-spice dim">
		max win <span class="win">{formatMW(maxPays)} MW</span>
	</div>

	<div class="boot-row">
		<button class="boot-btn" onclick={boot} disabled={!canBoot}>&gt;&gt; BOOT RIG &lt;&lt;</button>
		{#if !stateConfig.jurisdiction.disabledTurbo}
			<TurboToggle
				checked={stateBet.isTurbo}
				onToggle={(value) => stateBetDerived.updateIsTurbo(value, { persistent: true })}
			/>
		{/if}
	</div>
	{#if !stateBetDerived.isBetCostAvailable()}
		<!-- red is reserved for the meltdown moment (brief 7) -->
		<div class="warn">insufficient power reserve -- lower the stake</div>
	{/if}
	<div class="key-hint-line dim">[SPACE] to boot</div>
</div>

<div class="log-line cursor"></div>
</div>

<div class="settings-corner">
	{#if fairnessOpen}
		<FairnessPanel onClose={() => (fairnessOpen = false)} />
	{/if}
	{#if settingsOpen}
		<div class="settings-pop">
			<label>
				<input
					type="checkbox"
					checked={stateSession.soundEnabled}
					onchange={(event) => (stateSession.soundEnabled = event.currentTarget.checked)}
				/>
				sound
			</label>
			<label><input type="checkbox" bind:checked={scanlines} /> scanlines</label>
			<label><input type="checkbox" bind:checked={flicker} /> flicker</label>
		</div>
	{/if}
	<button
		class="fairness-btn"
		onclick={() => {
			fairnessOpen = !fairnessOpen;
			settingsOpen = false;
		}}
	>
		[FAIRNESS]
	</button>
	<button
		class="dots-btn"
		onclick={() => {
			settingsOpen = !settingsOpen;
			fairnessOpen = false;
		}}
		aria-label="display and sound settings"
	>
		&#8943;
	</button>
</div>
</div>
