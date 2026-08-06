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
	};

	const props: Props = $props();

	let authenticated = $state(false);
	let authFailed = $state(false);

	const failAuth = (error: unknown) => {
		console.error(error);
		stateAuth.status = 'failed';
		authFailed = true;
		// Do not open a dismissible modal — auth failure is terminal.
	};

	const isPositiveNumber = (value: unknown): value is number =>
		typeof value === 'number' && Number.isFinite(value) && value > 0;

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
				jurisdiction: config.jurisdiction as typeof stateConfig.jurisdiction,
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
	};

	const authenticate = async () => {
		const authenticateData = assertAuthResponse(
			await requestAuthenticate({
				rgsUrl: stateUrlDerived.rgsUrl(),
				sessionID: stateUrlDerived.sessionID(),
				language: stateUrlDerived.lang(),
			}),
		);

		stateBet.currency = authenticateData.balance.currency;
		stateBet.balanceAmount = authenticateData.balance.amount / API_AMOUNT_MULTIPLIER;

		stateConfig.jurisdiction = authenticateData.config.jurisdiction;
		applyBetConfig(authenticateData.config);

		// starting stake is defaultBetLevel unless an active/resumable round overrides it
		stateBet.betAmount = stateConfig.defaultBetLevel;
		stateBet.wageredBetAmount = stateConfig.defaultBetLevel;

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
				stateBet.betAmount = betAmountValue;
				stateBet.wageredBetAmount = betAmountValue;
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
