/**
 * Single money formatter for the Overheat UI.
 *
 * Based on Stake Engine CurrencyMeta + DisplayBalance, with reviewer overrides:
 * - Amounts are RGS integer base units (API_AMOUNT_MULTIPLIER = 1 whole unit).
 * - Precision: format at CurrencyMeta.decimals; only rescue extra places (up to
 *   scale precision) when that would wrongly show zero for a nonzero amount.
 * - Decimal places reconciled to Stake's published display table where the
 *   pasted meta disagreed (KWD/JOD/TND/OMR/BHD → 2; ISK/XGC → 2).
 * - Unknown currency: code as suffix, 2 decimals, one-shot warn.
 *
 * MW theme garnish does NOT go through this function (see formatMW).
 */

import { API_AMOUNT_MULTIPLIER } from 'constants-shared/bet';
import { stateBet } from 'state-shared';

import { BOOK_AMOUNT_SCALE } from './constants';

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

/** Fractional digits representable by the RGS base-unit scale (1e6 → 6). */
const maxDecimalsFromScale = (scale: number): number => {
	let n = Math.abs(Math.trunc(scale));
	let decimals = 0;
	while (n > 1) {
		n = Math.floor(n / 10);
		decimals += 1;
	}
	return decimals;
};

const MAX_DECIMALS = maxDecimalsFromScale(API_AMOUNT_MULTIPLIER);

const pow10 = (n: number): bigint => 10n ** BigInt(n);

type Balance = { amount: number; currency: string };

/** True when `code` is a key in Stake's CurrencyMeta (single supported set). */
export const isSupportedCurrency = (code: string): boolean =>
	Object.prototype.hasOwnProperty.call(CurrencyMeta, code);

/**
 * Whole currency units (game state) → nearest RGS integer base units.
 * Used only at the display boundary for values that still live as whole units
 * (stake, balance); payouts should already be base integers.
 */
export const toBaseUnits = (wholeUnits: number): number =>
	Math.round(Number(wholeUnits) * API_AMOUNT_MULTIPLIER);

/**
 * Payout in RGS base units from a book amount (mult × BOOK_AMOUNT_SCALE) and
 * a wagered stake in whole currency units. Integer math only — no cent rounding.
 *
 * Book units are a multiplier scale (100 = 1x), not currency. The product is
 * always API-scale base units for the formatter.
 */
export const bookPayoutBase = (bookAmount: number, wageredWhole: number): number => {
	const wageredBase = toBaseUnits(wageredWhole);
	const book = Math.round(Number(bookAmount));
	return Number((BigInt(wageredBase) * BigInt(book)) / BigInt(BOOK_AMOUNT_SCALE));
};

/** True when a digit string is numerically zero (-0, 0, 0.00, …). */
const isZeroDigits = (digits: string): boolean => /^[-]?0(?:\.0+)?$/.test(digits);

/**
 * Round integer base units to `decimals` places and build the digit string
 * with integer/BigInt math only (no float division of the money value).
 */
const formatAtDecimals = (baseUnits: number, decimals: number): string => {
	const negative = baseUnits < 0;
	const abs = BigInt(Math.abs(Math.trunc(baseUnits)));
	const clamped = Math.max(0, Math.min(decimals, MAX_DECIMALS));
	const drop = MAX_DECIMALS - clamped;
	const divisor = pow10(drop);
	// half-up rounding in the integer domain
	const rounded = (abs + divisor / 2n) / divisor;
	const fracScale = pow10(clamped);
	const intPart = rounded / fracScale;
	const fracPart = rounded % fracScale;
	const sign = negative ? '-' : '';
	if (clamped === 0) return `${sign}${intPart.toString()}`;
	return `${sign}${intPart.toString()}.${fracPart.toString().padStart(clamped, '0')}`;
};

/**
 * Rescue-based precision:
 * 1. Format at CurrencyMeta stdDecimals (rounded).
 * 2. If that is nonzero, keep it (JPY stays whole; USD stays 2 dp).
 * 3. Only if stdDecimals shows zero but the true amount is nonzero, extend
 *    one place at a time up to MAX_DECIMALS until a significant digit appears.
 */
const formatDigitsFromBase = (baseUnits: number, stdDecimals: number): string => {
	const abs = Math.abs(Math.trunc(baseUnits));
	const standard = formatAtDecimals(baseUnits, stdDecimals);
	if (!isZeroDigits(standard) || abs === 0) return standard;

	for (let d = stdDecimals + 1; d <= MAX_DECIMALS; d++) {
		const rescued = formatAtDecimals(baseUnits, d);
		if (!isZeroDigits(rescued)) return rescued;
	}
	return standard;
};

const warnedUnknown = new Set<string>();

const resolveMeta = (currency: string): CurrencyMetaEntry => {
	const known = CurrencyMeta[currency as Currency];
	if (known) return known;
	if (currency && !warnedUnknown.has(currency)) {
		warnedUnknown.add(currency);
		console.warn(
			`[formatMoney] unknown currency "${currency}" — using code suffix, 2 decimals`,
		);
	}
	return {
		symbol: currency || '',
		decimals: 2,
		symbolAfter: true,
	};
};

/**
 * Stake DisplayBalance with rescue-based scale precision.
 * `balance.amount` is an integer RGS base-unit amount.
 */
const displayBalance = (balance: Balance): string => {
	const meta = resolveMeta(balance.currency);
	const formattedAmount = formatDigitsFromBase(balance.amount, meta.decimals);
	if (meta.symbolAfter) {
		return meta.symbol ? `${formattedAmount} ${meta.symbol}` : formattedAmount;
	}
	return `${meta.symbol}${formattedAmount}`;
};

/** Active session currency (set at authenticate). */
export const activeCurrency = (): string => stateBet.currency;

/**
 * Format a money amount for the UI.
 * `baseUnits` must be an integer RGS base-unit amount (1_000_000 = 1.00).
 */
export const formatMoney = (baseUnits: number): string =>
	displayBalance({
		amount: Math.trunc(baseUnits),
		currency: activeCurrency(),
	});

/** Alias: format a raw RGS base-unit amount. */
export const formatMoneyFromApi = (apiAmount: number): string => formatMoney(apiAmount);

/** Themed garnish: megawatts — NOT money; never uses CurrencyMeta. Takes base units. */
export const formatMW = (baseUnits: number): string => {
	const digits = formatAtDecimals(Math.trunc(baseUnits), 2);
	return `${digits} MW`;
};
