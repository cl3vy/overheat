export const stateConfig = $state({
	jurisdiction: {
		socialCasino: false,
		disabledFullscreen: false,
		disabledTurbo: false,
		disabledSuperTurbo: false,
		disabledAutoplay: false,
		disabledSlamstop: false,
		disabledSpacebar: false,
		disabledBuyFeature: false,
		displayNetPosition: false,
		displayRTP: false,
		displaySessionTimer: false,
		minimumRoundDuration: 0,
	},
	/** Display-unit bet ladder from /wallet/authenticate `betLevels` (no local defaults). */
	betAmountOptions: [] as number[],
	betMenuOptions: [] as number[],
	/** Display-unit bounds / step / default from authenticate (unset until auth). */
	minBet: Number.NaN,
	maxBet: Number.NaN,
	stepBet: Number.NaN,
	defaultBetLevel: Number.NaN,
});
