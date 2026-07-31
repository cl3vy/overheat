import type { RigId, WinTier } from './constants';

export type RoundRecord = {
	rigTier: RigId;
	targetTemp: number;
	/** where the silicon actually gave out (couldHaveReached on wins) */
	crashTemp: number;
	/** true when the run reached the shutdown target (any tier) */
	win: boolean;
	payoutMW: number;
	/** payout as a multiple of the stake (0 bust, <1 partial, >=1 profit) */
	payoutMult: number;
	/** win tier when the target was reached */
	tier?: WinTier;
};

const MAX_ROUNDS = 40;

// ------------------------------------------------------------- meta layer
// Cosmetic persistence only (localStorage): personal bests, streaks and
// lifetime stats give losing rounds something to count toward. No effect on
// odds or payouts.

export type RigBest = {
	/** hottest temperature ever survived-to or fried-at on this rig */
	bestTemp: number;
	/** best payout multiple ever landed on this rig */
	bestMult: number;
};

export type MetaState = {
	bests: Partial<Record<RigId, RigBest>>;
	lifetimeRounds: number;
	lifetimeWagered: number;
	lifetimeReturned: number;
	/** longest run of consecutive rounds that secured at least one checkpoint */
	bestStreak: number;
};

const META_KEY = 'overheat.meta.v1';

const loadMeta = (): MetaState => {
	const empty: MetaState = {
		bests: {},
		lifetimeRounds: 0,
		lifetimeWagered: 0,
		lifetimeReturned: 0,
		bestStreak: 0,
	};
	try {
		const raw = globalThis.localStorage?.getItem(META_KEY);
		if (!raw) return empty;
		return { ...empty, ...JSON.parse(raw) };
	} catch {
		return empty;
	}
};

const saveMeta = (meta: MetaState) => {
	try {
		globalThis.localStorage?.setItem(META_KEY, JSON.stringify(meta));
	} catch {
		// storage unavailable (private mode / iframe policy): stay in-memory
	}
};

export const stateSession = $state({
	rounds: [] as RoundRecord[],
	soundEnabled: false,
	/** consecutive rounds that secured at least one checkpoint */
	heatStreak: 0,
	/** set for one round when a personal best was just broken */
	newBest: null as { rigTier: RigId; kind: 'temp' | 'mult' } | null,
	/** RGS round id of the most recent bet (fairness panel reference) */
	lastRoundID: null as number | null,
	meta: loadMeta(),
});

export const recordRound = (round: RoundRecord) => {
	stateSession.rounds.push(round);
	if (stateSession.rounds.length > MAX_ROUNDS) {
		stateSession.rounds.splice(0, stateSession.rounds.length - MAX_ROUNDS);
	}

	// heat streak: any secured payout keeps the streak alive
	stateSession.heatStreak = round.payoutMult > 0 ? stateSession.heatStreak + 1 : 0;

	// lifetime meta + personal bests
	const meta = stateSession.meta;
	meta.lifetimeRounds += 1;
	meta.lifetimeWagered += 1;
	meta.lifetimeReturned += round.payoutMult;
	meta.bestStreak = Math.max(meta.bestStreak, stateSession.heatStreak);

	const best = meta.bests[round.rigTier] ?? { bestTemp: 0, bestMult: 0 };
	stateSession.newBest = null;
	if (round.crashTemp > best.bestTemp) {
		best.bestTemp = round.crashTemp;
		stateSession.newBest = { rigTier: round.rigTier, kind: 'temp' };
	}
	if (round.payoutMult > best.bestMult) {
		best.bestMult = round.payoutMult;
		stateSession.newBest = { rigTier: round.rigTier, kind: 'mult' };
	}
	meta.bests[round.rigTier] = best;
	saveMeta(meta);
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
	bestFor: (rigTier: RigId): RigBest =>
		stateSession.meta.bests[rigTier] ?? { bestTemp: 0, bestMult: 0 },
};
