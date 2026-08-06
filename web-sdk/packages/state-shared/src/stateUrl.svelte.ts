import { locales } from 'config-lingui';
import { page } from '$app/state';

export type Language = (typeof locales)[number];


export type Key =
	// keys for play (Stake Engine launch URL — official spellings)
	| 'sessionID'
	| 'rgs_url'
	| 'lang'
	| 'currency'
	| 'device'
	| 'social'
	| 'demo'
	// keys for replay / optional starting stake
	| 'replay'
	| 'amount'
	| 'game'
	| 'mode'
	| 'version'
	| 'event';

const getUrlSearchParam = (key: Key) => page.url.searchParams.get(key) as string | null;

/** Locales we ship game strings for (subset of Stake Engine lang codes). */
const SHIPPED_GAME_LANGS = ['en', 'es', 'pt', 'ja', 'zh'] as const;

/** Optional. Official launch param is `lang` (ISO 639-1). Unsupported/missing → en. */
const lang = (): Language => {
	const raw = getUrlSearchParam('lang');
	if (!raw) return 'en';
	const normalized = raw === 'br' ? 'pt' : raw;
	if ((SHIPPED_GAME_LANGS as readonly string[]).includes(normalized)) {
		return normalized as Language;
	}
	return 'en';
};

const sessionID = () => getUrlSearchParam('sessionID') || '';
const rgsUrl = () => getUrlSearchParam('rgs_url') || '';
const social = () => getUrlSearchParam('social') === 'true';

/**
 * Optional display currency from the launch URL (`currency=USD`).
 * Empty string when missing/blank — caller falls back to RGS balance.currency.
 */
const currency = () => {
	const raw = (getUrlSearchParam('currency') || '').trim().toUpperCase();
	return raw;
};

// params for replay
const replay = () => getUrlSearchParam('replay') === 'true';
/** Optional. API base units (1e6 = $1). 0 when missing/invalid. */
const amount = () => {
	const raw = getUrlSearchParam('amount');
	if (raw == null || raw === '') return 0;
	const value = Number(raw);
	return Number.isFinite(value) && value > 0 ? value : 0;
};
const game = () => getUrlSearchParam('game') || '';
const version = () => getUrlSearchParam('version') || '';
const mode = () => getUrlSearchParam('mode') || '';
const event = () => getUrlSearchParam('event') || '';

export const stateUrlDerived = {
	// states for play
	lang,
	sessionID,
	rgsUrl,
	social,
	currency,
	// states for replay / optional stake
	replay,
	amount,
	game,
	mode,
	version,
	event,
};
