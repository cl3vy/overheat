<script lang="ts">
	import { onMount } from 'svelte';

	import { stateBet, stateBetDerived, stateConfig } from 'state-shared';

	import { MAX_WIN_MULT, RIGS, SALVAGE_PAYOUT, SALVAGE_PROB, winProbability } from '../game/constants';
	import { getContext } from '../game/context';
	import { stateSession, sessionStats } from '../game/stateSession.svelte';
	import TurboToggle from './TurboToggle.svelte';

	type Props = { scanlines: boolean; flicker: boolean };

	let { scanlines = $bindable(), flicker = $bindable() }: Props = $props();

	const context = getContext();

	let settingsOpen = $state(false);

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
	// any shutdown tier counts as survival (clean / overdrive / critical / golden)
	const survival = $derived(winProbability(rig.targetTemp) * 100);
	// two decimals below 10% so 0.97% never rounds up to a flattering 1.0%
	const survivalLabel = $derived(survival < 10 ? survival.toFixed(2) : survival.toFixed(1));
	const winPays = $derived(stateBet.betAmount * rig.targetTemp);
	const maxPays = $derived(stateBet.betAmount * rig.targetTemp * MAX_WIN_MULT);
	// 0..1 along the ladder, drives the heat colors
	const heat = $derived(rigIndex / (RIGS.length - 1));
	const heatClass = $derived(heat < 0.35 ? 'heat-low' : heat < 0.7 ? 'heat-mid' : 'heat-high');

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
		if (!canBoot) return;
		context.eventEmitter.broadcast({ type: 'bet' });
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
<div class="log-line dim">&gt; dial in a shutdown temp -- that's your cashout multiplier</div>
<div class="log-line dim">&gt; hotter runs pay more. hotter runs fry more.</div>

{#if stateSession.rounds.length > 0}
	<div class="history-strip">
		<span class="dim">RECENT:</span>
		{#each stateSession.rounds.slice(-14) as round, index (index)}
			<span
				class="history-chip {round.tier === 'golden'
					? 'chip-golden'
					: round.tier === 'salvage'
						? 'chip-salvage'
						: round.win
							? 'chip-win'
							: 'chip-bust'}"
			>
				{round.crashTemp.toFixed(2)}x
			</span>
		{/each}
		<span class="dim stats-inline">
			| wins {sessionStats.wins()}/{sessionStats.runs()} | hottest {sessionStats
				.hottestRun()
				.toFixed(2)}x | best bank {sessionStats.bestBankMW().toFixed(2)} MW
		</span>
	</div>
{/if}

<div class="dial-panel {heatClass}">
	<div class="dial-header">
		<span class="dial-title dim">SHUTDOWN TEMP</span>
		<span class="dial-rig-name">[ {rig.name} ]</span>
	</div>

	<div class="dial-readout">
		<span class="dial-mult">{rig.targetTemp.toFixed(2)}x</span>
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

	<div class="dial-facts">
		<span>
			survival odds: <span class="dial-odds">{survivalLabel}%</span>
		</span>
		<span class="dial-fact-sep dim">|</span>
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
			win pays: <span class="win">{formatMW(winPays)} MW</span>
		</span>
	</div>

	<div class="dial-spice dim">
		shutdowns can slip into <span class="warn">OVERDRIVE</span>: 1.5x / 3x /
		<span class="gold-text">10x GOLDEN</span> the payout -- max win
		<span class="win">{formatMW(maxPays)} MW</span>
	</div>
	<div class="dial-spice dim">
		melted rigs salvage <span class="warn">{SALVAGE_PAYOUT.toFixed(2)}x scrap</span> about
		{(SALVAGE_PROB * 100).toFixed(1)}% of runs
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
		<div class="fault">insufficient power reserve</div>
	{/if}
	<div class="key-hint-line dim">[SPACE] to boot</div>
</div>

<div class="log-line cursor"></div>
</div>

<div class="settings-corner">
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
		class="dots-btn"
		onclick={() => (settingsOpen = !settingsOpen)}
		aria-label="display and sound settings"
	>
		&#8943;
	</button>
</div>
</div>
