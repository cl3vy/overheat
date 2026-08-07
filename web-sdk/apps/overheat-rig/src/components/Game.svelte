<script lang="ts">
	import './app.css';
	import { onMount, untrack } from 'svelte';

	import { stateAuthDerived, stateBet, stateConfig, stateModal, stateUrlDerived } from 'state-shared';

	import EnableGameActor from './EnableGameActor.svelte';
	import RigSelect from './RigSelect.svelte';
	import RunView from './RunView.svelte';
	import RulesPanel from './RulesPanel.svelte';
	import ReplaySummaryPanel from './ReplaySummaryPanel.svelte';
	import ErrorPanel from './ErrorPanel.svelte';
	import { RIGS, RTP } from '../game/constants';
	import { getContext } from '../game/context';
	import { formatMoney, formatMW, toBaseUnits } from '../game/money';
	import { prefersReducedMotion } from '../game/motion';
	import { refreshBalance } from '../game/rgs';
	import { stateGame } from '../game/stateGame.svelte';
	import { t } from '../game/t';
	import { requestBoot } from '../game/utils';

	const context = getContext();

	// read-only replay window: no wallet UI, no live betting entry (QA phase 3)
	const isReplay = stateUrlDerived.replay();
	// Stake: show bet summary and wait for Start Replay before any frames play
	let replaySummaryOpen = $state(isReplay);

	let scanlines = $state(true);
	// flicker is opt-in for photosensitivity (QA 6.5); scanlines stay
	let flicker = $state(false);
	let rulesOpen = $state(false);

	// jurisdiction.displaySessionTimer — elapsed session clock
	const sessionStartedAt = Date.now();
	let sessionElapsedMs = $state(0);
	const sessionTimerLabel = $derived.by(() => {
		const totalSec = Math.floor(sessionElapsedMs / 1000);
		const h = Math.floor(totalSec / 3600);
		const m = Math.floor((totalSec % 3600) / 60);
		const s = totalSec % 60;
		const pad = (n: number) => String(n).padStart(2, '0');
		return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
	});

	// jurisdiction.displayNetPosition — delta vs balance at authenticate
	const sessionStartBalance = stateBet.balanceAmount;
	const netPosition = $derived(stateBet.balanceAmount - sessionStartBalance);

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
				const progress = Math.min((performance.now() - startedAt) / durationMs, 1);
				displayedBalance =
					from + (target - from) * (1 - (1 - progress) * (1 - progress));
				if (progress < 1) {
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
		if (stateAuthDerived.isFailed()) return;
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

	const startReplay = () => {
		if (!isReplay || !replaySummaryOpen) return;
		replaySummaryOpen = false;
		context.eventEmitter.broadcast({ type: 'resumeBet' });
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
		// (QA 5.5): the actor resumes active rounds and settles inactive ones.
		// Replay waits on the summary popup — do not start frames yet.
		if (stateBet.betToResume?.active && stateBet.betToResume.mode) {
			stateBet.activeBetModeKey = stateBet.betToResume.mode;
		}
		if (!isReplay) {
			context.eventEmitter.broadcast({ type: 'resumeBet' });
		}

		// keep the balance fresh between rounds
		const balanceInterval = setInterval(() => {
			if (context.stateXstateDerived.isIdle()) refreshBalance();
		}, 30_000);

		let timerInterval: ReturnType<typeof setInterval> | undefined;
		if (stateConfig.jurisdiction.displaySessionTimer) {
			timerInterval = setInterval(() => {
				sessionElapsedMs = Date.now() - sessionStartedAt;
			}, 1000);
		}

		return () => {
			clearInterval(balanceInterval);
			if (timerInterval) clearInterval(timerInterval);
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
		<span class="term-title-full">{t('hdr_console_full')}</span>
		<span class="term-title-mini">{t('brand_overheat')}</span>
		<span class="term-header-right">
			<button class="rules-btn" onclick={() => (rulesOpen = !rulesOpen)}>{t('btn_rules')}</button>
			{#if stateConfig.jurisdiction.displaySessionTimer}
				<span class="dim">{t('hdr_session', { time: sessionTimerLabel })}</span>
			{/if}
			{#if stateConfig.jurisdiction.displayRTP}
				<span class="dim">{t('hdr_rtp', { percent: (RTP * 100).toFixed(1) })}</span>
			{/if}
			{#if isReplay}
				<span class="dim">{t('hdr_replay')}</span>
			{:else}
				{t('hdr_pwr_reserve')}
				<span class="win pwr-reserve" class:flash={balanceFlash}>
					{formatMoney(toBaseUnits(displayedBalance))}
				</span>
				<span class="dim mw-garnish">{formatMW(toBaseUnits(displayedBalance))}</span>
				{#if stateConfig.jurisdiction.displayNetPosition}
					<span class="dim">
						{t('hdr_net', {
							amount: `${netPosition >= 0 ? '+' : ''}${formatMoney(toBaseUnits(netPosition))}`,
						})}
					</span>
				{/if}
			{/if}
			{#if stateBet.isTurbo}<span class="warn header-turbo">{t('hdr_turbo')}</span>{/if}
		</span>
	</div>

	<div class="term-main">
		{#if isReplay}
			<!-- never drop a replay viewer into the live betting UI (QA phase 3) -->
			{#if replaySummaryOpen}
				<ReplaySummaryPanel onStart={startReplay} />
			{:else if stateGame.phase === 'idle'}
				<div class="log-line dim">{t('status_loading_replay')}</div>
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
