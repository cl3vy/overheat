<script lang="ts">
	import { stateBet } from 'state-shared';

	import { LADDERS, MODE_MAX_WIN, RIGS, RTP } from '../game/constants';
	import { formatMoney } from '../game/money';
	import {
		isSocialCasino,
		labelCostAt,
		labelPayouts,
		phraseModeCosts,
		wordCashOut,
		wordPays,
		wordPayout,
		wordPayoutsPlural,
		wordStake,
	} from '../game/socialCopy';
	import { rigName, t } from '../game/t';

	type Props = { onClose: () => void };

	let { onClose }: Props = $props();

	// social-casino markets: restricted gambling phrases use approved swaps
	const social = $derived(isSocialCasino());
	const stakeWord = $derived(wordStake());
	const cashOut = $derived(wordCashOut());
	const paysWord = $derived(wordPays());
	const payoutWord = $derived(wordPayout());
	const payoutsWord = $derived(wordPayoutsPlural());
	const payoutsHeading = $derived(labelPayouts());
	const modeCosts = $derived(phraseModeCosts());
	const costAt = $derived(labelCostAt());

	const profileLabel = (profile: string) => {
		if (profile === 'drip') return t('profile_drip');
		if (profile === 'balanced') return t('profile_balanced');
		return t('profile_spike');
	};

	const maxWinMult = Math.max(...Object.values(MODE_MAX_WIN));
	const maxWinModeId = RIGS.find((rig) => MODE_MAX_WIN[rig.id] === maxWinMult)?.id ?? 'plasma';
	const maxWinMode = $derived(rigName(maxWinModeId));
</script>

<!-- submission checklist: RTP, max win, payout information, mode descriptions
     with cost info, general disclaimer, interaction guide -- all in one
     internally-scrollable overlay so the game frame itself never scrolls -->
<div class="rules-overlay" role="dialog" aria-label={t('a11y_rules')}>
	<div class="rules-pop">
		<div class="rules-title">{t('rules_title')}</div>

		<div class="rules-section">
			<div class="rules-heading">{t('rules_how_to_play')}</div>
			<p>
				{t('rules_howto_body', { cashOut, stake: stakeWord })}
			</p>
			<p class="dim">
				{t('rules_controls', { cashOut, stake: stakeWord })}
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">{t('rules_modes')}</div>
			<p class="dim">
				{t('rules_modes_intro', {
					modeCosts,
					stake: stakeWord,
					noCostNote: social ? '' : t('rules_no_cost_multipliers'),
					pays: paysWord,
					payout: payoutWord,
				})}
			</p>
			<div class="rules-table-scroll">
				<table class="rules-table">
					<thead>
						<tr>
							<th>{t('rules_th_rig')}</th>
							<th>{t('rules_th_cashout_target', { cashOut })}</th>
							<th>{t('rules_th_pays_something', { pays: paysWord })}</th>
							<th>{t('rules_th_checkpoints')}</th>
							<th>{t('rules_th_cost', { costAt, stake: stakeWord })}</th>
						</tr>
					</thead>
					<tbody>
						{#each RIGS as rig (rig.id)}
							<tr>
								<td>{rigName(rig.id)}</td>
								<td>{rig.targetTemp.toFixed(2)}x</td>
								<td>{(LADDERS[rig.id].anyPayoutProb * 100).toFixed(1)}%</td>
								<td>{profileLabel(LADDERS[rig.id].profile)}</td>
								<td>{formatMoney(stateBet.betAmount)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>

		<div class="rules-section">
			<div class="rules-heading">{payoutsHeading}</div>
			<p>
				{t('rules_payouts_body', {
					payout: payoutWord,
					pays: paysWord,
					stake: stakeWord,
				})}
			</p>
			<p>
				{t('rules_overdrive', { pays: paysWord })}
			</p>
			<p>
				{t('rules_max_win', {
					maxWin: maxWinMult.toFixed(0),
					stake: stakeWord,
					mode: maxWinMode,
					payouts: payoutsWord,
				})}
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">{t('rules_rtp_heading')}</div>
			<p>
				{t('rules_rtp_body', {
					percent: (RTP * 100).toFixed(2),
					cashOut,
				})}
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">{t('rules_disclaimer_heading')}</div>
			<p class="dim">
				{t('rules_disclaimer')}
				{#if social}
					{t('rules_social_entertainment')}
				{/if}
			</p>
		</div>

		<button class="term-btn rules-close" onclick={onClose}>{t('btn_close')}</button>
	</div>
</div>
