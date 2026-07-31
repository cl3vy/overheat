import { rgsFetcher } from 'rgs-fetcher';
import { stateBet, stateUrlDerived } from 'state-shared';
import { API_AMOUNT_MULTIPLIER } from 'constants-shared/bet';

/** Refresh the wallet balance between rounds (brief section 8, nice to have). */
export const refreshBalance = async () => {
	const rgsUrl = stateUrlDerived.rgsUrl();
	if (!rgsUrl) return;

	try {
		const data = await rgsFetcher.post({
			rgsUrl,
			url: '/wallet/balance',
			variables: { sessionID: stateUrlDerived.sessionID() },
		});
		if (data?.balance?.amount !== undefined) {
			stateBet.balanceAmount = data.balance.amount / API_AMOUNT_MULTIPLIER;
		}
	} catch (error) {
		console.error('balance refresh failed', error);
	}
};
