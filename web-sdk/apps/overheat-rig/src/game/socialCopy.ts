/**
 * Social-casino wording (jurisdiction.socialCasino).
 * Pulls from the active locale; social markets use *_social keys.
 */
import { stateConfig } from 'state-shared';

import type { MessageKey } from '../i18n/messagesMap/en';
import { t } from './t';

export const isSocialCasino = (): boolean => !!stateConfig.jurisdiction.socialCasino;

const pick = (standard: MessageKey, social: MessageKey): string =>
	t(isSocialCasino() ? social : standard);

/** stake → play amount */
export const wordStake = (): string => pick('word_stake', 'word_stake_social');

/** STAKE → PLAY AMOUNT (run topline) */
export const labelStake = (): string => pick('label_stake', 'label_stake_social');

/** cash out → collect */
export const wordCashOut = (): string => pick('word_cash_out', 'word_cash_out_social');

/** CASH OUT TARGET */
export const labelCashOutTarget = (): string =>
	pick('label_cash_out_target', 'label_cash_out_target_social');

/** pays → wins */
export const wordPays = (): string => pick('word_pays', 'word_pays_social');

/** pay → win */
export const wordPay = (): string => pick('word_pay', 'word_pay_social');

/** payout / pay out → win */
export const wordPayout = (): string => pick('word_payout', 'word_payout_social');

/** PAYOUTS heading */
export const labelPayouts = (): string => pick('label_payouts', 'label_payouts_social');

/** gambling → play */
export const wordGambling = (): string => pick('word_gambling', 'word_gambling_social');

/** "cost at current …" table header */
export const labelCostAt = (): string => pick('label_cost_at', 'label_cost_at_social');

/** "every mode costs exactly" → social variant */
export const phraseModeCosts = (): string =>
	pick('phrase_mode_costs', 'phrase_mode_costs_social');

export const wordPayoutsPlural = (): string =>
	pick('word_payouts_plural', 'word_payouts_plural_social');

/** Rig flavor for the active locale (social eco flavor when needed). */
export const flavorForRig = (rigId: string): string => {
	if (rigId === 'eco' && isSocialCasino()) return t('flavor_eco_social');
	const key = `flavor_${rigId}` as MessageKey;
	return t(key);
};
