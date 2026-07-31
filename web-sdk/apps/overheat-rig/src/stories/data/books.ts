import { LADDERS, type RigId, type WinTier } from '../../game/constants';
import type { BookEvent } from '../../game/typesBookEvent';

export type FixtureBook = {
	id: number;
	payoutMultiplier: number;
	events: BookEvent[];
	criteria: WinTier | 'bank' | 'bust';
};

const floor2 = (x: number) => Math.floor(x * 100) / 100;

type WinOptions = { tier?: WinTier; couldHaveReached?: number };

const winBook = (id: number, rigTier: RigId, options: WinOptions = {}): FixtureBook => {
	const ladder = LADDERS[rigTier];
	const tier = options.tier ?? 'clean';
	const bankedAt = ladder.tiers.find((t) => t.tier === tier)!.payout;
	const payout = Math.round(bankedAt * 100);
	const events: BookEvent[] = [
		{ index: 0, type: 'boot', rigTier, targetTemp: ladder.target, hashrate: 420 },
		{ index: 1, type: 'heat', crashTemp: bankedAt },
	];
	ladder.rungs.forEach((rung, i) => {
		events.push({
			index: 2 + i,
			type: 'bank',
			temp: rung.temp,
			amount: Math.round(rung.bank * 100),
		});
	});
	let index = 2 + ladder.rungs.length;
	events.push({
		index: index++,
		type: 'shutdown',
		bankedAt,
		couldHaveReached: Math.max(options.couldHaveReached ?? bankedAt, bankedAt),
		tier,
	});
	events.push({ index: index++, type: 'setTotalWin', amount: payout });
	events.push({ index: index, type: 'finalWin', amount: payout });
	return { id, payoutMultiplier: payout, events, criteria: tier };
};

const bustBook = (id: number, rigTier: RigId, crashTemp: number): FixtureBook => {
	const ladder = LADDERS[rigTier];
	const crossed = ladder.rungs.filter((rung) => crashTemp >= rung.temp - 1e-9);
	const payout = crossed.length ? Math.round(crossed[crossed.length - 1].bank * 100) : 0;
	const events: BookEvent[] = [
		{ index: 0, type: 'boot', rigTier, targetTemp: ladder.target, hashrate: 420 },
		{ index: 1, type: 'heat', crashTemp },
	];
	crossed.forEach((rung, i) => {
		events.push({
			index: 2 + i,
			type: 'bank',
			temp: rung.temp,
			amount: Math.round(rung.bank * 100),
		});
	});
	let index = 2 + crossed.length;
	events.push({ index: index++, type: 'meltdown', crashTemp, amount: payout });
	events.push({ index: index++, type: 'setTotalWin', amount: payout });
	events.push({ index: index, type: 'finalWin', amount: payout });
	return { id, payoutMultiplier: payout, events, criteria: crossed.length ? 'bank' : 'bust' };
};

// fixtures anchored to the real ladders so bank events always match
const oc = LADDERS.overclock;
const furnace = LADDERS.furnace;
const plasma = LADDERS.plasma;

export const bustInstant = bustBook(1, 'standard', 1.0);
/** fried before the first checkpoint: a true zero */
export const bustFar = bustBook(2, 'overclock', floor2(Math.max(1.01, oc.rungs[0].temp - 0.02)));
/** a couple of rungs secured, still below stake */
export const bankEarly = bustBook(3, 'furnace', floor2(furnace.rungs[2].temp + 0.01));
/** deep partial: most of the ladder banked, well above stake */
export const bankDeep = bustBook(4, 'plasma', floor2(plasma.rungs[10].temp + 0.05));
/** died one notch short of the next checkpoint (rung near miss) */
export const bankNearRung = bustBook(5, 'furnace', floor2(furnace.rungs[6].temp - 0.02));
/** died within sight of the target (signature near miss) */
export const bustNearMiss = bustBook(6, 'overclock', floor2(oc.target - 0.07));
export const winEco = winBook(7, 'eco', { couldHaveReached: 2.1 });
export const winOverclock = winBook(8, 'overclock', { couldHaveReached: 8.3 });
export const winPlasma = winBook(9, 'plasma', { couldHaveReached: 233.6 });
export const winOverdrive = winBook(10, 'overclock', {
	tier: 'overdrive',
	couldHaveReached: 9.4,
});
export const winCritical = winBook(11, 'boost', { tier: 'critical', couldHaveReached: 11.2 });
export const winGolden = winBook(12, 'furnace', { tier: 'golden', couldHaveReached: 142.7 });

export const allBooks: FixtureBook[] = [
	bustInstant,
	bustFar,
	bankEarly,
	bankDeep,
	bankNearRung,
	bustNearMiss,
	winEco,
	winOverclock,
	winPlasma,
	winOverdrive,
	winCritical,
	winGolden,
];

/** hyperbolic draw inside [lo, hi): P(C >= x | interval), inverse transform */
const drawInInterval = (lo: number, hi: number) => {
	const u = Math.random();
	const x = 1 / (1 / lo - u * (1 / lo - 1 / hi));
	return Math.min(Math.max(floor2(x), lo), floor2(hi - 0.01));
};

/**
 * Draw a book from the true checkpoint-banking distribution, mirroring the
 * math generator's exact class probabilities (shipped in ladders.json).
 * Storybook only -- live play draws from the RGS weighted lookup tables, but
 * this keeps the "random" demo story honest about the odds.
 */
export const drawRealisticBook = (rigTier: RigId): FixtureBook => {
	const ladder = LADDERS[rigTier];
	let u = Math.random();

	for (const tier of ladder.tiers) {
		if (u < tier.prob) {
			const couldHaveReached = floor2(
				Math.min(tier.payout / Math.max(Math.random(), 1e-9), 5000),
			);
			return winBook(Date.now(), rigTier, { tier: tier.tier, couldHaveReached });
		}
		u -= tier.prob;
	}

	for (let i = 0; i < ladder.rungs.length; i += 1) {
		const rung = ladder.rungs[i];
		if (u < rung.prob) {
			const hi = i + 1 < ladder.rungs.length ? ladder.rungs[i + 1].temp : ladder.target;
			return bustBook(Date.now(), rigTier, drawInInterval(rung.temp, hi));
		}
		u -= rung.prob;
	}

	// bust below the first rung; some fry on boot
	const crashTemp =
		Math.random() < 0.12 ? 1.0 : drawInInterval(1.0, ladder.rungs[0].temp);
	return bustBook(Date.now(), rigTier, crashTemp);
};
