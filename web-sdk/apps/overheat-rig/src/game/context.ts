import { setContextEventEmitter, getContextEventEmitter } from 'utils-event-emitter';
import { setContextXstate, getContextXstate } from 'utils-xstate';
import { setContextLayout, getContextLayout } from 'utils-layout';
import { setContextApp, getContextApp } from 'pixi-svelte';
import { stateMeta } from 'state-shared';

import { RIGS } from './constants';
import { eventEmitter, type EmitterEvent } from './eventEmitter';
import { stateXstate, stateXstateDerived } from './stateXstate';
import { stateLayout, stateLayoutDerived } from './stateLayout';
import { stateApp } from './stateApp';

import { stateGame } from './stateGame.svelte';
import { i18nDerived } from '../i18n/i18nDerived';

/**
 * Register the rig ladder as bet modes so the shared stateBet helpers
 * (betCostMultiplier, isBetCostAvailable, ...) resolve them. All rigs have
 * cost multiplier 1.0 -- the rig choice changes the target, not the stake.
 */
const registerRigBetModes = () => {
	for (const rig of RIGS) {
		stateMeta.betModeMeta[rig.id] = {
			mode: rig.id,
			costMultiplier: 1.0,
			type: 'default',
			parent: '',
			children: '',
			assets: { icon: '', dialogImage: '', dialogVolatility: '', volatility: '', button: '' },
			text: {
				title: rig.name,
				dialog: rig.flavor,
				button: '',
				betAmountLabel: '',
				tickerIdle: '',
				tickerSpin: '',
				bannerText: '',
			},
			maxWin: rig.targetTemp,
		};
	}
};

export const setContext = () => {
	registerRigBetModes();
	setContextEventEmitter<EmitterEvent>({ eventEmitter });
	setContextXstate({ stateXstate, stateXstateDerived });
	setContextLayout({ stateLayout, stateLayoutDerived });
	setContextApp({ stateApp });
};

export const getContext = () => ({
	...getContextEventEmitter<EmitterEvent>(),
	...getContextLayout(),
	...getContextXstate(),
	...getContextApp(),
	stateGame,
	i18nDerived,
});
