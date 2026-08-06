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
	import { API_AMOUNT_MULTIPLIER, MOST_USED_BET_INDEXES } from 'constants-shared/bet';

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
		if (
			!config ||
			!Array.isArray(config.betLevels) ||
			config.betLevels.length === 0 ||
			!config.jurisdiction ||
			typeof config.jurisdiction !== 'object'
		) {
			throw {
				error: 'AUTH_RESPONSE',
				message: 'authenticate response missing config',
			};
		}

		return authenticateData as {
			balance: { amount: number; currency: string };
			config: {
				betLevels: number[];
				minBet?: number;
				maxBet?: number;
				stepBet?: number;
				jurisdiction: typeof stateConfig.jurisdiction;
			};
			round?: any;
		};
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
		stateConfig.betAmountOptions = authenticateData.config.betLevels.map(
			(level) => level / API_AMOUNT_MULTIPLIER,
		);
		if (authenticateData.config.minBet)
			stateConfig.minBet = authenticateData.config.minBet / API_AMOUNT_MULTIPLIER;
		if (authenticateData.config.maxBet)
			stateConfig.maxBet = authenticateData.config.maxBet / API_AMOUNT_MULTIPLIER;
		if (authenticateData.config.stepBet)
			stateConfig.stepBet = authenticateData.config.stepBet / API_AMOUNT_MULTIPLIER;
		stateConfig.betMenuOptions = stateConfig.betAmountOptions.filter((_, index) =>
			MOST_USED_BET_INDEXES.includes(index),
		);

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
