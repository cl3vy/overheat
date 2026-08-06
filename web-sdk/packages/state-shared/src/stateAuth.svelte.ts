/**
 * Terminal authentication gate for live RGS launches.
 * Once `failed`, gameplay must not start (no retry into a playable state).
 */
export const stateAuth = $state({
	/** pending until authenticate resolves; ok unlocks the game; failed is terminal */
	status: 'pending' as 'pending' | 'ok' | 'failed',
});

export const stateAuthDerived = {
	isReady: () => stateAuth.status === 'ok',
	isFailed: () => stateAuth.status === 'failed',
};
