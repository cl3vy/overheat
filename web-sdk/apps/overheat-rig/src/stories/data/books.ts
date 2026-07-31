import {
	RTP,
	SALVAGE_PAYOUT,
	SALVAGE_PROB,
	WIN_TIERS,
	type RigId,
	type WinTier,
} from '../../game/constants';
import type { BookEvent } from '../../game/typesBookEvent';

export type FixtureBook = {
	id: number;
	payoutMultiplier: number;
	events: BookEvent[];
	criteria: WinTier | 'salvage' | 'bust';
};

type WinOptions = { tier?: WinTier; couldHaveReached?: number };
type BustOptions = { crashTemp: number; salvage?: boolean };

const winBook = (id: number, rigTier: RigId, targetTemp: number, options: WinOptions = {}): FixtureBook => {
	const tier = options.tier ?? 'clean';
	const mult = WIN_TIERS.find((t) => t.tier === tier)!.mult;
	const bankedAt = Math.round(targetTemp * mult * 100) / 100;
	const payout = Math.round(bankedAt * 100);
	const events: BookEvent[] = [
		{ index: 0, type: 'boot', rigTier, targetTemp, hashrate: 420 },
		{ index: 1, type: 'heat', crashTemp: bankedAt },
		{
			index: 2,
			type: 'shutdown',
			bankedAt,
			couldHaveReached: Math.max(options.couldHaveReached ?? bankedAt, bankedAt),
			tier,
		},
		{ index: 3, type: 'setTotalWin', amount: payout },
		{ index: 4, type: 'finalWin', amount: payout },
	];
	return { id, payoutMultiplier: payout, events, criteria: tier };
};

const bustBook = (id: number, rigTier: RigId, targetTemp: number, options: BustOptions): FixtureBook => {
	const payout = options.salvage ? Math.round(SALVAGE_PAYOUT * 100) : 0;
	const events: BookEvent[] = [
		{ index: 0, type: 'boot', rigTier, targetTemp, hashrate: 420 },
		{ index: 1, type: 'heat', crashTemp: options.crashTemp },
		{ index: 2, type: 'meltdown', crashTemp: options.crashTemp },
	];
	let index = 3;
	if (options.salvage) {
		events.push({ index: index++, type: 'salvage', amount: payout });
	}
	events.push({ index: index++, type: 'setTotalWin', amount: payout });
	events.push({ index: index, type: 'finalWin', amount: payout });
	return { id, payoutMultiplier: payout, events, criteria: options.salvage ? 'salvage' : 'bust' };
};

export const bustInstant = bustBook(1, 'standard', 2, { crashTemp: 1.0 });
export const bustFar = bustBook(2, 'overclock', 5, { crashTemp: 1.42 });
export const bustMid = bustBook(3, 'furnace', 10, { crashTemp: 6.35 });
export const bustNearMiss = bustBook(4, 'overclock', 5, { crashTemp: 4.87 });
export const bustSalvage = bustBook(8, 'overclock', 5, { crashTemp: 3.21, salvage: true });
export const winEco = winBook(5, 'eco', 1.5, { couldHaveReached: 2.1 });
export const winOverclock = winBook(6, 'overclock', 5, { couldHaveReached: 8.3 });
export const winPlasma = winBook(7, 'plasma', 100, { couldHaveReached: 233.6 });
export const winOverdrive = winBook(9, 'overclock', 5, {
	tier: 'overdrive',
	couldHaveReached: 9.4,
});
export const winCritical = winBook(10, 'boost', 3, { tier: 'critical', couldHaveReached: 11.2 });
export const winGolden = winBook(11, 'furnace', 10, { tier: 'golden', couldHaveReached: 142.7 });

export const allBooks: FixtureBook[] = [
	bustInstant,
	bustFar,
	bustMid,
	bustNearMiss,
	bustSalvage,
	winEco,
	winOverclock,
	winPlasma,
	winOverdrive,
	winCritical,
	winGolden,
];

const floor2 = (x: number) => Math.floor(x * 100) / 100;

/**
 * Draw a book from the true spicy distribution, mirroring the math generator:
 * win tiers pay mult x target with probability rtpShare x RTP / payout,
 * salvage pays 0.4x on ~9.7% of spins, the rest bust. Storybook only --
 * live play draws from the RGS weighted lookup tables, but this keeps the
 * "random" demo story honest about the odds.
 */
export const drawRealisticBook = (rigTier: string, targetTemp: number): FixtureBook => {
	let u = Math.random();
	for (const { tier, mult, rtpShare } of WIN_TIERS) {
		const p = (rtpShare * RTP) / (mult * targetTemp);
		if (u < p) {
			// post-mortem tease: P(X >= x | X >= banked) = banked / x
			const banked = targetTemp * mult;
			const couldHaveReached = floor2(
				Math.min(banked / Math.max(Math.random(), 1e-9), 5000),
			);
			return winBook(Date.now(), rigTier as RigId, targetTemp, { tier, couldHaveReached });
		}
		u -= p;
	}
	const salvage = u < SALVAGE_PROB;
	// bust crash temp: P(C = 1) = 1 - RTP, else P(C >= x) = RTP / x, capped below target
	const raw = Math.random() >= RTP ? 1.0 : Math.min(1 / Math.max(Math.random(), 1e-9), 5000);
	const crashTemp = Math.max(1.0, Math.min(floor2(raw), floor2(targetTemp - 0.01)));
	return bustBook(Date.now(), rigTier as RigId, targetTemp, { crashTemp, salvage });
};
