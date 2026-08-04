import type { RigId, WinTier } from './constants';
import { MAX_LOG_LINES } from './constants';
import type { Phase, LogLine, LogTone } from './types';

export const stateGame = $state({
	phase: 'idle' as Phase,
	rigTier: 'standard' as RigId,
	targetTemp: 2,
	hashrate: 0,
	currentTemp: 1,
	/** revealed fry temperature on a bust */
	crashTemp: 0,
	/** post-win tease: the temperature the rig could have survived to */
	couldHaveReached: 0,
	/** win tier when banked ('clean' | 'overdrive' | 'critical' | 'golden') */
	winTier: null as WinTier | null,
	/** cumulative payout secured by crossed checkpoint rungs (x stake) */
	securedMult: 0,
	/** number of checkpoint rungs crossed so far this round */
	rungsCrossed: 0,
	logs: [] as LogLine[],
	/** resume fast-forward: book events with index < skipUntilIndex apply instantly */
	skipUntilIndex: 0,
	/** brief power-up ceremony between config and reveal (visual feel P4) */
	poweringUp: false,
});

export const pushLog = (text: string, tone: LogTone = 'normal') => {
	stateGame.logs.push({ text, tone });
	if (stateGame.logs.length > MAX_LOG_LINES) {
		stateGame.logs.splice(0, stateGame.logs.length - MAX_LOG_LINES);
	}
};

export const resetRound = () => {
	stateGame.phase = 'idle';
	stateGame.currentTemp = 1;
	stateGame.crashTemp = 0;
	stateGame.couldHaveReached = 0;
	stateGame.winTier = null;
	stateGame.securedMult = 0;
	stateGame.rungsCrossed = 0;
	stateGame.logs = [];
	stateGame.skipUntilIndex = 0;
	stateGame.hashrate = 0;
	stateGame.poweringUp = false;
};
