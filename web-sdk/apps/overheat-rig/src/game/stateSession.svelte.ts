import type { RigId, WinTier } from './constants';

export type RoundRecord = {
	rigTier: RigId;
	targetTemp: number;
	/** where the silicon actually gave out (couldHaveReached on wins) */
	crashTemp: number;
	win: boolean;
	payoutMW: number;
	/** win tier on wins, 'salvage' for partial scrap recovery on busts */
	tier?: WinTier | 'salvage';
};

const MAX_ROUNDS = 40;

export const stateSession = $state({
	rounds: [] as RoundRecord[],
	soundEnabled: false,
});

export const recordRound = (round: RoundRecord) => {
	stateSession.rounds.push(round);
	if (stateSession.rounds.length > MAX_ROUNDS) {
		stateSession.rounds.splice(0, stateSession.rounds.length - MAX_ROUNDS);
	}
};

export const sessionStats = {
	runs: () => stateSession.rounds.length,
	wins: () => stateSession.rounds.filter((round) => round.win).length,
	hottestRun: () =>
		stateSession.rounds.reduce((max, round) => Math.max(max, round.crashTemp), 0),
	bestBankMW: () =>
		stateSession.rounds.reduce((max, round) => Math.max(max, round.payoutMW), 0),
	/** rounds since the silicon last ran to `threshold`x or hotter */
	runsSinceHot: (threshold: number) => {
		const rounds = stateSession.rounds;
		for (let i = rounds.length - 1; i >= 0; i -= 1) {
			if (rounds[i].crashTemp >= threshold) return rounds.length - 1 - i;
		}
		return rounds.length;
	},
};
