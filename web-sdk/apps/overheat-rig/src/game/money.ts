/**
 * Single money formatter for the Overheat UI.
 *
 * Based on Stake Engine CurrencyMeta + DisplayBalance, with reviewer overrides:
 * - DisplayBalance always ÷ API_AMOUNT_MULTIPLIER (RGS base → whole units).
 * - Decimal places reconciled to Stake's published display table where the
 *   pasted meta disagreed (KWD/JOD/TND/OMR/BHD → 2; ISK/XGC → 2).
 * - Unknown currency: code as suffix, 2 decimals, one-shot warn.
 *
 * MW theme garnish does NOT go through this function (see formatMW).
 */

import { API_AMOUNT_MULTIPLIER } from 'constants-shared/bet';
import { stateBet } from 'state-shared';

/** Available currency codes for Stake Engine */
type Currency =
	| 'USD'
	| 'CAD'
	| 'JPY'
	| 'EUR'
	| 'RUB'
	| 'CNY'
	| 'PHP'
	| 'INR'
	| 'IDR'
	| 'KRW'
	| 'BRL'
	| 'MXN'
	| 'DKK'
	| 'PLN'
	| 'VND'
	| 'TRY'
	| 'CLP'
	| 'ARS'
	| 'PEN'
	| 'NGN'
	| 'SAR'
	| 'ILS'
	| 'AED'
	| 'TWD'
	| 'NOK'
	| 'KWD'
	| 'JOD'
	| 'CRC'
	| 'TND'
	| 'SGD'
	| 'MYR'
	| 'OMR'
	| 'QAR'
	| 'BHD'
	| 'PKR'
	| 'EGP'
	| 'NZD'
	| 'BOB'
	| 'GHS'
	| 'KES'
	| 'MAD'
	| 'BAM'
	| 'ISK'
	| 'TZS'
	| 'UGX'
	| 'XOF'
	| 'XGC'
	| 'XSC'
	| 'XEC';

type CurrencyMetaEntry = { symbol: string; decimals: number; symbolAfter?: boolean };

/**
 * Currency metadata: symbol, default decimals, symbol placement.
 * Stake map with table overrides applied (see file header).
 */
const CurrencyMeta: Record<Currency, CurrencyMetaEntry> = {
	USD: { symbol: '$', decimals: 2 },
	CAD: { symbol: 'CA$', decimals: 2 },
	JPY: { symbol: '¥', decimals: 0 },
	EUR: { symbol: '€', decimals: 2 },
	RUB: { symbol: '₽', decimals: 2 },
	CNY: { symbol: 'CN¥', decimals: 2 },
	PHP: { symbol: '₱', decimals: 2 },
	INR: { symbol: '₹', decimals: 2 },
	IDR: { symbol: 'Rp', decimals: 0 },
	KRW: { symbol: '₩', decimals: 0 },
	BRL: { symbol: 'R$', decimals: 2 },
	MXN: { symbol: 'MX$', decimals: 2 },
	DKK: { symbol: 'KR', decimals: 2, symbolAfter: true },
	PLN: { symbol: 'zł', decimals: 2, symbolAfter: true },
	VND: { symbol: '₫', decimals: 0, symbolAfter: true },
	TRY: { symbol: '₺', decimals: 2 },
	CLP: { symbol: 'CLP', decimals: 0, symbolAfter: true },
	ARS: { symbol: 'ARS', decimals: 2, symbolAfter: true },
	PEN: { symbol: 'S/', decimals: 2, symbolAfter: true },
	NGN: { symbol: '₦', decimals: 2 },
	SAR: { symbol: 'SAR', decimals: 2, symbolAfter: true },
	ILS: { symbol: '₪', decimals: 2 },
	AED: { symbol: 'AED', decimals: 2, symbolAfter: true },
	TWD: { symbol: 'NT$', decimals: 2 },
	NOK: { symbol: 'kr', decimals: 2, symbolAfter: true },
	// table: 2 decimals (Stake sample map had 3)
	KWD: { symbol: 'KD', decimals: 2 },
	JOD: { symbol: 'JD', decimals: 2 },
	CRC: { symbol: '₡', decimals: 2 },
	TND: { symbol: 'TND', decimals: 2, symbolAfter: true },
	SGD: { symbol: 'SG$', decimals: 2 },
	MYR: { symbol: 'RM', decimals: 2 },
	OMR: { symbol: 'OMR', decimals: 2, symbolAfter: true },
	QAR: { symbol: 'QAR', decimals: 2, symbolAfter: true },
	BHD: { symbol: 'BD', decimals: 2 },
	PKR: { symbol: '₨', decimals: 2 },
	EGP: { symbol: 'ج.م', decimals: 2 },
	NZD: { symbol: 'NZ$', decimals: 2 },
	BOB: { symbol: 'Bs', decimals: 2 },
	GHS: { symbol: 'GH₵', decimals: 2 },
	KES: { symbol: 'KSh', decimals: 2 },
	MAD: { symbol: 'MAD', decimals: 2, symbolAfter: true },
	BAM: { symbol: 'KM', decimals: 2 },
	// table: kr10.00 (Stake sample map had 0)
	ISK: { symbol: 'kr', decimals: 2, symbolAfter: true },
	TZS: { symbol: 'TSh', decimals: 2 },
	UGX: { symbol: 'USh', decimals: 0 },
	XOF: { symbol: 'CFA', decimals: 0, symbolAfter: true },
	// table: 10.00 GC (Stake sample map had 0)
	XGC: { symbol: 'GC', decimals: 2 },
	XSC: { symbol: 'SC', decimals: 2 },
	XEC: { symbol: 'SC', decimals: 2 },
};

type Balance = { amount: number; currency: string };

/** True when `code` is a key in Stake's CurrencyMeta (single supported set). */
export const isSupportedCurrency = (code: string): boolean =>
	Object.prototype.hasOwnProperty.call(CurrencyMeta, code);

const warnedUnknown = new Set<string>();

/**
 * Stake DisplayBalance, with the required base-unit scale step.
 * `balance.amount` is RGS base units (1_000_000 = 1.00 whole unit).
 */
const displayBalance = (balance: Balance): string => {
	const known = CurrencyMeta[balance.currency as Currency];
	let meta: CurrencyMetaEntry;
	if (known) {
		meta = known;
	} else {
		if (balance.currency && !warnedUnknown.has(balance.currency)) {
			warnedUnknown.add(balance.currency);
			console.warn(
				`[formatMoney] unknown currency "${balance.currency}" — using code suffix, 2 decimals`,
			);
		}
		meta = {
			symbol: balance.currency || '',
			decimals: 2,
			symbolAfter: true,
		};
	}

	// RGS base → whole units (Stake DisplayBalance assumes whole units)
	const wholeUnits = balance.amount / API_AMOUNT_MULTIPLIER;
	const formattedAmount = wholeUnits.toFixed(meta.decimals);
	if (meta.symbolAfter) {
		return meta.symbol ? `${formattedAmount} ${meta.symbol}` : formattedAmount;
	}
	return `${meta.symbol}${formattedAmount}`;
};

/** Active session currency (set at authenticate). */
export const activeCurrency = (): string => stateBet.currency;

/**
 * Format a money amount for the UI (stake, balance, payouts, header, etc.).
 *
 * Game state stores whole currency units (scaled at authenticate). We convert
 * back to RGS base units here so {@link displayBalance} always applies the
 * official ÷1_000_000 step.
 */
export const formatMoney = (wholeUnits: number): string =>
	displayBalance({
		amount: wholeUnits * API_AMOUNT_MULTIPLIER,
		currency: activeCurrency(),
	});

/** Format a raw RGS base-unit amount directly. */
export const formatMoneyFromApi = (apiAmount: number): string =>
	displayBalance({ amount: apiAmount, currency: activeCurrency() });

/** Round to integer cents — shared helper for payout math display paths. */
export const toCents = (amount: number): number => Math.round(amount * 100);

/**
 * Payout for a book-event amount (payout multiplier x 100) on a wagered
 * stake, computed in integer cents so sub-cent float drift cannot leak
 * into the display.
 */
export const bookPayoutCents = (bookAmount: number, wageredAmount: number): number =>
	Math.round((bookAmount * toCents(wageredAmount)) / 100);

/** Format integer cents in the session currency. */
export const formatCents = (cents: number): string => formatMoney(cents / 100);

/** Themed garnish: megawatts — NOT money; never uses CurrencyMeta. */
export const formatMW = (amount: number): string =>
	`${(toCents(amount) / 100).toLocaleString('en-US', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	})} MW`;
