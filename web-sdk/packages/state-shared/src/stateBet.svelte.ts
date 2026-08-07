import type { BaseBet } from 'utils-bet';
import { stateConfig } from './stateConfig.svelte';
import { stateMeta } from './stateMeta.svelte';

export type Currency = string;
export type BetToResume = BaseBet | null;
export type BetModeKey = string;

export const stateBet = $state({
	currency: '' as Currency,
	balanceAmount: 0,
	// display units; set to authenticate defaultBetLevel (or resume amount) before play
	betAmount: 0,
	wageredBetAmount: 0,
	betToResume: null as BetToResume,
	activeBetModeKey: 'BASE' as BetModeKey,
	winBookEventAmount: 0,
	autoSpinsLoss: 0,
	autoSpinsCounter: 0,
	autoSpinsLossLimitAmount: Infinity,
	autoSpinsSingleWinLimitAmount: Infinity,
	isSpaceHold: false,
	isTurbo: false,
});

/** Largest authenticate bet level that is still ≤ cap (keeps stakes on the RGS ladder). */
const largestLevelAtMost = (cap: number) => {
	const levels = stateConfig.betAmountOptions;
	if (!levels.length) return null;
	let best: number | null = null;
	for (const level of levels) {
		if (level <= cap + 1e-9) best = level;
	}
	return best;
};

const correctBetAmount = (value: number) => {
	if (value <= 0) return 0;
	const costMultiplier = betCostMultiplier();
	if (costMultiplier === 0) return 0;
	const affordable = stateBet.balanceAmount / costMultiplier;
	const capped = value > affordable ? affordable : value;

	// Prefer an authenticate betLevel so balance clamping never leaves an
	// off-ladder / off-step stake the RGS would reject.
	const onLadder = largestLevelAtMost(capped);
	if (onLadder != null) return onLadder;

	// No ladder yet (pre-auth): still respect min/max/step when present.
	const { minBet, maxBet, stepBet } = stateConfig;
	if (
		Number.isFinite(minBet) &&
		Number.isFinite(maxBet) &&
		Number.isFinite(stepBet) &&
		stepBet > 0
	) {
		const hi = Math.min(maxBet, capped);
		if (hi < minBet) return minBet;
		const steps = Math.floor((hi - minBet) / stepBet + 1e-9);
		return minBet + steps * stepBet;
	}

	return capped;
};

const setBetAmount = (value: number) => {
	stateBet.betAmount = correctBetAmount(value);
};

const updateBetAmount = (update: (value: number) => number) => {
	stateBet.betAmount = correctBetAmount(update(stateBet.betAmount));
};

let isTurboLocked = false;

const updateIsTurbo = (value: boolean, options: { persistent: boolean }) => {
	const { persistent } = options;

	if (!persistent && isTurboLocked) return;
	if (persistent) isTurboLocked = value;

	stateBet.isTurbo = value;
};

const activeBetMode = () => stateMeta.betModeMeta?.[stateBet.activeBetModeKey.toUpperCase()]
	?? stateMeta.betModeMeta?.[stateBet.activeBetModeKey.toLowerCase()]
	?? null;
const isContinuousBet = () => stateBet.autoSpinsCounter > 1 || stateBet.isSpaceHold;
const timeScale = () => (stateBet.isTurbo ? 2 : 1);
const betCostMultiplier = () =>
	stateBetDerived.activeBetMode().type === 'activate'
		? stateBetDerived.activeBetMode().costMultiplier
		: 1;
const betCost = () => stateBet.betAmount * betCostMultiplier();
const isBetCostAvailable = () => betCost() > 0 && betCost() <= stateBet.balanceAmount;
const hasAutoBetCounter = () => stateBet.autoSpinsCounter !== 0;

export const stateBetDerived = {
	setBetAmount,
	updateBetAmount,
	updateIsTurbo,
	activeBetMode,
	isContinuousBet,
	timeScale,
	betCost,
	isBetCostAvailable,
	hasAutoBetCounter,
};
