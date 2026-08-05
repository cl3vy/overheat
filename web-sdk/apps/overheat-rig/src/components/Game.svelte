<script lang="ts">
	import './app.css';
	import { onMount, untrack } from 'svelte';

	import { stateBet, stateConfig, stateModal, stateUrlDerived } from 'state-shared';

	import EnableGameActor from './EnableGameActor.svelte';
	import RigSelect from './RigSelect.svelte';
	import RunView from './RunView.svelte';
	import RulesPanel from './RulesPanel.svelte';
	import ErrorPanel from './ErrorPanel.svelte';
	import { RIGS } from '../game/constants';
	import { getContext } from '../game/context';
	import { formatMoney, formatMW } from '../game/money';
	import { prefersReducedMotion } from '../game/motion';
	import { refreshBalance } from '../game/rgs';
	import { stateGame } from '../game/stateGame.svelte';
	import { requestBoot } from '../game/utils';

	const context = getContext();

	// read-only replay window: no wallet UI, no live betting entry (QA phase 3)
	const isReplay = stateUrlDerived.replay();

	let scanlines = $state(true);
	// flicker is opt-in for photosensitivity (QA 6.5); scanlines stay
	let flicker = $state(false);
	let rulesOpen = $state(false);

	// ambient heat tier drives background glow + ember tint (visual feel P1)
	const ambientTier = $derived.by(() => {
		if (stateGame.phase === 'fried') return 'ambient-melt';
		if (stateGame.phase === 'banked') return 'ambient-win';
		if (stateGame.phase === 'heating' || stateGame.phase === 'booting') {
			const fill = Math.min(
				Math.max(
					(stateGame.currentTemp - 1) / Math.max(stateGame.targetTemp - 1, 0.0001),
					0,
				),
				1,
			);
			if (fill < 0.35) return 'ambient-low';
			if (fill < 0.7) return 'ambient-mid';
			return 'ambient-high';
		}
		const index = Math.max(
			0,
			RIGS.findIndex((rig) => rig.id === stateBet.activeBetModeKey),
		);
		const heat = index / Math.max(RIGS.length - 1, 1);
		if (heat < 0.35) return 'ambient-low';
		if (heat < 0.7) return 'ambient-mid';
		return 'ambient-high';
	});

	type Ember = { id: number; left: number; delay: number; duration: number; size: number };
	const embers = $derived.by((): Ember[] => {
		if (prefersReducedMotion()) return [];
		return Array.from({ length: 14 }, (_, id) => ({
			id,
			left: 4 + ((id * 37) % 92),
			delay: (id * 0.7) % 8,
			duration: 9 + (id % 5) * 1.4,
			size: 1.5 + (id % 3),
		}));
	});

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

	// spacebar = bet, from the rig select screen or straight off a settled
	// round. QA 2.1: SPACE must boot from ANY focus state (slider, stake
	// field, buttons), so the handler runs in the capture phase, always
	// prevents the default (scroll / re-click / slider nudge) and boots.
	const onKeydown = (event: KeyboardEvent) => {
		if (event.code !== 'Space' || event.repeat) return;
		if (stateConfig.jurisdiction.disabledSpacebar) return;
		if (stateModal.modal || rulesOpen || isReplay) return;
		event.preventDefault();
		const active = document.activeElement as HTMLElement | null;
		if (active && active.tagName === 'INPUT' && active.getAttribute('type') === 'text') {
			// commit a half-typed stake before booting with it
			active.blur();
		}
		requestBoot(context);
	};

	onMount(() => {
		// no Pixi canvas in this game: release the SDK loading screen
		context.stateApp.loaded = true;
		context.stateLayout.showLoadingScreen = false;

		window.addEventListener('keydown', onKeydown, { capture: true });

		// jurisdiction.disabledFullscreen (QA 4.4): this game never offers a
		// fullscreen control of its own, and the flag also forbids the
		// browser Fullscreen API being entered from the shell. Block any
		// attempt so a surrounding iframe / host button can't put us there.
		const blockFullscreen = (event: Event) => {
			if (!stateConfig.jurisdiction.disabledFullscreen) return;
			event.preventDefault();
			if (document.fullscreenElement) {
				document.exitFullscreen?.().catch(() => {});
			}
		};
		document.addEventListener('fullscreenchange', blockFullscreen);

		// resume an unfinished round returned by /wallet/authenticate
		// (QA 5.5): the actor resumes active rounds and settles inactive ones
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
			window.removeEventListener('keydown', onKeydown, { capture: true });
			document.removeEventListener('fullscreenchange', blockFullscreen);
		};
	});
</script>

<EnableGameActor />

<div class="tv-shell">
<div
	class="crt {ambientTier}"
	class:scanlines
	class:flicker
	class:melt={stateGame.phase === 'fried'}
	class:bank={stateGame.phase === 'banked'}
	class:powering={stateGame.poweringUp}
>
	<div class="crt-ambient" aria-hidden="true"></div>
	<div class="crt-embers" aria-hidden="true">
		{#each embers as ember (ember.id)}
			<span
				class="ember"
				style="left: {ember.left}%; animation-delay: {ember.delay}s; animation-duration: {ember.duration}s; width: {ember.size}px; height: {ember.size}px;"
			></span>
		{/each}
	</div>

	<div class="term-header">
		<span class="term-title-full">OVERHEAT // MINING RIG THERMAL CONSOLE</span>
		<span class="term-title-mini">OVERHEAT</span>
		<span class="term-header-right">
			<button class="rules-btn" onclick={() => (rulesOpen = !rulesOpen)}>[RULES]</button>
			{#if isReplay}
				<span class="dim">REPLAY -- ROUND PLAYBACK</span>
			{:else}
				PWR RESERVE:
				<span class="win pwr-reserve" class:flash={balanceFlash}>
					{formatMoney(displayedBalance)}
				</span>
				<span class="dim mw-garnish">{formatMW(displayedBalance)}</span>
			{/if}
			{#if stateBet.isTurbo}<span class="warn header-turbo"> [TURBO]</span>{/if}
		</span>
	</div>

	<div class="term-main">
		{#if isReplay}
			<!-- never drop a replay viewer into the live betting UI (QA phase 3) -->
			{#if stateGame.phase === 'idle'}
				<div class="log-line dim">loading replay...</div>
			{:else}
				<RunView />
			{/if}
		{:else if stateGame.phase === 'idle'}
			<RigSelect bind:scanlines bind:flicker />
		{:else}
			<RunView />
		{/if}
	</div>

	{#if rulesOpen}
		<RulesPanel onClose={() => (rulesOpen = false)} />
	{/if}

	<ErrorPanel />
	<div class="crt-glass" aria-hidden="true"></div>
</div>
</div>
