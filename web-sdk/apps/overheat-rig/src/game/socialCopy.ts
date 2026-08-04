/**
 * Social-casino wording (jurisdiction.socialCasino).
 * Restricted gambling phrases swap to the approved alternatives below.
 */
import { stateConfig } from 'state-shared';

export const isSocialCasino = (): boolean => !!stateConfig.jurisdiction.socialCasino;

const pick = <T>(social: T, standard: T): T => (isSocialCasino() ? social : standard);

/** stake → play amount */
export const wordStake = (): string => pick('play amount', 'stake');

/** STAKE → PLAY AMOUNT (run topline) */
export const labelStake = (): string => pick('PLAY AMOUNT', 'STAKE');

/** cash out → collect (cash → coins; "coins out" does not read) */
export const wordCashOut = (): string => pick('collect', 'cash out');

/** CASH OUT TARGET */
export const labelCashOutTarget = (): string => pick('COLLECT TARGET', 'CASH OUT TARGET');

/** pays → wins */
export const wordPays = (): string => pick('wins', 'pays');

/** pay → win */
export const wordPay = (): string => pick('win', 'pay');

/** payout / pay out → win */
export const wordPayout = (): string => pick('win', 'payout');

/** PAYOUTS heading */
export const labelPayouts = (): string => pick('WINS', 'PAYOUTS');

/** gambling → play */
export const wordGambling = (): string => pick('play', 'gambling');

/** cost of → can be played for */
export const phraseCostOf = (): string => pick('can be played for', 'cost of');

/** "cost at current …" table header */
export const labelCostAt = (): string =>
	pick('can be played for at current', 'cost at current');

/** "every mode costs exactly" → "every mode can be played for exactly" */
export const phraseModeCosts = (): string =>
	pick('every mode can be played for exactly', 'every mode costs exactly');

/** Rig flavor lines that use restricted pay-verbs */
export const flavorForSocial = (flavor: string): string => {
	if (!isSocialCasino()) return flavor;
	return flavor.replace(/\bpays\b/g, 'wins').replace(/\bpay\b/g, 'win');
};
