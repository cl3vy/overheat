/**
 * Outcome-scaled pacing (brief 5.5). The timeline is derived from crashTemp
 * vs targetTemp read out of the book events; it never affects the payout.
 */

export type Ease = 'linear' | 'out';

export type ClimbSegment = {
	toTemp: number;
	durationMs: number;
	ease: Ease;
};

const log2 = (x: number) => Math.log2(Math.max(x, 1));

/** Win: climb all the way to the shutdown temperature. */
export const buildWinClimb = (targetTemp: number): ClimbSegment[] => {
	const totalMs = 1100 + 850 * log2(targetTemp);
	if (targetTemp < 5) {
		return [{ toTemp: targetTemp, durationMs: totalMs, ease: 'linear' }];
	}
	// hotter rigs earn a longer, tenser crawl with a hold before the bank
	const nearTemp = 1 + (targetTemp - 1) * 0.955;
	return [
		{ toTemp: nearTemp, durationMs: totalMs, ease: 'out' },
		{ toTemp: nearTemp, durationMs: 350 + 130 * log2(targetTemp), ease: 'linear' },
		{ toTemp: targetTemp, durationMs: 500, ease: 'linear' },
	];
};

/** Bust: fry fast when far below target, milk the near miss. */
export const buildBustClimb = (targetTemp: number, crashTemp: number): ClimbSegment[] => {
	if (crashTemp <= 1.005) {
		// fried on boot
		return [{ toTemp: crashTemp, durationMs: 200, ease: 'linear' }];
	}

	const progress = Math.min((crashTemp - 1) / (targetTemp - 1), 1);

	if (progress < 0.5) {
		return [{ toTemp: crashTemp, durationMs: 500 + 900 * progress, ease: 'linear' }];
	}

	if (progress < 0.85) {
		const durationMs = 1300 + 1300 * ((progress - 0.5) / 0.35);
		return [{ toTemp: crashTemp, durationMs, ease: 'out' }];
	}

	// near miss: climb, crawl agonisingly close to the target, hold, fry
	const crawlStart = 1 + (crashTemp - 1) * 0.92;
	return [
		{ toTemp: crawlStart, durationMs: 2000, ease: 'out' },
		{ toTemp: crashTemp, durationMs: 1700, ease: 'out' },
		{ toTemp: crashTemp, durationMs: 900, ease: 'linear' },
	];
};

export const buildClimb = (options: {
	targetTemp: number;
	crashTemp: number;
	isWin: boolean;
	minimumRoundDurationMs?: number;
}): ClimbSegment[] => {
	const { targetTemp, crashTemp, isWin, minimumRoundDurationMs = 0 } = options;
	const segments = isWin ? buildWinClimb(targetTemp) : buildBustClimb(targetTemp, crashTemp);

	const totalMs = segments.reduce((sum, segment) => sum + segment.durationMs, 0);
	if (minimumRoundDurationMs > totalMs && totalMs > 0) {
		const scale = minimumRoundDurationMs / totalMs;
		return segments.map((segment) => ({
			...segment,
			durationMs: segment.durationMs * scale,
		}));
	}
	return segments;
};

export const applyEase = (t: number, ease: Ease) => {
	if (ease === 'out') return 1 - (1 - t) * (1 - t);
	return t;
};
