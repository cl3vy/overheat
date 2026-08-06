<script lang="ts">
	import { onMount } from 'svelte';

	import { stateBet, stateBetDerived, stateConfig } from 'state-shared';

	import { LADDERS, MODE_MAX_WIN, RIGS } from '../game/constants';
	import { formatMoney, formatMW } from '../game/money';
	import {
		flavorForSocial,
		labelCashOutTarget,
		wordCashOut,
		wordPays,
		wordStake,
	} from '../game/socialCopy';
	import { getContext } from '../game/context';
	import { isCoarsePointer, prefersReducedMotion } from '../game/motion';
	import { stateSession, sessionStats } from '../game/stateSession.svelte';
	import { requestBoot } from '../game/utils';
	import FairnessPanel from './FairnessPanel.svelte';
	import TurboToggle from './TurboToggle.svelte';

	type Props = { scanlines: boolean; flicker: boolean };

	let { scanlines = $bindable(), flicker = $bindable() }: Props = $props();

	const context = getContext();

	let settingsOpen = $state(false);
	let fairnessOpen = $state(false);
	let bootCharging = $state(false);
	let panelTilt = $state({ x: 0, y: 0 });
	let dialEl = $state<HTMLDivElement | null>(null);

	const betOptions = $derived(stateConfig.betAmountOptions);

	/** Index into authenticate betLevels — the only selectable set. */
	const betIndex = $derived.by(() => {
		const levels = betOptions;
		if (!levels.length) return -1;
		const exact = levels.findIndex(
			(level) => Math.abs(level - stateBet.betAmount) < 1e-9,
		);
		if (exact >= 0) return exact;
		// off-ladder (resume / typed): nearest level for display/stepping
		let best = 0;
		for (let i = 1; i < levels.length; i++) {
			if (Math.abs(levels[i] - stateBet.betAmount) < Math.abs(levels[best] - stateBet.betAmount)) {
				best = i;
			}
		}
		return best;
	});

	let stakeText = $state('');

	// reflect external stake changes (steppers, seeding, balance clamps) in the field
	$effect(() => {
		stakeText = stateBet.betAmount.toFixed(2);
	});

	const nearestBetLevel = (raw: number) => {
		const levels = betOptions;
		if (!levels.length) return raw;
		const { minBet, maxBet } = stateConfig;
		const clamped = Math.min(Math.max(raw, minBet), maxBet);
		return levels.reduce((best, level) =>
			Math.abs(level - clamped) < Math.abs(best - clamped) ? level : best,
		);
	};

	/**
	 * Commit a typed stake by snapping to the nearest authenticate betLevels entry.
	 * Manual field stays; stepBet does not drive selection.
	 */
	const commitStake = () => {
		const raw = Number(stakeText.replace(/,/g, ''));
		if (!Number.isFinite(raw) || raw <= 0) {
			stakeText = stateBet.betAmount.toFixed(2);
			return;
		}
		stateBetDerived.setBetAmount(nearestBetLevel(raw));
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

	const cashOut = $derived(wordCashOut());
	const paysWord = $derived(wordPays());
	const stakeWord = $derived(wordStake());
	const cashOutTitle = $derived(labelCashOutTarget());
	const rigFlavor = $derived(flavorForSocial(rig.flavor));

	// meltdown clause gated on whether the active mode banks checkpoints
	// (all current rigs do; the gate keeps the copy honest if one ever doesn't)
	const meltdownClause = $derived(
		(LADDERS[rig.id]?.rungs.length ?? 0) > 0
			? 'if it melts down first, you keep only what the checkpoints banked.'
			: `if it melts down first, you lose the ${stakeWord}.`,
	);

	// hit frequency stays as a standalone mode descriptor -- never rendered
	// on the same line as any payout, odds-for-payout, or profit figure
	const anyPayout = $derived(rigLadder.anyPayoutProb * 100);
	const winPays = $derived(stateBet.betAmount * rig.targetTemp);
	const maxPays = $derived(stateBet.betAmount * MODE_MAX_WIN[rig.id]);
	// 0..1 along the ladder, drives the heat colors
	const heat = $derived(rigIndex / (RIGS.length - 1));
	const heatClass = $derived(heat < 0.35 ? 'heat-low' : heat < 0.7 ? 'heat-mid' : 'heat-high');

	// ---------------------------------------------------------- stats strip
	// HOTTEST + BEST BANK only -- no RECENT chips, streak, or per-rig best

	const hottest = $derived(sessionStats.hottestRun());
	const bestBank = $derived(sessionStats.bestBankMW());
	const hasPeaks = $derived(hottest > 0 || bestBank > 0);

	const setRigIndex = (index: number) => {
		const clamped = Math.min(Math.max(index, 0), RIGS.length - 1);
		stateBet.activeBetModeKey = RIGS[clamped].id;
	};

	/** +/- moves to adjacent betLevels entries (index-based; not stepBet). */
	const stepBetAmount = (direction: 1 | -1) => {
		const levels = betOptions;
		if (!levels.length || betIndex < 0) return;
		const next = betIndex + direction;
		if (next < 0 || next >= levels.length) return;
		stateBetDerived.setBetAmount(levels[next]);
	};

	const atMinLevel = $derived(betIndex <= 0);
	const atMaxLevel = $derived(betIndex < 0 || betIndex >= betOptions.length - 1);

	const canBoot = $derived(
		context.stateXstateDerived.isIdle() &&
			stateBetDerived.isBetCostAvailable() &&
			RIGS.some((r) => r.id === stateBet.activeBetModeKey),
	);

	const boot = () => {
		if (!canBoot) return;
		bootCharging = true;
		setTimeout(() => {
			bootCharging = false;
		}, 220);
		requestBoot(context);
	};

	const onPanelMove = (event: PointerEvent) => {
		if (isCoarsePointer() || prefersReducedMotion() || !dialEl) return;
		const rect = dialEl.getBoundingClientRect();
		const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
		const y = ((event.clientY - rect.top) / rect.height) * 2 - 1;
		panelTilt = { x: Math.max(-1, Math.min(1, x)), y: Math.max(-1, Math.min(1, y)) };
	};

	const onPanelLeave = () => {
		panelTilt = { x: 0, y: 0 };
	};

	onMount(() => {
		// live play: Authenticate already set defaultBetLevel. Snap any off-ladder
		// amount onto betLevels so no control can leave an invalid stake selected.
		if (betOptions.length) {
			const onLadder = betOptions.some(
				(option) => Math.abs(option - stateBet.betAmount) < 1e-9,
			);
			if (!onLadder) {
				stateBetDerived.setBetAmount(nearestBetLevel(stateBet.betAmount));
			}
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
			set your auto {cashOut} target. boot the rig. it climbs on its own and
			stops there automatically. {meltdownClause}
		</div>
	</div>
{:else}
	<div class="log-line dim">
		&gt; set your auto {cashOut} target -- the rig climbs on its own and stops there
		automatically. {meltdownClause}
	</div>
{/if}

<!-- single peak row reserved at load so first bank never reflows the page -->
<div class="stats-block">
	<div class="peak-strip" class:strip-empty={!hasPeaks}>
		{#if hasPeaks}
			{#if hottest > 0}
				<span class="peak">HOTTEST <span class="peak-value">{hottest.toFixed(2)}x</span></span>
			{/if}
			{#if bestBank > 0}
				<span class="peak amber">BEST BANK <span class="peak-value">{formatMoney(bestBank)}</span></span>
			{/if}
		{:else}
			<span class="peak dim">HOTTEST --</span>
		{/if}
	</div>
</div>

<div
	class="dial-panel {heatClass}"
	bind:this={dialEl}
	style="--px: {panelTilt.x}; --py: {panelTilt.y}"
	onpointermove={onPanelMove}
	onpointerleave={onPanelLeave}
>
	<div class="dial-body">
		<div class="dial-header">
			<!-- plain meaning is the primary label; the themed name is flavor (R2 3.1) -->
			<span class="dial-title">{cashOutTitle}</span>
			<span class="dial-rig-name">[ {rig.name} ]</span>
		</div>

		<div class="dial-readout">
			<span class="dial-mult">{rig.targetTemp.toFixed(2)}x</span>
			<!-- inline translation: themed label above, plain meaning here (brief 3) -->
			<span class="dial-translate">{cashOut} at {rig.targetTemp.toFixed(2)}x</span>
			<span class="dial-flavor dim">{rigFlavor}</span>
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

		<!-- standalone mode descriptor: never shares a line with any other figure -->
		<div class="dial-facts dial-odds-line">
			<span>
				{paysWord} something: <span class="dial-odds">{anyPayout.toFixed(1)}%</span> of runs
			</span>
		</div>

		<div class="dial-facts stake-facts">
			<span class="stake-row">
				<span class="stake-label">{stakeWord}:</span>
				<button class="term-btn" onclick={() => stepBetAmount(-1)} disabled={atMinLevel}>-</button>
				<input
					class="stake-input"
					type="text"
					inputmode="decimal"
					bind:value={stakeText}
					onblur={commitStake}
					onkeydown={(event) => event.key === 'Enter' && event.currentTarget.blur()}
					aria-label={stakeWord}
				/>
				<button class="term-btn" onclick={() => stepBetAmount(1)} disabled={atMaxLevel}>+</button>
				<!-- real currency is primary; MW is theme garnish (QA 4.1) -->
				<span class="win">{formatMoney(stateBet.betAmount)}</span>
				<span class="dim mw-garnish">{formatMW(stateBet.betAmount)}</span>
			</span>
		</div>

		<!-- one payout line carries both figures (final declutter 1.4) -->
		<div class="dial-spice dim">
			full send {paysWord} <span class="win">{formatMoney(winPays)}</span>,
			up to <span class="win">{formatMoney(maxPays)}</span> on overdrive
		</div>

		<div class="boot-row">
			<button
				class="boot-btn"
				class:charging={bootCharging}
				onclick={boot}
				disabled={!canBoot}>&gt;&gt; BOOT RIG &lt;&lt;</button
			>
			{#if !stateConfig.jurisdiction.disabledTurbo}
				<TurboToggle
					checked={stateBet.isTurbo}
					onToggle={(value) => stateBetDerived.updateIsTurbo(value, { persistent: true })}
				/>
			{/if}
		</div>
		{#if !stateBetDerived.isBetCostAvailable()}
			<!-- red is reserved for the meltdown moment (brief 7) -->
			<div class="warn">insufficient power reserve -- lower the {stakeWord}</div>
		{/if}
		<div class="key-hint-line">[SPACE] to boot</div>
	</div>
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
