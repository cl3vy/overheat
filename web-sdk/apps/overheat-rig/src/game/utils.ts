import { stateBet, stateBetDerived } from 'state-shared';
import { createPlayBookUtils } from 'utils-book';

import { bookEventHandlerMap } from './bookEventHandlerMap';
import { RIGS } from './constants';
import type { getContext } from './context';
import { stateGame } from './stateGame.svelte';
import { stateSession } from './stateSession.svelte';
import type { Bet } from './typesBookEvent';

export const { playBookEvent, playBookEvents } = createPlayBookUtils({ bookEventHandlerMap });

/** Minimum gap between /wallet/play requests. Turbo rounds settle in well
 * under a second, so an unthrottled space-mash can hammer the RGS several
 * times per second and get bets rejected. */
const BOOT_COOLDOWN_MS = 600;
let lastBootAt = 0;

/**
 * The single entry point for placing a bet (BOOT button, BOOT AGAIN,
 * spacebar). Guards: machine idle (never race an in-flight round or its
 * end-round call), affordable stake, valid rig, and a short cooldown.
 */
export const requestBoot = (context: ReturnType<typeof getContext>) => {
	if (!context.stateXstateDerived.isIdle()) return;
	if (!stateBetDerived.isBetCostAvailable()) return;
	if (!RIGS.some((rig) => rig.id === stateBet.activeBetModeKey)) return;
	const now = Date.now();
	if (now - lastBootAt < BOOT_COOLDOWN_MS) return;
	lastBootAt = now;
	context.eventEmitter.broadcast({ type: 'bet' });
};

export const playBet = async (bet: Bet) => {
	// fairness panel reference: the RGS round id for this settled bet
	// (absent in Storybook fixtures)
	stateSession.lastRoundID = bet.roundID ?? null;
	stateBet.winBookEventAmount = 0;
	await playBookEvents(bet.state);
};

/**
 * Resume (brief 5.4): the RGS returns the recorded /bet/event progress index.
 * Events before it are fast-forwarded (applied with no animation), the rest
 * replay normally.
 */
export const convertToResumableBet = (betToResume: Bet) => {
	stateGame.skipUntilIndex = Number(betToResume.event) || 0;
	return betToResume;
};

/** Apply the final state of an inactive round with no animation. */
export const settleInactiveBet = (betToResume: Bet) => {
	if (!betToResume.state?.length) return;
	stateGame.skipUntilIndex = Number.MAX_SAFE_INTEGER;
	playBookEvents(betToResume.state).finally(() => {
		stateGame.skipUntilIndex = 0;
	});
};
