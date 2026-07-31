import { stateBet } from 'state-shared';
import { createPlayBookUtils } from 'utils-book';

import { bookEventHandlerMap } from './bookEventHandlerMap';
import { stateGame } from './stateGame.svelte';
import type { Bet } from './typesBookEvent';

export const { playBookEvent, playBookEvents } = createPlayBookUtils({ bookEventHandlerMap });

export const playBet = async (bet: Bet) => {
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
