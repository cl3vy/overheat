export type RigId =
	| 'idle'
	| 'eco'
	| 'standard'
	| 'boost'
	| 'overclock'
	| 'nitro'
	| 'furnace'
	| 'inferno'
	| 'meltdown'
	| 'reactor'
	| 'plasma';

export type RigInfo = {
	id: RigId;
	name: string;
	targetTemp: number;
	flavor: string;
};

// dense ladder so the shutdown-temp dial feels like a custom multiplier
export const RIGS: RigInfo[] = [
	{ id: 'idle', name: 'IDLE', targetTemp: 1.2, flavor: 'barely warm. basically a savings account.' },
	{ id: 'eco', name: 'ECO', targetTemp: 1.5, flavor: 'undervolted. boring. pays the rent.' },
	{ id: 'standard', name: 'STANDARD', targetTemp: 2, flavor: 'stock cooler, stock nerves.' },
	{ id: 'boost', name: 'BOOST', targetTemp: 3, flavor: 'factory overclock. mild sweat.' },
	{ id: 'overclock', name: 'OVERCLOCK', targetTemp: 5, flavor: 'warranty void. thermal paste optional.' },
	{ id: 'nitro', name: 'NITRO', targetTemp: 7, flavor: 'aftermarket fans, screaming.' },
	{ id: 'furnace', name: 'FURNACE', targetTemp: 10, flavor: 'heats the room. sometimes the house.' },
	{ id: 'inferno', name: 'INFERNO', targetTemp: 15, flavor: 'the smoke detector is unplugged.' },
	{ id: 'meltdown', name: 'MELTDOWN', targetTemp: 25, flavor: 'silicon roulette. bring a fire blanket.' },
	{ id: 'reactor', name: 'REACTOR', targetTemp: 50, flavor: 'unlicensed fission. tell no one.' },
	{ id: 'plasma', name: 'PLASMA', targetTemp: 100, flavor: 'this is not mining. this is a star.' },
];

export const RIG_MAP: Record<RigId, RigInfo> = Object.fromEntries(
	RIGS.map((rig) => [rig.id, rig]),
) as Record<RigId, RigInfo>;

// terminal palette (brief 5.3)
export const COLORS = {
	bg: '#0a0e0a',
	green: '#00ff41',
	amber: '#ffb000',
	red: '#ff2b2b',
};

// book event amounts are payout multiplier x 100 (matches math generator)
export const BOOK_AMOUNT_SCALE = 100;

export const MAX_LOG_LINES = 14;
