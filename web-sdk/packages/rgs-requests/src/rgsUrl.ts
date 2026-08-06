/**
 * Stake Engine launch params pass `rgs_url` as a host (optionally with path),
 * without a scheme. The fetcher builds `https://${rgsUrl}${path}`.
 */
export const assertValidRgsUrl = (rgsUrl: string): void => {
	const raw = (rgsUrl ?? '').trim();
	if (!raw) {
		throw { error: 'AUTH_RGS_URL', message: 'rgs_url missing or empty' };
	}
	// A scheme here would become https://https://... when the fetcher prefixes.
	if (/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(raw)) {
		throw { error: 'AUTH_RGS_URL', message: 'rgs_url is not a valid host URL' };
	}
	let parsed: URL;
	try {
		parsed = new URL(`https://${raw}`);
	} catch {
		throw { error: 'AUTH_RGS_URL', message: 'rgs_url is not a valid URL' };
	}
	if (!parsed.hostname) {
		throw { error: 'AUTH_RGS_URL', message: 'rgs_url is not a valid URL' };
	}
};
