<script lang="ts">
	import { API_AMOUNT_MULTIPLIER } from 'constants-shared/bet';
	import { stateBet, stateMeta, stateUrlDerived } from 'state-shared';

	import { BOOK_AMOUNT_SCALE } from '../game/constants';
	import { formatMoney, toBaseUnits } from '../game/money';
	import {
		labelReplayBaseBet,
		labelReplayPayoutMult,
		labelReplayTotalBet,
	} from '../game/socialCopy';
	import { rigName, t } from '../game/t';
	import type { Bet } from '../game/typesBookEvent';

	type Props = { onStart: () => void };

	let { onStart }: Props = $props();

	const bet = $derived(stateBet.betToResume as Bet | null);

	const modeKey = $derived(
		(bet?.mode || stateUrlDerived.mode() || stateBet.activeBetModeKey || '').toString(),
	);

	const modeLabel = $derived.by(() => {
		const key = modeKey;
		if (!key) return '—';
		const named = rigName(key.toLowerCase());
		// rigName falls back to the message key when missing — treat as unknown
		if (named && named !== `rig_${key.toLowerCase()}_name`) return named.toUpperCase();
		return key.toUpperCase();
	});

	/** Base stake in whole currency units. */
	const baseBet = $derived.by(() => {
		const fromUrl = stateUrlDerived.amount();
		if (fromUrl > 0) return fromUrl / API_AMOUNT_MULTIPLIER;
		if (stateBet.betAmount > 0) return stateBet.betAmount;
		const roundAmount = bet?.amount;
		if (typeof roundAmount === 'number' && roundAmount > 0) {
			// RGS / replay amount is API base units
			return roundAmount / API_AMOUNT_MULTIPLIER;
		}
		return 0;
	});

	const costMultiplier = $derived.by(() => {
		const fromReplay = (bet as { costMultiplier?: number } | null)?.costMultiplier;
		if (typeof fromReplay === 'number' && Number.isFinite(fromReplay) && fromReplay > 0) {
			return fromReplay;
		}
		const meta =
			stateMeta.betModeMeta?.[modeKey] ??
			stateMeta.betModeMeta?.[modeKey.toLowerCase()] ??
			stateMeta.betModeMeta?.[modeKey.toUpperCase()];
		if (typeof meta?.costMultiplier === 'number' && meta.costMultiplier > 0) {
			return meta.costMultiplier;
		}
		return 1;
	});

	const payoutMultiplier = $derived.by(() => {
		const fromRound = bet?.payoutMultiplier;
		if (typeof fromRound === 'number' && Number.isFinite(fromRound)) return fromRound;
		const events = bet?.state ?? [];
		for (let i = events.length - 1; i >= 0; i -= 1) {
			const event = events[i];
			if (event.type === 'finalWin' || event.type === 'setTotalWin') {
				return event.amount / BOOK_AMOUNT_SCALE;
			}
		}
		return 0;
	});

	const totalBetCost = $derived(baseBet * costMultiplier);
	const totalWin = $derived(totalBetCost * payoutMultiplier);

	// Stake template labels; socialCasino swaps bet/payout via socialCopy
	const rowMode = $derived(t('replay_row_mode'));
	const rowBaseBet = $derived(labelReplayBaseBet());
	const rowCostMult = $derived(t('replay_row_cost_mult'));
	const rowTotalBet = $derived(labelReplayTotalBet());
	const rowPayoutMult = $derived(labelReplayPayoutMult());
	const rowTotalWin = $derived(t('replay_row_total_win'));

	const formatMult = (value: number) => {
		if (!Number.isFinite(value)) return '0x';
		const rounded = Math.round(value * 1000) / 1000;
		const text = Number.isInteger(rounded)
			? String(rounded)
			: String(rounded).replace(/(\.\d*?[1-9])0+$/, '$1').replace(/\.0+$/, '');
		return `${text}x`;
	};
</script>

<div class="replay-overlay" role="dialog" aria-label={t('a11y_replay_summary')}>
	<div class="replay-pop">
		<div class="replay-title">{t('replay_summary_title')}</div>
		<p class="replay-note dim">{t('replay_summary_note')}</p>

		<table class="replay-table">
			<tbody>
				<tr>
					<th scope="row">{rowMode}</th>
					<td>{modeLabel}</td>
				</tr>
				<tr>
					<th scope="row">{rowBaseBet}</th>
					<td>{formatMoney(toBaseUnits(baseBet))}</td>
				</tr>
				<tr>
					<th scope="row">{rowCostMult}</th>
					<td>{formatMult(costMultiplier)}</td>
				</tr>
				<tr>
					<th scope="row">{rowTotalBet}</th>
					<td>{formatMoney(toBaseUnits(totalBetCost))}</td>
				</tr>
				<tr>
					<th scope="row">{rowPayoutMult}</th>
					<td>{formatMult(payoutMultiplier)}</td>
				</tr>
				<tr>
					<th scope="row">{rowTotalWin}</th>
					<td class="win">{formatMoney(toBaseUnits(totalWin))}</td>
				</tr>
			</tbody>
		</table>

		<button class="boot-btn replay-start" onclick={onStart}>{t('btn_start_replay')}</button>
	</div>
</div>
