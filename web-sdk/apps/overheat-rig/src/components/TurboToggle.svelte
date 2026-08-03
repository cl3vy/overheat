<script lang="ts">
	import { playSwitchClick } from '../game/sound';

	type Props = {
		checked: boolean;
		onToggle: (value: boolean) => void;
	};

	let { checked, onToggle }: Props = $props();

	const flip = () => {
		const next = !checked;
		onToggle(next);
		playSwitchClick(next);
	};
</script>

<button
	class="turbo-btn"
	class:on={checked}
	onclick={flip}
	aria-pressed={checked}
	title="turbo: faster reveal, same odds"
>
	<span class="turbo-text">TURBO [{checked ? 'ON' : 'OFF'}]</span>
</button>
