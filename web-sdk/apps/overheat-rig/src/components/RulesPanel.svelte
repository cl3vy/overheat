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
		wordStake,
	} from '../game/socialCopy';

	type Props = { onClose: () => void };

	let { onClose }: Props = $props();

	// social-casino markets: restricted gambling phrases use approved swaps
	const social = $derived(isSocialCasino());
	const stakeWord = $derived(wordStake());
	const cashOut = $derived(wordCashOut());
	const paysWord = $derived(wordPays());
	const payoutWord = $derived(wordPayout());
	const payoutsWord = $derived(social ? 'wins' : 'payouts');
	const payoutsHeading = $derived(labelPayouts());
	const modeCosts = $derived(phraseModeCosts());
	const costAt = $derived(labelCostAt());

	const PROFILE_LABELS = {
		drip: 'frequent, small',
		balanced: 'steady',
		spike: 'rare, big',
		spike_deep: 'rare, big',
	} as const;

	const maxWinMult = Math.max(...Object.values(MODE_MAX_WIN));
	const maxWinMode = RIGS.find((rig) => MODE_MAX_WIN[rig.id] === maxWinMult)?.name ?? 'PLASMA';
</script>

<!-- submission checklist: RTP, max win, payout information, mode descriptions
     with cost info, general disclaimer, interaction guide -- all in one
     internally-scrollable overlay so the game frame itself never scrolls -->
<div class="rules-overlay" role="dialog" aria-label="game rules">
	<div class="rules-pop">
		<div class="rules-title">// GAME RULES</div>

		<div class="rules-section">
			<div class="rules-heading">HOW TO PLAY</div>
			<p>
				set your auto {cashOut} target and your {stakeWord}, then boot the rig. the
				rig climbs on its own and stops at your target automatically -- there is
				no action to take during the round. if it melts down before the target,
				you keep only what the checkpoints banked along the way.
			</p>
			<p class="dim">
				controls: pick a rig with the slider or the - / + buttons (that sets the
				{cashOut} target), set the {stakeWord} with - / + or by typing it, then
				press BOOT RIG. on desktop, SPACE boots. results settle automatically;
				BOOT AGAIN repeats the same round.
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">MODES</div>
			<p class="dim">
				{modeCosts} the {stakeWord} you set{social ? '' : ' (no cost multipliers)'}.
				"{paysWord} something" is the chance a round returns any {payoutWord} at all.
			</p>
			<div class="rules-table-scroll">
				<table class="rules-table">
					<thead>
						<tr>
							<th>rig</th>
							<th>{cashOut} target</th>
							<th>{paysWord} something</th>
							<th>checkpoints</th>
							<th>{costAt} {stakeWord}</th>
						</tr>
					</thead>
					<tbody>
						{#each RIGS as rig (rig.id)}
							<tr>
								<td>{rig.name}</td>
								<td>{rig.targetTemp.toFixed(2)}x</td>
								<td>{(LADDERS[rig.id].anyPayoutProb * 100).toFixed(1)}%</td>
								<td>{PROFILE_LABELS[LADDERS[rig.id].profile]}</td>
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
				each rig has a ladder of checkpoints below its target. as the rig climbs,
				every checkpoint it crosses banks a partial {payoutWord} that is kept even if
				the rig melts down afterwards. reaching the target {paysWord} the full target
				multiplier times your {stakeWord}.
			</p>
			<p>
				<span class="win">OVERDRIVE:</span> on a small share of winning rounds the
				thermal limiter slips past the target and the round {paysWord} a bonus
				multiplier on shutdown -- 1.5x the target (overdrive), 3x the target
				(critical), or 10x the target (golden shutdown). overdrive is decided by
				the round outcome; it needs no input and cannot be triggered manually.
			</p>
			<p>
				maximum win: <span class="win">{maxWinMult.toFixed(0)}x the {stakeWord}</span>
				(a top payout on {maxWinMode}). {payoutsWord} are capped
				at the maximum win.
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">RTP</div>
			<p>
				the return to player is <span class="win">{(RTP * 100).toFixed(2)}%</span>
				on every mode and every {cashOut} target.
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">DISCLAIMER</div>
			<p class="dim">
				Malfunction voids all wins and plays. A consistent internet connection is
				required. In the event of a disconnection, reload the game to finish any
				uncompleted rounds. The expected return is calculated over many plays. The
				game display is not representative of any physical device and is for
				illustrative purposes only. Winnings are settled according to the amount
				received from the Remote Game Server and not from events within the web
				browser. TM and © 2026 Stake Engine.
				{#if social}
					This game is provided for entertainment purposes only.
				{/if}
			</p>
		</div>

		<button class="term-btn rules-close" onclick={onClose}>CLOSE</button>
	</div>
</div>
