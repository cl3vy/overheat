import { recordBookEvent, type BookEventHandlerMap } from 'utils-book';
import { stateBet, stateConfig } from 'state-shared';
import { waitForTimeout } from 'utils-shared/wait';

import { BOOK_AMOUNT_SCALE, LADDERS, RIG_MAP, type LadderRung } from './constants';
import { stateGame, pushLog } from './stateGame.svelte';
import { recordRound } from './stateSession.svelte';
import {
	buildClimbPath,
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
	playBankTick,
	playOverdriveSurge,
} from './sound';
import type { BookEvent, BookEventOfType, BookEventContext } from './typesBookEvent';

const TICK_MS = 33;

/** Turbo or resume fast-forward: apply the event state with no animation. */
const isInstant = (bookEvent: BookEvent) =>
	stateBet.isTurbo || bookEvent.index < stateGame.skipUntilIndex;

/** Light up rungs the display temperature has crossed (live, during climb). */
const syncSecured = (rungs: LadderRung[], silent = false) => {
	let crossed = 0;
	let secured = 0;
	for (const rung of rungs) {
		if (stateGame.currentTemp >= rung.temp - 1e-9) {
			crossed += 1;
			secured = rung.bank;
		} else break;
	}
	if (crossed > stateGame.rungsCrossed) {
		stateGame.rungsCrossed = crossed;
		stateGame.securedMult = secured;
		// the SECURED YIELD box is the single source of truth for banked
		// progress (R2 1.3): a tick sound marks the lock, no log line
		if (!silent) playBankTick(crossed);
	}
};

const animateSegments = async (segments: ClimbSegment[], rungs?: LadderRung[]) => {
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
			if (rungs) syncSecured(rungs);
		}
		stateGame.currentTemp = segment.toTemp;
		if (rungs) syncSecured(rungs);
	}
};

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
		stateGame.securedMult = 0;
		stateGame.rungsCrossed = 0;
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
		const ladder = LADDERS[stateGame.rigTier];

		if (isInstant(bookEvent)) {
			stateGame.currentTemp = bookEvent.crashTemp;
			syncSecured(ladder.rungs, true);
			return;
		}

		startHum();
		// on overdrive wins crashTemp is the boosted bank point above the target:
		// run the normal suspense climb to the target first, then surge past it
		const overdrive = isWin && bookEvent.crashTemp > stateGame.targetTemp + 1e-9;
		const segments = buildClimbPath({
			targetTemp: stateGame.targetTemp,
			endTemp: overdrive ? stateGame.targetTemp : bookEvent.crashTemp,
			rungTemps: ladder.rungs.map((rung) => rung.temp),
			isWin,
			minimumRoundDurationMs: stateConfig.jurisdiction.minimumRoundDuration,
		});
		await animateSegments(segments, ladder.rungs);
		if (overdrive) {
			// the overdrive story plays out in the center column (temp readout
			// tag + celebration headline), not in the log (R2 1.3)
			playOverdriveSurge(bookEvent.crashTemp / stateGame.targetTemp);
			await animateSegments(buildOverdriveSegments(stateGame.targetTemp, bookEvent.crashTemp));
		}
	},

	bank: async (bookEvent: BookEventOfType<'bank'>) => {
		recordBookEvent({ bookEvent });
		// the climb animation already showed this rung locking in; the book
		// event pins the exact secured state (and covers turbo/resume paths)
		const ladder = LADDERS[stateGame.rigTier];
		const rungIndex = ladder.rungs.findIndex(
			(rung) => Math.round(rung.bank * BOOK_AMOUNT_SCALE) === bookEvent.amount,
		);
		stateGame.securedMult = bookEvent.amount / BOOK_AMOUNT_SCALE;
		if (rungIndex >= 0) {
			stateGame.rungsCrossed = Math.max(stateGame.rungsCrossed, rungIndex + 1);
		}
	},

	meltdown: async (bookEvent: BookEventOfType<'meltdown'>) => {
		recordBookEvent({ bookEvent });
		const instant = isInstant(bookEvent);
		const kept = bookEvent.amount / BOOK_AMOUNT_SCALE;

		stateGame.currentTemp = bookEvent.crashTemp;
		stateGame.crashTemp = bookEvent.crashTemp;
		stateGame.securedMult = kept;
		stateGame.phase = 'fried';
		stopHum();
		if (!instant) playMeltdown();

		// the meltdown story (banner, near miss, checkpoints held) renders in
		// the center column; the log stays boot flavor only (R2 1.3)
		if (!instant) await waitForTimeout(700);
	},

	shutdown: async (bookEvent: BookEventOfType<'shutdown'>) => {
		recordBookEvent({ bookEvent });
		const instant = isInstant(bookEvent);
		const tier = bookEvent.tier ?? 'clean';
		const ladder = LADDERS[stateGame.rigTier];

		stateGame.currentTemp = bookEvent.bankedAt;
		stateGame.couldHaveReached = bookEvent.couldHaveReached;
		stateGame.winTier = tier;
		stateGame.securedMult = bookEvent.bankedAt;
		stateGame.rungsCrossed = ladder.rungs.length;
		// seed the win display; the setTotalWin money event that follows
		// carries the same value (payout is bankedAt by construction)
		stateBet.winBookEventAmount = Math.round(bookEvent.bankedAt * 100);
		stateGame.phase = 'banked';
		stopHum();
		if (!instant) playBankLock();
		// win fanfare, tier headline and post-mortem all render in the
		// RunView celebration; the log stays boot flavor only (R2 1.3)
		if (!instant) await waitForTimeout(650);
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
		// reaching the target counts as a win; partial checkpoint banks are
		// recorded with their payout but win=false (the rig still fried)
		const win = shutdownEvent !== undefined;
		recordRound({
			rigTier: stateGame.rigTier,
			targetTemp: stateGame.targetTemp,
			crashTemp: win
				? (shutdownEvent?.couldHaveReached ?? stateGame.targetTemp)
				: (meltdownEvent?.crashTemp ?? stateGame.crashTemp),
			win,
			payoutMW: (bookEvent.amount / BOOK_AMOUNT_SCALE) * stateBet.wageredBetAmount,
			payoutMult: bookEvent.amount / BOOK_AMOUNT_SCALE,
			tier: shutdownEvent?.tier,
		});
	},
};
