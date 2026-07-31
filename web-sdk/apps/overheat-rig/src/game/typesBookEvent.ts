import type { BetType } from 'rgs-requests';

import type { RigId } from './constants';

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
	bankedAt: number;
	couldHaveReached: number;
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
	| BookEventSetTotalWin
	| BookEventFinalWin;

export type Bet = BetType<BookEvent>;
export type BookEventOfType<T> = Extract<BookEvent, { type: T }>;
export type BookEventContext = { bookEvents: BookEvent[] };
