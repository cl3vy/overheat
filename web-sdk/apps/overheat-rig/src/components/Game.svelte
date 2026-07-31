<script lang="ts">
	import './app.css';
	import { onMount, untrack } from 'svelte';

	import { stateBet, stateBetDerived, stateConfig, stateModal } from 'state-shared';

	import { RIGS } from '../game/constants';

	import EnableGameActor from './EnableGameActor.svelte';
	import RigSelect from './RigSelect.svelte';
	import RunView from './RunView.svelte';
	import ErrorPanel from './ErrorPanel.svelte';
	import { getContext } from '../game/context';
	import { stateGame } from '../game/stateGame.svelte';
	import { refreshBalance } from '../game/rgs';

	const context = getContext();

	let scanlines = $state(true);
	let flicker = $state(true);

	const formatMW = (value: number) =>
		value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

	// header balance: decreases (stake taken) snap instantly, increases roll
	// up like an odometer with a green flash so the player watches it grow
	let displayedBalance = $state(0);
	let balanceFlash = $state(false);
	let balanceAnimId = 0;
	$effect(() => {
		const target = stateBet.balanceAmount;
		untrack(() => {
			if (target === displayedBalance) return;
			const id = ++balanceAnimId;
			if (target < displayedBalance || displayedBalance === 0) {
				displayedBalance = target;
				return;
			}
			const from = displayedBalance;
			balanceFlash = true;
			const startedAt = performance.now();
			const durationMs = 900;
			const step = () => {
				if (id !== balanceAnimId) return;
				const t = Math.min((performance.now() - startedAt) / durationMs, 1);
				displayedBalance = from + (target - from) * (1 - (1 - t) * (1 - t));
				if (t < 1) {
					requestAnimationFrame(step);
				} else {
					displayedBalance = target;
					setTimeout(() => {
						if (id === balanceAnimId) balanceFlash = false;
					}, 350);
				}
			};
			requestAnimationFrame(step);
		});
	});

	// spacebar = bet, from the rig select screen or straight off a settled round
	const onKeydown = (event: KeyboardEvent) => {
		if (event.code !== 'Space' || event.repeat) return;
		if (stateConfig.jurisdiction.disabledSpacebar) return;
		if (stateModal.modal) return;
		const tag = (event.target as HTMLElement | null)?.tagName;
		if (tag === 'INPUT' || tag === 'TEXTAREA') return;
		// swallow native space behavior (button re-click, page scroll)
		event.preventDefault();
		if (!context.stateXstateDerived.isIdle()) return;
		if (!stateBetDerived.isBetCostAvailable()) return;
		if (!RIGS.some((rig) => rig.id === stateBet.activeBetModeKey)) return;
		context.eventEmitter.broadcast({ type: 'bet' });
	};

	onMount(() => {
		// no Pixi canvas in this game: release the SDK loading screen
		context.stateApp.loaded = true;
		context.stateLayout.showLoadingScreen = false;

		window.addEventListener('keydown', onKeydown);

		// resume an unfinished round returned by /wallet/authenticate
		if (stateBet.betToResume?.active && stateBet.betToResume.mode) {
			stateBet.activeBetModeKey = stateBet.betToResume.mode;
		}
		context.eventEmitter.broadcast({ type: 'resumeBet' });

		// keep the balance fresh between rounds
		const balanceInterval = setInterval(() => {
			if (context.stateXstateDerived.isIdle()) refreshBalance();
		}, 30_000);
		return () => {
			clearInterval(balanceInterval);
			window.removeEventListener('keydown', onKeydown);
		};
	});
</script>

<EnableGameActor />

<div class="tv-shell">
<div
	class="crt"
	class:scanlines
	class:flicker
	class:melt={stateGame.phase === 'fried'}
	class:bank={stateGame.phase === 'banked'}
>
	<div class="term-header">
		<span>OVERHEAT // MINING RIG THERMAL CONSOLE v1.0</span>
		<span>
			PWR RESERVE:
			<span class="win pwr-reserve" class:flash={balanceFlash}>
				{formatMW(displayedBalance)} MW
			</span>
			{#if stateBet.isTurbo}<span class="warn"> [TURBO]</span>{/if}
		</span>
	</div>

	<div class="term-main">
		{#if stateGame.phase === 'idle'}
			<RigSelect bind:scanlines bind:flicker />
		{:else}
			<RunView />
		{/if}
	</div>

	<ErrorPanel />
	<div class="crt-glass" aria-hidden="true"></div>
</div>
</div>
