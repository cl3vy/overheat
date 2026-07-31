import { recordBookEvent, type BookEventHandlerMap } from 'utils-book';
import { stateBet, stateConfig } from 'state-shared';
import { waitForTimeout } from 'utils-shared/wait';

import { BOOK_AMOUNT_SCALE, RIG_MAP } from './constants';
import { stateGame, pushLog } from './stateGame.svelte';
import { recordRound } from './stateSession.svelte';
import {
	buildClimb,
	buildOverdriveSegments,
	applyEase,
	jitterOffset,
	type ClimbSegment,
} from './pacing';
import {
	playBoot,
	startHum,
	setHumLevel,
	stopHum,
	playMeltdown,
	playBankLock,
	playOverdriveSurge,
	playSalvage,
} from './sound';
import type { BookEvent, BookEventOfType, BookEventContext } from './typesBookEvent';

const TICK_MS = 33;

/** Turbo or resume fast-forward: apply the event state with no animation. */
const isInstant = (bookEvent: BookEvent) =>
	stateBet.isTurbo || bookEvent.index < stateGame.skipUntilIndex;

const animateSegments = async (segments: ClimbSegment[]) => {
	for (const segment of segments) {
		const fromTemp = stateGame.currentTemp;
		const startedAt = performance.now();
		let elapsed = 0;
		while (elapsed < segment.durationMs) {
			await waitForTimeout(TICK_MS);
			elapsed = performance.now() - startedAt;
			const t = Math.min(elapsed / segment.durationMs, 1);
			const base = fromTemp + (segment.toTemp - fromTemp) * applyEase(t, segment.ease);
			stateGame.currentTemp = segment.jitter
				? Math.max(base + jitterOffset(elapsed, stateGame.targetTemp), 1)
				: base;
			setHumLevel((stateGame.currentTemp - 1) / Math.max(stateGame.targetTemp - 1, 0.0001));
		}
		stateGame.currentTemp = segment.toTemp;
	}
};

// deterministic per round (keyed off the crash temp) so replays match
const MELTDOWN_SCENES: string[][] = [
	['!! VRM FAILURE -- voltage regulator vaporised', '   (crackle) .. magic smoke released'],
	['!! THERMAL PASTE EVAPORATED', '   core delaminating .. (~~~) . o O ( smoke )'],
	['!! FAN BEARING SEIZED @ 14,000 RPM', '   cascade failure in 3.. 2.. 1..'],
	['!! SILICON SLAG DETECTED IN SOCKET', '   this rig is now modern art'],
	['!! POWER STAGE SHORT -- BREAKER TRIPPED', '   the whole block just went dark'],
	['!! DIE CRACKED ALONG THE HEAT SPREADER', '   warranty status: hilarious'],
];

const INSTANT_BUST_SCENE = ['!! POST FAILURE -- FRIED ON BOOT', '   it never even mined a block'];

export const bookEventHandlerMap: BookEventHandlerMap<BookEvent, BookEventContext> = {
	boot: async (bookEvent: BookEventOfType<'boot'>) => {
		recordBookEvent({ bookEvent });
		const instant = isInstant(bookEvent);
		const rig = RIG_MAP[bookEvent.rigTier];

		stateGame.phase = 'booting';
		stateGame.rigTier = bookEvent.rigTier;
		stateGame.targetTemp = bookEvent.targetTemp;
		stateGame.hashrate = bookEvent.hashrate;
		stateGame.currentTemp = 1;
		stateGame.crashTemp = 0;
		stateGame.couldHaveReached = 0;
		stateGame.winTier = null;
		stateGame.salvageMult = 0;
		stateGame.logs = [];

		if (!instant) playBoot();

		const bootLines = [
			`> POWER ON -- RIG: ${rig?.name ?? bookEvent.rigTier}`,
			'> BIOS OK .. volt rails nominal',
			`> hashrate online: ${bookEvent.hashrate} MH/s`,
			`> shutdown temp locked: ${bookEvent.targetTemp.toFixed(2)}x`,
			'> mining...',
		];
		for (const line of bootLines) {
			pushLog(line, 'dim');
			if (!instant) await waitForTimeout(130);
		}

		stateGame.phase = 'heating';
	},

	heat: async (bookEvent: BookEventOfType<'heat'>, { bookEvents }: BookEventContext) => {
		recordBookEvent({ bookEvent });
		const isWin = bookEvents.some((event) => event.type === 'shutdown');

		if (isInstant(bookEvent)) {
			stateGame.currentTemp = bookEvent.crashTemp;
			return;
		}

		startHum();
		// on overdrive wins crashTemp is the boosted bank point above the target:
		// run the normal suspense climb to the target first, then surge past it
		const overdrive = isWin && bookEvent.crashTemp > stateGame.targetTemp + 1e-9;
		const segments = buildClimb({
			targetTemp: stateGame.targetTemp,
			crashTemp: overdrive ? stateGame.targetTemp : bookEvent.crashTemp,
			isWin,
			minimumRoundDurationMs: stateConfig.jurisdiction.minimumRoundDuration,
		});
		await animateSegments(segments);
		if (overdrive) {
			const multiple = bookEvent.crashTemp / stateGame.targetTemp;
			pushLog('!! SHUTDOWN COMMAND REJECTED -- THERMAL LIMITER SLIPPED', 'warn');
			playOverdriveSurge(multiple);
			await animateSegments(buildOverdriveSegments(stateGame.targetTemp, bookEvent.crashTemp));
		}
	},

	meltdown: async (bookEvent: BookEventOfType<'meltdown'>) => {
		recordBookEvent({ bookEvent });
		const instant = isInstant(bookEvent);

		stateGame.currentTemp = bookEvent.crashTemp;
		stateGame.crashTemp = bookEvent.crashTemp;
		stateGame.phase = 'fried';
		stopHum();
		if (!instant) playMeltdown();

		const isInstantBust = bookEvent.crashTemp <= 1.005;
		const scene = isInstantBust
			? INSTANT_BUST_SCENE
			: MELTDOWN_SCENES[Math.round(bookEvent.crashTemp * 100) % MELTDOWN_SCENES.length];

		pushLog(`!! THERMAL RUNAWAY @ ${bookEvent.crashTemp.toFixed(2)}x`, 'fault');
		if (!instant) await waitForTimeout(220);
		for (const line of scene) {
			pushLog(line, line.startsWith('!!') ? 'fault' : 'dim');
			if (!instant) await waitForTimeout(180);
		}

		// near miss: rub it in
		const shortBy = stateGame.targetTemp - bookEvent.crashTemp;
		if (!isInstantBust && shortBy / Math.max(stateGame.targetTemp - 1, 0.0001) < 0.1) {
			pushLog(`   ${shortBy.toFixed(2)}x short of shutdown. brutal.`, 'warn');
		}
		if (!instant) await waitForTimeout(400);
	},

	shutdown: async (bookEvent: BookEventOfType<'shutdown'>) => {
		recordBookEvent({ bookEvent });
		const instant = isInstant(bookEvent);
		const tier = bookEvent.tier ?? 'clean';

		stateGame.currentTemp = bookEvent.bankedAt;
		stateGame.couldHaveReached = bookEvent.couldHaveReached;
		stateGame.winTier = tier;
		// seed the win display; the setTotalWin money event that follows
		// carries the same value (payout is bankedAt by construction)
		stateBet.winBookEventAmount = Math.round(bookEvent.bankedAt * 100);
		stateGame.phase = 'banked';
		stopHum();
		if (!instant) playBankLock();
		// win fanfare is played by the RunView in-place celebration

		if (tier === 'clean') {
			pushLog(`>> TARGET TEMP ${bookEvent.bankedAt.toFixed(2)}x REACHED`, 'win');
			if (!instant) await waitForTimeout(250);
			pushLog('>> SAFE SHUTDOWN -- COINS BANKED', 'win');
		} else if (tier === 'overdrive') {
			pushLog(`>> OVERDRIVE HOLD @ ${bookEvent.bankedAt.toFixed(2)}x -- 1.5x TARGET`, 'win');
			if (!instant) await waitForTimeout(250);
			pushLog('>> EMERGENCY SHUTDOWN CAUGHT IT -- BONUS COINS BANKED', 'win');
		} else if (tier === 'critical') {
			pushLog(`>> CRITICAL OVERDRIVE @ ${bookEvent.bankedAt.toFixed(2)}x -- 3x TARGET`, 'win');
			if (!instant) await waitForTimeout(250);
			pushLog('>> BREAKER SLAMMED -- TRIPLE YIELD BANKED', 'win');
		} else {
			pushLog(`>> GOLDEN SHUTDOWN @ ${bookEvent.bankedAt.toFixed(2)}x -- 10x TARGET`, 'win');
			if (!instant) await waitForTimeout(250);
			pushLog('>> THE SILICON ASCENDED. 10x YIELD BANKED.', 'win');
		}
		if (!instant) await waitForTimeout(400);
		if (bookEvent.couldHaveReached > bookEvent.bankedAt) {
			pushLog(
				`>> post-mortem: silicon would have survived to ${bookEvent.couldHaveReached.toFixed(2)}x`,
				'dim',
			);
		}
	},

	salvage: async (bookEvent: BookEventOfType<'salvage'>) => {
		recordBookEvent({ bookEvent });
		const instant = isInstant(bookEvent);

		stateGame.salvageMult = bookEvent.amount / BOOK_AMOUNT_SCALE;
		stateBet.winBookEventAmount = bookEvent.amount;
		if (!instant) {
			await waitForTimeout(500);
			playSalvage();
		}
		pushLog('>> scavenging the wreck...', 'dim');
		if (!instant) await waitForTimeout(350);
		pushLog(
			`>> SCRAP SALVAGE: ${stateGame.salvageMult.toFixed(2)}x stake recovered from the slag`,
			'warn',
		);
	},

	setTotalWin: async (bookEvent: BookEventOfType<'setTotalWin'>) => {
		// book units: payout multiplier x 100
		stateBet.winBookEventAmount = bookEvent.amount;
	},

	finalWin: async (bookEvent: BookEventOfType<'finalWin'>, { bookEvents }: BookEventContext) => {
		stateBet.winBookEventAmount = bookEvent.amount;

		// session history (display-only texture: strip + stats)
		const meltdownEvent = bookEvents.find(
			(event): event is BookEventOfType<'meltdown'> => event.type === 'meltdown',
		);
		const shutdownEvent = bookEvents.find(
			(event): event is BookEventOfType<'shutdown'> => event.type === 'shutdown',
		);
		const salvageEvent = bookEvents.find(
			(event): event is BookEventOfType<'salvage'> => event.type === 'salvage',
		);
		// a salvage is still a bust: only a real shutdown counts as a win
		const win = shutdownEvent !== undefined;
		recordRound({
			rigTier: stateGame.rigTier,
			targetTemp: stateGame.targetTemp,
			crashTemp: win
				? (shutdownEvent?.couldHaveReached ?? stateGame.targetTemp)
				: (meltdownEvent?.crashTemp ?? stateGame.crashTemp),
			win,
			payoutMW: (bookEvent.amount / BOOK_AMOUNT_SCALE) * stateBet.wageredBetAmount,
			tier: shutdownEvent ? (shutdownEvent.tier ?? 'clean') : salvageEvent ? 'salvage' : undefined,
		});
	},
};
