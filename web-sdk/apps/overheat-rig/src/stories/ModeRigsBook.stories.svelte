<script lang="ts" module>
	import { defineMeta } from '@storybook/addon-svelte-csf';

	const { Story } = defineMeta({
		title: 'MODE_RIGS/book',
	});
</script>

<script lang="ts">
	import {
		StoryGameTemplate,
		StoryLocale,
		type TemplateArgs,
		templateArgs,
	} from 'components-storybook';

	import Game from '../components/Game.svelte';
	import { RIG_MAP, type RigId } from '../game/constants';
	import { setContext } from '../game/context';
	import { playBet } from '../game/utils';
	import {
		drawRealisticBook,
		bustInstant,
		bustFar,
		bustNearMiss,
		bustSalvage,
		winEco,
		winOverclock,
		winPlasma,
		winOverdrive,
		winCritical,
		winGolden,
		type FixtureBook,
	} from './data/books';

	import { stateBet } from 'state-shared';

	setContext();

	// storybook only: seed a balance so the rig select screen is usable
	if (stateBet.balanceAmount === 0) stateBet.balanceAmount = 1000;

	const runBook = async (fixture: FixtureBook) => {
		// storybook only: simulate the wallet the RGS would drive in live play
		// (play deducts the stake, end-round credits the payout after the reveal)
		stateBet.wageredBetAmount = stateBet.betAmount;
		stateBet.balanceAmount -= stateBet.betAmount;

		await playBet({ ...fixture, state: fixture.events } as any);

		stateBet.balanceAmount += (fixture.payoutMultiplier / 100) * stateBet.wageredBetAmount;
	};
</script>

{#snippet template(args: TemplateArgs<any>)}
	<StoryGameTemplate
		skipLoadingScreen={args.skipLoadingScreen}
		action={async () => {
			await args.action?.(args.data);
		}}
	>
		<StoryLocale lang="en">
			<Game />
		</StoryLocale>
	</StoryGameTemplate>
{/snippet}

<Story
	name="random"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => {
			// draw from the true 96.5%-RTP spicy distribution for the dialed rig
			const rig = RIG_MAP[stateBet.activeBetModeKey as RigId] ?? RIG_MAP.standard;
			await runBook(drawRealisticBook(rig.id, rig.targetTemp));
		},
	})}
	{template}
/>

<Story
	name="bust instant (fried on boot)"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(bustInstant),
	})}
	{template}
/>

<Story
	name="bust far below target"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(bustFar),
	})}
	{template}
/>

<Story
	name="bust near miss (signature moment)"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(bustNearMiss),
	})}
	{template}
/>

<Story
	name="win eco 1.5x"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(winEco),
	})}
	{template}
/>

<Story
	name="win overclock 5x"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(winOverclock),
	})}
	{template}
/>

<Story
	name="win plasma 100x"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(winPlasma),
	})}
	{template}
/>

<Story
	name="bust with scrap salvage (0.4x back)"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(bustSalvage),
	})}
	{template}
/>

<Story
	name="overdrive 1.5x target (overclock 7.5x)"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(winOverdrive),
	})}
	{template}
/>

<Story
	name="critical overdrive 3x target (boost 9x)"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(winCritical),
	})}
	{template}
/>

<Story
	name="golden shutdown 10x target (furnace 100x)"
	args={templateArgs({
		skipLoadingScreen: true,
		data: {},
		action: async () => runBook(winGolden),
	})}
	{template}
/>
