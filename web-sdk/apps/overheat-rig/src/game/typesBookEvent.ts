import type { BetType } from 'rgs-requests';

import type { RigId, WinTier } from './constants';

type BookEventBoot = {
	index: number;
	type: 'boot';
	rigTier: RigId;
	targetTemp: number;
	hashrate: number;
};

type BookEventHeat = {
	index: number;
	type: 'heat';
	crashTemp: number;
};

type BookEventMeltdown = {
	index: number;
	type: 'meltdown';
	crashTemp: number;
};

type BookEventShutdown = {
	index: number;
	type: 'shutdown';
	/** payout multiplier: targetTemp for clean, up to 10x targetTemp on golden */
	bankedAt: number;
	couldHaveReached: number;
	/** absent in pre-spicy books; treat as 'clean' */
	tier?: WinTier;
};

/** partial scrap recovery on a bust: pays less than the stake */
type BookEventSalvage = {
	index: number;
	type: 'salvage';
	/** book units: payout multiplier x 100 */
	amount: number;
};

type BookEventSetTotalWin = {
	index: number;
	type: 'setTotalWin';
	amount: number;
};

type BookEventFinalWin = {
	index: number;
	type: 'finalWin';
	amount: number;
};

export type BookEvent =
	| BookEventBoot
	| BookEventHeat
	| BookEventMeltdown
	| BookEventShutdown
	| BookEventSalvage
	| BookEventSetTotalWin
	| BookEventFinalWin;

export type Bet = BetType<BookEvent>;
export type BookEventOfType<T> = Extract<BookEvent, { type: T }>;
export type BookEventContext = { bookEvents: BookEvent[] };
