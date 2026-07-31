/**
 * Outcome-scaled pacing (brief 5.5). The timeline is derived from crashTemp
 * vs targetTemp read out of the book events; it never affects the payout.
 *
 * Decorrelation principle: every round follows the SAME time-at-temperature
 * law, with a hesitation stall at each checkpoint rung. A bust is the win
 * path truncated at the fry point, so the first N seconds of a dud are
 * indistinguishable from the first N seconds of a jackpot -- the reveal
 * cannot telegraph the outcome class early.
 */

export type Ease = 'linear' | 'out';

export type ClimbSegment = {
	toTemp: number;
	durationMs: number;
	ease: Ease;
	/** hold at toTemp with a nervous temp wobble (rung hesitation) */
	jitter?: boolean;
	/** the checkpoint temp this stall sits on (used for chirps/ladder) */
	milestone?: number;
};

const log2 = (x: number) => Math.log2(Math.max(x, 1));
const clamp = (x: number, lo: number, hi: number) => Math.min(Math.max(x, lo), hi);

/**
 * Cumulative time to reach climb progress p in [0,1].
 * t(p) = p^EXP means early heat is cheap and the final 10% of the climb
 * costs ~25% of the round -- classic "almost there" tension.
 */
const CLIMB_EXP = 2.6;

/** total duration of a full climb to the target: ~4s at 1.5x, ~13s at 100x */
const fullClimbMs = (targetTemp: number) => 3000 + 1500 * log2(targetTemp);

export const buildClimbPath = (options: {
	targetTemp: number;
	/** where the visible climb stops: the fry temp on busts, the target on wins */
	endTemp: number;
	/** checkpoint rung temperatures for the active rig (all below target) */
	rungTemps: number[];
	isWin: boolean;
	minimumRoundDurationMs?: number;
}): ClimbSegment[] => {
	const { targetTemp, endTemp, rungTemps, isWin, minimumRoundDurationMs = 0 } = options;

	if (!isWin && endTemp <= 1.005) {
		// fried on boot: the one honestly-instant outcome
		return [{ toTemp: endTemp, durationMs: 200, ease: 'linear' }];
	}

	const totalMs = fullClimbMs(targetTemp);
	const progressOf = (temp: number) => (temp - 1) / Math.max(targetTemp - 1, 0.0001);
	const timeAt = (p: number) => Math.pow(clamp(p, 0, 1), CLIMB_EXP) * totalMs;
	// dense ladders stall briefly, sparse ladders linger
	const stallMs = clamp(520 - rungTemps.length * 22, 170, 420);

	const segments: ClimbSegment[] = [];
	let prevTime = 0;
	let lastTemp = 1;

	// shared prefix -- identical for wins and busts up to the fry point
	for (const rung of rungTemps) {
		if (rung >= endTemp - 1e-9) break;
		const t = timeAt(progressOf(rung));
		segments.push({ toTemp: rung, durationMs: Math.max(t - prevTime, 140), ease: 'linear' });
		segments.push({
			toTemp: rung,
			durationMs: stallMs + (Math.round(rung * 100) % 90),
			ease: 'linear',
			jitter: true,
			milestone: rung,
		});
		prevTime = t;
		lastTemp = rung;
	}

	if (isWin) {
		// approach crawl into the hold point, then the tense pre-bank pause
		const nearTemp = Math.max(1 + (targetTemp - 1) * 0.955, lastTemp);
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
	} else if (progressOf(endTemp) >= 0.85) {
		// died within sight of the target: crawl agonisingly close, hold, fry
		const crawlStart = Math.max(1 + (endTemp - 1) * 0.92, lastTemp);
		segments.push({
			toTemp: crawlStart,
			durationMs: Math.max(timeAt(progressOf(crawlStart)) - prevTime, 700),
			ease: 'out',
		});
		segments.push({ toTemp: endTemp, durationMs: 1500, ease: 'out' });
		segments.push({ toTemp: endTemp, durationMs: 850, ease: 'linear', jitter: true });
	} else {
		// fry mid-stride on the shared law -- no deceleration tell
		segments.push({
			toTemp: endTemp,
			durationMs: Math.max(timeAt(progressOf(endTemp)) - prevTime, 260),
			ease: 'linear',
		});
	}

	const total = segments.reduce((sum, segment) => sum + segment.durationMs, 0);
	if (minimumRoundDurationMs > total && total > 0) {
		const scale = minimumRoundDurationMs / total;
		return segments.map((segment) => ({ ...segment, durationMs: segment.durationMs * scale }));
	}
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
