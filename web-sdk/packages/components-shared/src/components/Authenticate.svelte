<script lang="ts">
	import { onMount, type Snippet } from 'svelte';

	import { requestAuthenticate, requestReplay } from 'rgs-requests';
	import {
		stateUrlDerived,
		stateBet,
		stateConfig,
		stateAuth,
		stateUi,
	} from 'state-shared';
	import { API_AMOUNT_MULTIPLIER } from 'constants-shared/bet';

	type Props = {
		children: Snippet;
		/** Optional terminal error UI; game children are never rendered on failure */
		error?: Snippet;
		/**
		 * Optional launch `currency` gate — must match Stake CurrencyMeta keys.
		 * When omitted, the launch currency param is ignored (balance.currency wins).
		 */
		isSupportedCurrency?: (code: string) => boolean;
	};

	const props: Props = $props();

	let authenticated = $state(false);
	let authFailed = $state(false);
	let warnedUnsupportedLaunchCurrency = false;

	const failAuth = (error: unknown) => {
		console.error(error);
		stateAuth.status = 'failed';
		authFailed = true;
		// Do not open a dismissible modal — auth failure is terminal.
	};

	const isPositiveNumber = (value: unknown): value is number =>
		typeof value === 'number' && Number.isFinite(value) && value > 0;

	/** Snap a display-unit amount onto betLevels (nearest; clamp to ends if out of range). */
	const snapToBetLevels = (displayAmount: number, levels: number[]): number => {
		if (!levels.length) return displayAmount;
		if (displayAmount <= levels[0]) return levels[0];
		if (displayAmount >= levels[levels.length - 1]) return levels[levels.length - 1];
		return levels.reduce((best, level) =>
			Math.abs(level - displayAmount) < Math.abs(best - displayAmount) ? level : best,
		);
	};

	/** All five bet fields are required; missing/invalid → auth failure (no local fallback). */
	const assertBetConfig = (config: any) => {
		const { minBet, maxBet, stepBet, defaultBetLevel, betLevels } = config ?? {};

		if (!isPositiveNumber(minBet)) {
			throw { error: 'AUTH_BET_CONFIG', message: 'authenticate config.minBet missing or invalid' };
		}
		if (!isPositiveNumber(maxBet) || maxBet < minBet) {
			throw { error: 'AUTH_BET_CONFIG', message: 'authenticate config.maxBet missing or invalid' };
		}
		if (!isPositiveNumber(stepBet)) {
			throw {
				error: 'AUTH_BET_CONFIG',
				message: 'authenticate config.stepBet missing or invalid',
			};
		}
		if (typeof defaultBetLevel !== 'number' || !Number.isFinite(defaultBetLevel) || defaultBetLevel <= 0) {
			throw {
				error: 'AUTH_BET_CONFIG',
				message: 'authenticate config.defaultBetLevel missing or invalid',
			};
		}
		if (
			!Array.isArray(betLevels) ||
			betLevels.length === 0 ||
			!betLevels.every((level: unknown) => typeof level === 'number' && Number.isFinite(level) && level > 0)
		) {
			throw {
				error: 'AUTH_BET_CONFIG',
				message: 'authenticate config.betLevels missing or invalid',
			};
		}
		if (defaultBetLevel < minBet || defaultBetLevel > maxBet) {
			throw {
				error: 'AUTH_BET_CONFIG',
				message: 'authenticate config.defaultBetLevel outside minBet/maxBet',
			};
		}
		if (!betLevels.includes(defaultBetLevel)) {
			throw {
				error: 'AUTH_BET_CONFIG',
				message: 'authenticate config.defaultBetLevel not present in betLevels',
			};
		}
		for (const level of betLevels) {
			if (level < minBet || level > maxBet) {
				throw {
					error: 'AUTH_BET_CONFIG',
					message: 'authenticate config.betLevels outside minBet/maxBet',
				};
			}
		}

		return {
			minBet,
			maxBet,
			stepBet,
			defaultBetLevel,
			betLevels: betLevels as number[],
		};
	};

	/** Honor jurisdiction flags from this session's authenticate response. */
	const applyJurisdiction = (jurisdiction: Record<string, unknown>) => {
		const num = (value: unknown, fallback: number) =>
			typeof value === 'number' && Number.isFinite(value) ? value : fallback;

		stateConfig.jurisdiction = {
			socialCasino: !!jurisdiction.socialCasino,
			disabledFullscreen: !!jurisdiction.disabledFullscreen,
			disabledTurbo: !!jurisdiction.disabledTurbo,
			disabledSuperTurbo: !!jurisdiction.disabledSuperTurbo,
			disabledAutoplay: !!jurisdiction.disabledAutoplay,
			disabledSlamstop: !!jurisdiction.disabledSlamstop,
			disabledSpacebar: !!jurisdiction.disabledSpacebar,
			disabledBuyFeature: !!jurisdiction.disabledBuyFeature,
			displayNetPosition: !!jurisdiction.displayNetPosition,
			displayRTP: !!jurisdiction.displayRTP,
			displaySessionTimer: !!jurisdiction.displaySessionTimer,
			minimumRoundDuration: num(jurisdiction.minimumRoundDuration, 0),
		};
	};

	const assertAuthResponse = (authenticateData: any) => {
		if (!authenticateData || typeof authenticateData !== 'object') {
			throw { error: 'AUTH_RESPONSE', message: 'authenticate response missing' };
		}
		if (authenticateData.error) throw authenticateData;

		const statusCode = authenticateData.status?.statusCode;
		if (statusCode && statusCode !== 'SUCCESS') throw authenticateData;

		const balance = authenticateData.balance;
		if (
			!balance ||
			typeof balance.amount !== 'number' ||
			typeof balance.currency !== 'string' ||
			!balance.currency
		) {
			throw {
				error: 'AUTH_RESPONSE',
				message: 'authenticate response missing balance',
			};
		}

		const config = authenticateData.config;
		if (!config || !config.jurisdiction || typeof config.jurisdiction !== 'object') {
			throw {
				error: 'AUTH_RESPONSE',
				message: 'authenticate response missing config',
			};
		}

		const betConfig = assertBetConfig(config);

		return {
			balance: balance as { amount: number; currency: string },
			config: {
				...betConfig,
				jurisdiction: config.jurisdiction as Record<string, unknown>,
			},
			round: authenticateData.round as any,
		};
	};

	const applyBetConfig = (betConfig: {
		minBet: number;
		maxBet: number;
		stepBet: number;
		defaultBetLevel: number;
		betLevels: number[];
	}) => {
		const toDisplay = (amount: number) => amount / API_AMOUNT_MULTIPLIER;
		const levels = betConfig.betLevels.map(toDisplay);
		stateConfig.minBet = toDisplay(betConfig.minBet);
		stateConfig.maxBet = toDisplay(betConfig.maxBet);
		stateConfig.stepBet = toDisplay(betConfig.stepBet);
		stateConfig.defaultBetLevel = toDisplay(betConfig.defaultBetLevel);
		stateConfig.betAmountOptions = levels;
		// full ladder — no hardcoded "most used" subset
		stateConfig.betMenuOptions = levels;
		return levels;
	};

	const authenticate = async () => {
		const authenticateData = assertAuthResponse(
			await requestAuthenticate({
				rgsUrl: stateUrlDerived.rgsUrl(),
				sessionID: stateUrlDerived.sessionID(),
				language: stateUrlDerived.lang(),
			}),
		);

		// Currency: optional launch `currency` if in CurrencyMeta, else RGS balance.currency.
		// Unsupported launch codes are ignored (never fail auth); formatter fallback is separate.
		const launchCurrency = stateUrlDerived.currency();
		const launchSupported =
			Boolean(launchCurrency) &&
			typeof props.isSupportedCurrency === 'function' &&
			props.isSupportedCurrency(launchCurrency);
		if (launchCurrency && !launchSupported && !warnedUnsupportedLaunchCurrency) {
			warnedUnsupportedLaunchCurrency = true;
			console.warn(
				`[currency] unsupported launch currency "${launchCurrency}" — using balance.currency`,
			);
		}
		stateBet.currency = launchSupported
			? launchCurrency
			: authenticateData.balance.currency;

		stateBet.balanceAmount = authenticateData.balance.amount / API_AMOUNT_MULTIPLIER;

		applyJurisdiction(authenticateData.config.jurisdiction);
		const levels = applyBetConfig(authenticateData.config);

		// jurisdiction may forbid turbo for this market
		if (stateConfig.jurisdiction.disabledTurbo) {
			stateBet.isTurbo = false;
		}

		// Starting stake: optional launch `amount` snapped to betLevels, else defaultBetLevel
		const launchAmountApi = stateUrlDerived.amount();
		const startStake =
			launchAmountApi > 0
				? snapToBetLevels(launchAmountApi / API_AMOUNT_MULTIPLIER, levels)
				: stateConfig.defaultBetLevel;
		stateBet.betAmount = startStake;
		stateBet.wageredBetAmount = startStake;

		if (authenticateData.round) {
			if (authenticateData.round?.state) {
				// @ts-ignore
				stateBet.betToResume = authenticateData.round;
			}

			if (authenticateData.round?.amount) {
				const betAmountValue =
					authenticateData.round.amount > 0
						? authenticateData.round.amount / API_AMOUNT_MULTIPLIER
						: 0;
				// resume amount must stay on the ladder
				const snapped = snapToBetLevels(betAmountValue, levels);
				stateBet.betAmount = snapped;
				stateBet.wageredBetAmount = snapped;
			}

			if (authenticateData.round?.mode) {
				stateBet.activeBetModeKey = authenticateData.round.mode;
			}
		}
	};

	const handleReplay = async () => {
		stateBet.betAmount = stateUrlDerived.amount() / API_AMOUNT_MULTIPLIER || 0;
		stateBet.wageredBetAmount = stateUrlDerived.amount() / API_AMOUNT_MULTIPLIER || 0;
		stateBet.activeBetModeKey = stateUrlDerived.mode();

		// replay skips /wallet/authenticate — still need a currency for formatMoney
		const launchCurrency = stateUrlDerived.currency();
		if (launchCurrency) stateBet.currency = launchCurrency;

		const data = await requestReplay({
			rgsUrl: stateUrlDerived.rgsUrl(),
			game: stateUrlDerived.game(),
			mode: stateUrlDerived.mode(),
			version: stateUrlDerived.version(),
			event: stateUrlDerived.event(),
		});

		if (data) {
			// @ts-ignore
			stateBet.betToResume = {
				...data,
				event: '0',
				active: true,
				mode: stateUrlDerived.mode(),
				// keep base stake on the round so the summary can read it
				amount: stateUrlDerived.amount() || (data as { amount?: number }).amount,
			};
		}
	};

	onMount(async () => {
		try {
			if (stateUrlDerived.replay()) {
				stateUi.config.mode = 'replay';
				await handleReplay();
			} else {
				stateUi.config.mode = 'default';
				await authenticate();
			}
			stateAuth.status = 'ok';
			authenticated = true;
		} catch (error) {
			failAuth(error);
		}
	});
</script>

{#if authFailed}
	{#if props.error}
		{@render props.error()}
	{:else}
		<div role="alert">Authentication failed. Cannot start game.</div>
	{/if}
{:else if authenticated}
	{@render props.children()}
{/if}
