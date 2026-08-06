<script lang="ts">
	import { playSwitchClick } from '../game/sound';
	import { t } from '../game/t';

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
	title={t('turbo_tooltip')}
>
	<span class="turbo-text">{checked ? t('turbo_on') : t('turbo_off')}</span>
</button>
