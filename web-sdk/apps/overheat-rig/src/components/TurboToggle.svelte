<script lang="ts">
	import { playSwitchClick } from '../game/sound';

	type Props = {
		checked: boolean;
		onToggle: (value: boolean) => void;
	};

	let { checked, onToggle }: Props = $props();

	const FLAME_CHARS = ['^', ')', '*', '(', ';', "'", '~', '^', '*', ')', ';', '('];

	const flip = () => {
		const next = !checked;
		onToggle(next);
		playSwitchClick(next);
	};
</script>

<button class="turbo-btn" class:on={checked} onclick={flip} aria-pressed={checked}>
	{#if checked}
		<span class="turbo-flames" aria-hidden="true">
			{#each FLAME_CHARS as char, index (index)}
				<span class="fglyph" style="--i: {index}">{char}</span>
			{/each}
		</span>
	{/if}
	<span class="turbo-text">TURBO [{checked ? 'ON' : 'OFF'}]</span>
</button>
