/**
 * Outcome-scaled pacing (brief 5.5). The timeline is derived from crashTemp
 * vs targetTemp read out of the book events; it never affects the payout.
 *
 * Win climbs are built for suspense: fast early heat that decelerates on
 * approach (the last stretch takes disproportionately long), micro-stalls at
 * round multipliers, and a total duration that scales with the target
 * (~4s for 1.5x up to ~13s for 100x). Display-only.
 */

export type Ease = 'linear' | 'out';

export type ClimbSegment = {
	toTemp: number;
	durationMs: number;
	ease: Ease;
	/** hold at toTemp with a nervous temp wobble (milestone hesitation) */
	jitter?: boolean;
	/** the round multiplier this stall sits on (used for chirps/ladder) */
	milestone?: number;
};

const log2 = (x: number) => Math.log2(Math.max(x, 1));

/** Round multipliers where the climb hesitates for a beat. */
export const WIN_MILESTONES = [1.5, 2, 3, 5, 10, 20, 50];

/**
 * Cumulative time to reach climb progress p in [0,1].
 * t(p) = p^EXP means early heat is cheap and the final 10% of the climb
 * costs ~25% of the round — classic "almost there" tension.
 */
const CLIMB_EXP = 2.6;

/** Win: climb all the way to the shutdown temperature. */
export const buildWinClimb = (targetTemp: number): ClimbSegment[] => {
	// ~4s at 1.5x, ~7s at 5x, ~10s at 20x, ~13s at 100x
	const totalMs = 3000 + 1500 * log2(targetTemp);
	const progressOf = (temp: number) => (temp - 1) / Math.max(targetTemp - 1, 0.0001);
	const timeAt = (p: number) => Math.pow(Math.min(Math.max(p, 0), 1), CLIMB_EXP) * totalMs;

	// hold just short of the target before the final push
	const nearTemp = 1 + (targetTemp - 1) * 0.955;
	const milestones = WIN_MILESTONES.filter((m) => m > 1 && m < nearTemp);

	const segments: ClimbSegment[] = [];
	let prevTime = 0;
	for (const milestone of milestones) {
		const t = timeAt(progressOf(milestone));
		segments.push({
			toTemp: milestone,
			durationMs: Math.max(t - prevTime, 150),
			ease: 'linear',
		});
		// micro-stall: deterministic 300-500ms hesitation with temp jitter
		segments.push({
			toTemp: milestone,
			durationMs: 300 + (Math.round(milestone * 100) % 201),
			ease: 'linear',
			jitter: true,
			milestone,
		});
		prevTime = t;
	}

	// approach crawl into the hold point, then the tense pre-bank pause
	segments.push({
		toTemp: nearTemp,
		durationMs: Math.max(timeAt(progressOf(nearTemp)) - prevTime, 400),
		ease: 'out',
	});
	segments.push({
		toTemp: nearTemp,
		durationMs: 350 + 130 * log2(targetTemp),
		ease: 'linear',
		jitter: true,
	});
	// the bank push
	segments.push({ toTemp: targetTemp, durationMs: 500, ease: 'linear' });
	return segments;
};

/**
 * Overdrive: the limiter slips at the target and the temp punches past it to
 * the boosted bank point (1.5x / 3x / 10x the target). Excitement, not
 * suspense: fast surges with brief stunned holds between them.
 */
export const buildOverdriveSegments = (targetTemp: number, bankedAt: number): ClimbSegment[] => {
	const segments: ClimbSegment[] = [
		// the "shutdown... failed?" beat right at the target
		{ toTemp: targetTemp, durationMs: 450, ease: 'linear', jitter: true },
	];
	const ratio = bankedAt / targetTemp;
	const steps = ratio >= 6 ? 3 : ratio >= 2.5 ? 2 : 1;
	for (let i = 1; i <= steps; i += 1) {
		const toTemp = i === steps ? bankedAt : targetTemp * Math.pow(ratio, i / steps);
		segments.push({ toTemp, durationMs: 550 + i * 150, ease: 'out' });
		if (i < steps) {
			segments.push({ toTemp, durationMs: 260, ease: 'linear', jitter: true });
		}
	}
	return segments;
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
		{ toTemp: crashTemp, durationMs: 900, ease: 'linear', jitter: true },
	];
};

export const buildClimb = (options: {
	targetTemp: number;
	/** bust: where it fried; win: the bank point (above target on overdrive) */
	crashTemp: number;
	isWin: boolean;
	minimumRoundDurationMs?: number;
}): ClimbSegment[] => {
	const { targetTemp, crashTemp, isWin, minimumRoundDurationMs = 0 } = options;
	// overdrive surges past the target are animated separately by the heat
	// handler (buildOverdriveSegments) so the surge sting can play between them
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

/**
 * Wobble offset for jitter holds: a nervous flutter that dips slightly
 * below the held temp, scaled to the climb so it reads at any target.
 */
export const jitterOffset = (elapsedMs: number, targetTemp: number) => {
	const amplitude = Math.max(targetTemp - 1, 0.5) * 0.006;
	return -Math.abs(Math.sin(elapsedMs / 53) + 0.4 * Math.sin(elapsedMs / 17)) * amplitude;
};
