<script lang="ts">
	import './app.css';
	import { onMount, untrack } from 'svelte';

	import { stateBet, stateConfig, stateModal, stateUrlDerived } from 'state-shared';

	import EnableGameActor from './EnableGameActor.svelte';
	import RigSelect from './RigSelect.svelte';
	import RunView from './RunView.svelte';
	import RulesPanel from './RulesPanel.svelte';
	import ErrorPanel from './ErrorPanel.svelte';
	import { getContext } from '../game/context';
	import { stateGame } from '../game/stateGame.svelte';
	import { formatMoney, formatMW } from '../game/money';
	import { refreshBalance } from '../game/rgs';
	import { requestBoot } from '../game/utils';

	const context = getContext();

	// read-only replay window: no wallet UI, no live betting entry (QA phase 3)
	const isReplay = stateUrlDerived.replay();

	let scanlines = $state(true);
	// flicker is opt-in for photosensitivity (QA 6.5); scanlines stay
	let flicker = $state(false);
	let rulesOpen = $state(false);


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
	class="crt"
	class:scanlines
	class:flicker
	class:melt={stateGame.phase === 'fried'}
	class:bank={stateGame.phase === 'banked'}
>
	<div class="term-header">
		<span>OVERHEAT // MINING RIG THERMAL CONSOLE</span>
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
			{#if stateBet.isTurbo}<span class="warn"> [TURBO]</span>{/if}
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
