<script lang="ts">
	import { stateModal } from 'state-shared';

	const ERROR_HINTS: Record<string, string> = {
		ERR_VAL: 'request rejected: invalid parameters',
		ERR_IPB: 'insufficient power reserve (balance too low)',
		ERR_IS: 'session invalid or expired -- relaunch the game',
		ERR_ATE: 'authentication token expired -- relaunch the game',
		ERR_GLE: 'gambling limits exceeded',
		ERR_LOC: 'play not permitted from this location',
		ERR_BE: 'a round is already active on this session',
		ERR_GEN: 'server fault -- try again',
		ERR_MAINTENANCE: 'engine down for maintenance -- try again later',
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

	const hint = $derived(ERROR_HINTS[errorCode] ?? 'unexpected fault -- check console for details');

	const dismiss = () => {
		stateModal.modal = null;
	};
</script>

{#if modal?.name === 'error'}
	<div class="overlay">
		<div class="panel">
			<div class="log-line fault">!! SYSTEM FAULT {errorCode ? `[${errorCode}]` : ''}</div>
			<div class="log-line fault">&gt; {hint}</div>
			<div style="margin-top: 12px;">
				<button class="term-btn danger" onclick={dismiss}>ACKNOWLEDGE</button>
			</div>
		</div>
	</div>
{/if}
