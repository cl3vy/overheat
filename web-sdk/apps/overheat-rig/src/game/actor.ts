import { stateBet } from 'state-shared';
import { createPrimaryMachines, createIntermediateMachines, createGameActor } from 'utils-xstate';

import { RIG_MAP, type RigId } from './constants';
import type { Bet } from './typesBookEvent';
import { playBet, convertToResumableBet, settleInactiveBet } from './utils';
import { pushLog, resetRound, stateGame } from './stateGame.svelte';
import { t } from './t';

const primaryMachines = createPrimaryMachines<Bet>({
	onResumeGameActive: (betToResume) => convertToResumableBet(betToResume),
	onResumeGameInactive: (betToResume) => settleInactiveBet(betToResume),
	onNewGameStart: async () => {
		stateBet.winBookEventAmount = 0;
		resetRound();
		// seed the run screen from the CURRENT selection before the play
		// response arrives, so the boot frame can never show the previous
		// round's rig, stake or target (QA 5.1: stale first frame)
		const rig = RIG_MAP[stateBet.activeBetModeKey as RigId];
		if (rig) {
			stateGame.rigTier = rig.id;
			stateGame.targetTemp = rig.targetTemp;
		}
		stateGame.phase = 'booting';
		stateGame.poweringUp = true;
		pushLog(t('log_power_contacting'), 'dim');
		// brief power-up ceremony (visual feel P4); turbo shortens, never skips
		const holdMs = stateBet.isTurbo ? 160 : 480;
		await new Promise((resolve) => setTimeout(resolve, holdMs));
		stateGame.poweringUp = false;
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
