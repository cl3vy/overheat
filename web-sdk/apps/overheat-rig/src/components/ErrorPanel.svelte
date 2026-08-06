<script lang="ts">
	import { stateModal } from 'state-shared';

	import type { MessageKey } from '../i18n/messagesMap/en';
	import { wordGambling } from '../game/socialCopy';
	import { t } from '../game/t';

	const ERROR_HINTS: Record<string, MessageKey> = {
		ERR_VAL: 'err_val',
		ERR_IPB: 'err_ipb',
		ERR_IS: 'err_is',
		ERR_ATE: 'err_ate',
		ERR_GLE: 'err_gle',
		ERR_LOC: 'err_loc',
		ERR_BE: 'err_be',
		ERR_GEN: 'err_gen',
		ERR_MAINTENANCE: 'err_maintenance',
	};

	const modal = $derived(stateModal.modal);

	const errorCode = $derived.by(() => {
		if (modal?.name !== 'error') return '';
		const error = modal.error;
		return (
			error?.error?.statusCode ??
			error?.status?.statusCode ??
			error?.statusCode ??
			(typeof error?.error === 'string' ? error.error : '') ??
			''
		);
	});

	const hint = $derived.by(() => {
		if (errorCode === 'ERR_GLE') return t('err_gle', { gambling: wordGambling() });
		const key = ERROR_HINTS[errorCode] ?? 'err_unexpected';
		return t(key);
	});

	const dismiss = () => {
		stateModal.modal = null;
	};
</script>

{#if modal?.name === 'error'}
	<div class="overlay">
		<div class="panel">
			<div class="log-line fault">
				{t('error_system_fault', { code: errorCode ? `[${errorCode}]` : '' })}
			</div>
			<div class="log-line fault">&gt; {hint}</div>
			<div style="margin-top: 12px;">
				<button class="term-btn danger" onclick={dismiss}>{t('btn_acknowledge')}</button>
			</div>
		</div>
	</div>
{/if}
