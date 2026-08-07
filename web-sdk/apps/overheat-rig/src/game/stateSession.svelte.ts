import type { RigId, WinTier } from './constants';

export type RoundRecord = {
	rigTier: RigId;
	targetTemp: number;
	/** where the silicon actually gave out (couldHaveReached on wins) */
	crashTemp: number;
	/** true when the run reached the shutdown target (any tier) */
	win: boolean;
	/** payout in RGS integer base units (for formatMoney / best-bank display) */
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

// QA 5.4 first-run hygiene: display stats are namespaced per player session
// and per currency (key parts from the launch URL), and live in
// sessionStorage so a fresh player always starts from a clean slate.
// Everything here is display-only and can never alter gameplay or payouts.
const metaKey = () => {
	let sessionPart = 'local';
	let currencyPart = 'XXX';
	try {
		const params = new URLSearchParams(globalThis.location?.search ?? '');
		sessionPart = params.get('sessionID') ?? 'local';
		currencyPart = params.get('currency') ?? 'XXX';
	} catch {
		// no location (SSR/test): keep the defaults
	}
	return `overheat.meta.v2.${sessionPart}.${currencyPart}`;
};

const loadMeta = (): MetaState => {
	const empty: MetaState = {
		bests: {},
		lifetimeRounds: 0,
		lifetimeWagered: 0,
		lifetimeReturned: 0,
		bestStreak: 0,
	};
	try {
		const raw = globalThis.sessionStorage?.getItem(metaKey());
		if (!raw) return empty;
		return { ...empty, ...JSON.parse(raw) };
	} catch {
		return empty;
	}
};

const saveMeta = (meta: MetaState) => {
	try {
		globalThis.sessionStorage?.setItem(metaKey(), JSON.stringify(meta));
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
	newBest: null as { rigTier: RigId; kind: 'mult' } | null,
	/** RGS round id of the most recent bet (fairness panel reference) */
	lastRoundID: null as number | string | null,
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
	// bestTemp is tracked silently (feeds the config peaks line) but never
	// wears the badge: a hotter zero-bank near miss is not a "best run".
	// the badge fires only on genuine banked improvement.
	if (round.crashTemp > best.bestTemp) {
		best.bestTemp = round.crashTemp;
	}
	if (round.payoutMult > 0 && round.payoutMult > best.bestMult) {
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
