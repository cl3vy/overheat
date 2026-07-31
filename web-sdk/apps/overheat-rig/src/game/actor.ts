import { stateBet } from 'state-shared';
import { createPrimaryMachines, createIntermediateMachines, createGameActor } from 'utils-xstate';

import type { Bet } from './typesBookEvent';
import { playBet, convertToResumableBet, settleInactiveBet } from './utils';
import { resetRound, stateGame } from './stateGame.svelte';

const primaryMachines = createPrimaryMachines<Bet>({
	onResumeGameActive: (betToResume) => convertToResumableBet(betToResume),
	onResumeGameInactive: (betToResume) => settleInactiveBet(betToResume),
	onNewGameStart: async () => {
		stateBet.winBookEventAmount = 0;
		resetRound();
		stateGame.phase = 'booting';
	},
	onNewGameError: () => {
		resetRound();
	},
	onPlayGame: async (bet) => await playBet(bet),
	// Treat every active round as "bonus" so the machine calls
	// /wallet/end-round AFTER the reveal (brief 5.4: the win banks at the
	// visual shutdown moment and a mid-animation disconnect stays resumable).
	checkIsBonusGame: () => true,
});

const intermediateMachines = createIntermediateMachines(primaryMachines);

export const gameActor = createGameActor(intermediateMachines);
