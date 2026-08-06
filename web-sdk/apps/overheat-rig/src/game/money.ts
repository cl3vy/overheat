/**
 * The single money formatter for the whole game (QA remediation Phase 4).
 *
 * Rules:
 * - every amount is rounded to integer cents exactly once, here, at render.
 * - the active currency is stateBet.currency (launch `currency` if valid,
 *   otherwise RGS balance.currency). Do not format money elsewhere.
 * - zero-decimal currencies (JPY, KRW, ...) render without ".00": the
 *   Intl currency data decides the fraction digits, we don't force them.
 */

import { stateBet, stateI18n } from 'state-shared';

// social-casino currencies with no ISO Intl entry (matches the SDK map)
const NO_LOCALISATION_CURRENCY_MAP: Record<string, string> = {
	XGC: 'GC',
	XSC: 'SC',
};

/** Round to integer cents -- the one rounding rule in the game. */
export const toCents = (amount: number): number => Math.round(amount * 100);

/**
 * Payout for a book-event amount (payout multiplier x 100) on a wagered
 * stake, computed in integer cents so sub-cent float drift cannot leak
 * into the display.
 */
export const bookPayoutCents = (bookAmount: number, wageredAmount: number): number =>
	Math.round((bookAmount * toCents(wageredAmount)) / 100);

/** Active session currency (set at authenticate). */
export const activeCurrency = (): string => stateBet.currency;

/** Format an amount in the active session currency (locale + currency aware). */
export const formatMoney = (amount: number): string => {
	const value = toCents(amount) / 100;
	const currency = activeCurrency();
	if (!currency) {
		return value.toFixed(2);
	}
	if (currency in NO_LOCALISATION_CURRENCY_MAP) {
		return `${NO_LOCALISATION_CURRENCY_MAP[currency]} ${value.toFixed(2)}`;
	}
	const opts = {
		style: 'currency' as const,
		currency,
		// narrowSymbol keeps "$1.00" instead of "USD 1.00" so the stake
		// row never jumps between a wrapping code and a symbol
		currencyDisplay: 'narrowSymbol' as const,
	};
	try {
		return stateI18n.i18n.number(value, opts);
	} catch {
		try {
			return new Intl.NumberFormat(undefined, opts).format(value);
		} catch {
			return `${currency} ${value.toFixed(2)}`;
		}
	}
};

/** Format integer cents in the session currency. */
export const formatCents = (cents: number): string => formatMoney(cents / 100);

/** Themed garnish: the same amount as megawatts, never the primary figure. */
export const formatMW = (amount: number): string =>
	`${(toCents(amount) / 100).toLocaleString('en-US', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	})} MW`;
