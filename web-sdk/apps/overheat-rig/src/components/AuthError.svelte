<script lang="ts">
	// Game never mounts on auth failure, so pull CRT styles in here.
	import './app.css';
</script>

<!--
	Terminal auth failure screen. No controls that start or resume a round.
-->
<div class="tv-shell">
	<div class="crt ambient-low scanlines auth-fail-crt">
		<div class="crt-ambient" aria-hidden="true"></div>
		<div class="term-header">
			<span class="term-title-full">OVERHEAT // MINING RIG THERMAL CONSOLE</span>
			<span class="term-title-mini">OVERHEAT</span>
		</div>
		<div class="term-main auth-fail-main" role="alert">
			<div class="auth-fail-panel">
				<div class="log-line fault">!! AUTHENTICATION FAILED</div>
				<div class="log-line fault">&gt; Authentication failed. Cannot start game.</div>
				<div class="log-line dim" style="margin-top: 12px;">
					&gt; rgs handshake rejected -- reload with a valid session to continue
				</div>
			</div>
		</div>
		<div class="crt-glass" aria-hidden="true"></div>
	</div>
</div>

<style>
	.auth-fail-crt {
		min-height: 100%;
	}

	.auth-fail-main {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 24px;
	}

	.auth-fail-panel {
		max-width: 36rem;
		border: 1px solid rgba(255, 60, 60, 0.55);
		box-shadow: 0 0 18px rgba(255, 40, 40, 0.18);
		padding: 18px 20px;
		background: rgba(8, 0, 0, 0.45);
	}
</style>
