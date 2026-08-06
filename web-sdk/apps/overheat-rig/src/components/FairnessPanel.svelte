<script lang="ts">
	import { stateConfig } from 'state-shared';

	import { RTP } from '../game/constants';
	import { stateSession } from '../game/stateSession.svelte';
	import { t } from '../game/t';

	type Props = { onClose: () => void };

	let { onClose }: Props = $props();

	const showRtp = $derived(stateConfig.jurisdiction.displayRTP);
</script>

<!-- trust hook (brief 1.6): surface the fairness proof, never the loss math.
     every figure here is true and verifiable with the operator. -->
<div class="fairness-pop" role="dialog" aria-label={t('a11y_fairness')}>
	<div class="fairness-title">{t('fairness_title')}</div>
	{#if showRtp}
		<div class="fairness-row">
			<span class="dim">{t('rules_rtp_heading')}</span>
			<span class="win">{t('fairness_rtp', { percent: (RTP * 100).toFixed(1) })}</span>
		</div>
	{/if}
	<div class="fairness-row">
		<span class="dim">{t('fairness_last_round')}</span>
		<span>{stateSession.lastRoundID ?? '--'}</span>
	</div>
	<div class="fairness-copy dim">
		{t('fairness_body')}
	</div>
	<button class="term-btn" onclick={onClose}>{t('btn_close')}</button>
</div>
