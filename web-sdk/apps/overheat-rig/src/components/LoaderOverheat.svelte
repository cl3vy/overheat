<script lang="ts">
	/**
	 * Branded CRT boot screen (QA 5.6). The SDK template ships two
	 * placeholders here -- a generic "Stake Engine" splash gif and a
	 * "LoaderExample" that literally renders the text "Add Your Loader" --
	 * and the submission checklist forbids shipping either. This replaces
	 * both with the game's own BIOS-boot aesthetic, no image asset needed.
	 */
	import { onMount } from 'svelte';

	type Props = { oncomplete?: () => void };

	const { oncomplete }: Props = $props();

	const BOOT_LINES = [
		'OVERHEAT THERMAL BIOS v2.0',
		'POST........................ OK',
		'checking cooling loop....... OK',
		'spinning up rig array....... OK',
		'RGS handshake...............',
	];

	// total time the boot screen holds, matching the SDK template's own
	// splash timing (~2s) so load doesn't feel slower or faster than before
	const HOLD_MS = 2000;

	let visible = $state(true);
	let linesShown = $state(0);

	onMount(() => {
		const stepMs = Math.round((HOLD_MS * 0.7) / BOOT_LINES.length);
		const timers: ReturnType<typeof setTimeout>[] = [];
		BOOT_LINES.forEach((_, index) => {
			timers.push(
				setTimeout(() => {
					linesShown = index + 1;
				}, stepMs * index),
			);
		});
		timers.push(
			setTimeout(() => {
				visible = false;
				oncomplete?.();
			}, HOLD_MS),
		);
		return () => timers.forEach(clearTimeout);
	});
</script>

{#if visible}
	<div class="loader-wrap" role="status" aria-label="loading">
		<div class="loader-scanlines" aria-hidden="true"></div>
		<div class="loader-body">
			<div class="loader-logo">OVERHEAT</div>
			<div class="loader-sub">MINING RIG THERMAL CONSOLE</div>
			<div class="loader-log">
				{#each BOOT_LINES.slice(0, linesShown) as line, index (line)}
					<div class="loader-line">
						&gt; {line}{#if index === linesShown - 1 && index === BOOT_LINES.length - 1}<span
								class="loader-cursor">_</span
							>{/if}
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}

<style>
	.loader-wrap {
		position: fixed;
		inset: 0;
		z-index: 999;
		background: #0a0e0a;
		color: #00ff41;
		font-family: 'Menlo', 'Consolas', 'DejaVu Sans Mono', 'Courier New', monospace;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		text-shadow: 0 0 6px rgba(0, 255, 65, 0.35);
	}

	.loader-scanlines {
		position: absolute;
		inset: 0;
		pointer-events: none;
		background: repeating-linear-gradient(
			to bottom,
			rgba(0, 0, 0, 0) 0px,
			rgba(0, 0, 0, 0) 1px,
			rgba(0, 0, 0, 0.35) 2px,
			rgba(0, 0, 0, 0.35) 3px
		);
	}

	.loader-body {
		text-align: center;
		padding: 0 24px;
	}

	.loader-logo {
		font-size: clamp(28px, 8vw, 56px);
		font-weight: bold;
		letter-spacing: 0.12em;
		animation: loader-flicker 2.6s infinite;
	}

	.loader-sub {
		margin-top: 8px;
		font-size: clamp(10px, 2.4vw, 13px);
		letter-spacing: 0.2em;
		opacity: 0.7;
	}

	.loader-log {
		margin-top: 22px;
		font-size: clamp(10px, 2.2vw, 13px);
		text-align: left;
		min-height: 6.5em;
		opacity: 0.85;
	}

	.loader-line {
		white-space: nowrap;
	}

	.loader-cursor {
		animation: loader-blink 1s steps(1) infinite;
	}

	@keyframes loader-blink {
		50% {
			opacity: 0;
		}
	}

	@keyframes loader-flicker {
		0%,
		94%,
		100% {
			opacity: 1;
		}
		95% {
			opacity: 0.82;
		}
		96% {
			opacity: 1;
		}
		97% {
			opacity: 0.88;
		}
	}
</style>
