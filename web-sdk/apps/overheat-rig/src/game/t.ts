/**
 * Game string lookup. Never renders a raw key when English exists.
 * Simple `{name}` interpolation (not full ICU).
 */
import { stateI18n } from 'state-shared';

import en, { type MessageKey } from '../i18n/messagesMap/en';

type Vars = Record<string, string | number>;

const interpolate = (template: string, vars?: Vars): string => {
	if (!vars) return template;
	return template.replace(/\{(\w+)\}/g, (match, name: string) =>
		vars[name] != null ? String(vars[name]) : match,
	);
};

export const t = (key: MessageKey, vars?: Vars): string => {
	const catalog = stateI18n.i18n.messages as Record<string, unknown> | undefined;
	const active = catalog?.[key];
	const fromActive = typeof active === 'string' ? active : undefined;
	const fallback = en[key];
	const template = fromActive && fromActive !== key ? fromActive : fallback;
	return interpolate(template, vars);
};

/** Translate if key exists in en; otherwise return the provided English fallback text. */
export const tOr = (key: string, englishFallback: string, vars?: Vars): string => {
	if (key in en) return t(key as MessageKey, vars);
	return interpolate(englishFallback, vars);
};

/** Display name for a rig API id (idle…plasma). */
export const rigName = (rigId: string): string => {
	const key = `rig_${rigId}_name` as MessageKey;
	return t(key);
};
