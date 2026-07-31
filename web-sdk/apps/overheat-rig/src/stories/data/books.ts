import type { BookEvent } from '../../game/typesBookEvent';

export type FixtureBook = {
	id: number;
	payoutMultiplier: number;
	events: BookEvent[];
	criteria: 'win' | 'bust';
};

const book = (
	id: number,
	rigTier: BookEvent extends { rigTier: infer R } ? R : any,
	targetTemp: number,
	options: { crashTemp?: number; couldHaveReached?: number },
): FixtureBook => {
	const isWin = options.crashTemp === undefined;
	const payout = isWin ? Math.round(targetTemp * 100) : 0;
	const events: BookEvent[] = [
		{ index: 0, type: 'boot', rigTier, targetTemp, hashrate: 420 },
		{ index: 1, type: 'heat', crashTemp: isWin ? targetTemp : options.crashTemp! },
		isWin
			? {
					index: 2,
					type: 'shutdown',
					bankedAt: targetTemp,
					couldHaveReached: options.couldHaveReached ?? targetTemp,
				}
			: { index: 2, type: 'meltdown', crashTemp: options.crashTemp! },
		{ index: 3, type: 'setTotalWin', amount: payout },
		{ index: 4, type: 'finalWin', amount: payout },
	];
	return { id, payoutMultiplier: payout, events, criteria: isWin ? 'win' : 'bust' };
};

export const bustInstant = book(1, 'standard', 2, { crashTemp: 1.0 });
export const bustFar = book(2, 'overclock', 5, { crashTemp: 1.42 });
export const bustMid = book(3, 'furnace', 10, { crashTemp: 6.35 });
export const bustNearMiss = book(4, 'overclock', 5, { crashTemp: 4.87 });
export const winEco = book(5, 'eco', 1.5, { couldHaveReached: 2.1 });
export const winOverclock = book(6, 'overclock', 5, { couldHaveReached: 8.3 });
export const winPlasma = book(7, 'plasma', 100, { couldHaveReached: 233.6 });

export const allBooks: FixtureBook[] = [
	bustInstant,
	bustFar,
	bustMid,
	bustNearMiss,
	winEco,
	winOverclock,
	winPlasma,
];

const floor2 = (x: number) => Math.floor(x * 100) / 100;

/**
 * Draw a book from the true crash distribution, mirroring the math
 * generator: P(C >= x) = 0.97/x with 3% instant-bust mass at 1.00.
 * Storybook only -- live play draws from the RGS weighted lookup tables,
 * but this keeps the "random" demo story honest about the odds.
 */
export const drawRealisticBook = (rigTier: string, targetTemp: number): FixtureBook => {
	const crash =
		Math.random() >= 0.97 ? 1.0 : Math.min(1 / Math.max(Math.random(), 1e-9), 5000);
	if (crash >= targetTemp) {
		return book(Date.now(), rigTier as never, targetTemp, {
			couldHaveReached: Math.max(targetTemp, floor2(crash)),
		});
	}
	const crashDisplay = Math.max(1.0, Math.min(floor2(crash), floor2(targetTemp - 0.01)));
	return book(Date.now(), rigTier as never, targetTemp, { crashTemp: crashDisplay });
};
