<script lang="ts">
	import { RTP } from '../game/constants';
	import { stateSession } from '../game/stateSession.svelte';

	type Props = { onClose: () => void };

	let { onClose }: Props = $props();
</script>

<!-- trust hook (brief 1.6): surface the fairness proof, never the loss math.
     every figure here is true and verifiable with the operator. -->
<div class="fairness-pop" role="dialog" aria-label="provably fair details">
	<div class="fairness-title">// PROVABLY FAIR</div>
	<div class="fairness-row">
		<span class="dim">RTP</span>
		<span class="win">{(RTP * 100).toFixed(1)}% -- every rig</span>
	</div>
	<div class="fairness-row">
		<span class="dim">LAST ROUND ID</span>
		<span>{stateSession.lastRoundID ?? '--'}</span>
	</div>
	<div class="fairness-copy dim">
		every outcome is drawn from a sealed, precomputed outcome table and settled
		server-side by the Stake Engine RGS before the reveal animates. the reveal
		cannot change the result. quote a round id to the operator to audit any
		settled round.
	</div>
	<button class="term-btn" onclick={onClose}>CLOSE</button>
</div>
