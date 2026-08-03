<script lang="ts">
	import { stateBet, stateConfig } from 'state-shared';

	import { LADDERS, MAX_WIN_MULT, RIGS, RTP } from '../game/constants';
	import { formatMoney } from '../game/money';

	type Props = { onClose: () => void };

	let { onClose }: Props = $props();

	// social-casino markets (QA 4.4): softer wording, no real-money language
	const social = $derived(!!stateConfig.jurisdiction.socialCasino);
	const stakeWord = $derived(social ? 'play amount' : 'stake');

	const PROFILE_LABELS = {
		drip: 'frequent, small',
		balanced: 'steady',
		spike: 'rare, big',
		spike_deep: 'rare, big',
	} as const;

	// max win across the whole game: highest target x the golden multiplier
	const maxTarget = Math.max(...RIGS.map((rig) => rig.targetTemp));
	const maxWinMult = maxTarget * MAX_WIN_MULT;
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
				set your auto cash out target and your {stakeWord}, then boot the rig. the
				rig climbs on its own and stops at your target automatically -- there is
				no action to take during the round. if it melts down before the target,
				you keep only what the checkpoints banked along the way.
			</p>
			<p class="dim">
				controls: pick a rig with the slider or the - / + buttons (that sets the
				cash out target), set the {stakeWord} with - / + or by typing it, then
				press BOOT RIG. on desktop, SPACE boots. results settle automatically;
				BOOT AGAIN repeats the same round.
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">MODES</div>
			<p class="dim">
				every mode costs exactly the {stakeWord} you set (no cost multipliers).
				"pays something" is the chance a round returns any payout at all.
			</p>
			<div class="rules-table-scroll">
				<table class="rules-table">
					<thead>
						<tr>
							<th>rig</th>
							<th>cash out target</th>
							<th>pays something</th>
							<th>checkpoints</th>
							<th>cost at current {stakeWord}</th>
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
			<div class="rules-heading">PAYOUTS</div>
			<p>
				each rig has a ladder of checkpoints below its target. as the rig climbs,
				every checkpoint it crosses banks a partial payout that is kept even if
				the rig melts down afterwards. reaching the target pays the full target
				multiplier times your {stakeWord}.
			</p>
			<p>
				<span class="win">OVERDRIVE:</span> on a small share of winning rounds the
				thermal limiter slips past the target and the round pays a bonus
				multiplier on shutdown -- 1.5x the target (overdrive), 3x the target
				(critical), or 10x the target (golden shutdown). overdrive is decided by
				the round outcome; it needs no input and cannot be triggered manually.
			</p>
			<p>
				maximum win: <span class="win">{maxWinMult.toFixed(0)}x the {stakeWord}</span>
				(a golden shutdown on the {maxTarget.toFixed(0)}x rig). payouts are capped
				at the maximum win.
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">RTP</div>
			<p>
				the return to player is <span class="win">{(RTP * 100).toFixed(2)}%</span>
				on every mode and every cash out target.
			</p>
		</div>

		<div class="rules-section">
			<div class="rules-heading">DISCLAIMER</div>
			<p class="dim">
				malfunction voids all plays and pays. incomplete rounds are resumed or
				settled automatically the next time the game loads. displayed animations
				are a reveal of an outcome already settled server-side and do not affect
				the result. session statistics shown in the game are cosmetic and have no
				effect on odds or payouts.
				{#if social}
					this game is provided for entertainment purposes only.
				{/if}
			</p>
		</div>

		<button class="term-btn rules-close" onclick={onClose}>CLOSE</button>
	</div>
</div>
