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

/** a checkpoint rung crossed: `amount` is the cumulative secured payout */
type BookEventBank = {
	index: number;
	type: 'bank';
	/** rung temperature (multiplier) */
	temp: number;
	/** book units: cumulative payout multiplier x 100 */
	amount: number;
};

type BookEventMeltdown = {
	index: number;
	type: 'meltdown';
	crashTemp: number;
	/** book units: payout kept from the rungs banked before the fry */
	amount: number;
};

type BookEventShutdown = {
	index: number;
	type: 'shutdown';
	/** payout multiplier: the shutdown mult reached (clean ≈ target; overdrive bands above) */
	bankedAt: number;
	couldHaveReached: number;
	tier: WinTier;
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
	| BookEventBank
	| BookEventMeltdown
	| BookEventShutdown
	| BookEventSetTotalWin
	| BookEventFinalWin;

export type Bet = BetType<BookEvent>;
export type BookEventOfType<T> = Extract<BookEvent, { type: T }>;
export type BookEventContext = { bookEvents: BookEvent[] };
