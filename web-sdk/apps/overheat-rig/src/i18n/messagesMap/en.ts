/**
 * Overheat source locale (English).
 * Stable descriptive keys — never use English text as the key.
 *
 * UNTRANSLATED (kept as-is across locales):
 * - brand_overheat, brand fragments "OVERHEAT"
 * - Units: MW, MH/s, x multipliers, %
 * - Error codes ERR_*
 * - ASCII/glyphs in rain and rung marks
 * - Rig API ids (idle…plasma) — display names are translated separately
 */
const en = {
	// —— Brand / chrome (brand stays OVERHEAT) ——
	brand_overheat: 'OVERHEAT',
	hdr_console_full: 'OVERHEAT // MINING RIG THERMAL CONSOLE',
	hdr_console_sub: 'MINING RIG THERMAL CONSOLE',
	btn_rules: '[RULES]',
	hdr_session: 'SESSION {time}',
	hdr_rtp: 'RTP {percent}%',
	hdr_replay: 'REPLAY -- ROUND PLAYBACK',
	hdr_pwr_reserve: 'PWR RESERVE:',
	hdr_net: 'NET {amount}',
	hdr_turbo: ' [TURBO]',
	status_loading_replay: 'loading replay...',
	replay_summary_title: '// REPLAY SUMMARY',
	replay_summary_note:
		'this is a replay of a previous round. no real bet is placed.',
	replay_row_mode: 'Mode',
	replay_row_base_bet: 'Base Bet',
	replay_row_base_bet_social: 'Base Play',
	replay_row_cost_mult: 'Cost Multiplier',
	replay_row_total_bet: 'Total Bet Cost',
	replay_row_total_bet_social: 'Total Play Cost',
	replay_row_payout_mult: 'Payout Multiplier',
	replay_row_payout_mult_social: 'Win Multiplier',
	replay_row_total_win: 'Total Win',
	btn_start_replay: '>> START REPLAY <<',
	a11y_replay_summary: 'replay bet summary',

	// —— Social / standard lexicon ——
	word_stake: 'stake',
	word_stake_social: 'play amount',
	label_stake: 'STAKE',
	label_stake_social: 'PLAY AMOUNT',
	word_cash_out: 'cash out',
	word_cash_out_social: 'collect',
	label_cash_out_target: 'CASH OUT TARGET',
	label_cash_out_target_social: 'COLLECT TARGET',
	word_pays: 'pays',
	word_pays_social: 'wins',
	word_pay: 'pay',
	word_pay_social: 'win',
	word_payout: 'payout',
	word_payout_social: 'win',
	label_payouts: 'PAYOUTS',
	label_payouts_social: 'WINS',
	word_gambling: 'gambling',
	word_gambling_social: 'play',
	label_cost_at: 'cost at current',
	label_cost_at_social: 'can be played for at current',
	phrase_mode_costs: 'every mode costs exactly',
	phrase_mode_costs_social: 'every mode can be played for exactly',
	word_payouts_plural: 'payouts',
	word_payouts_plural_social: 'wins',

	// —— Rig select / how it works ——
	loop_title: '// HOW IT WORKS',
	loop_body_first:
		'set your auto {cashOut} target. boot the rig. it climbs on its own and stops there automatically. {meltdownClause}',
	loop_body_return:
		'> set your auto {cashOut} target -- the rig climbs on its own and stops there automatically. {meltdownClause}',
	loop_melt_keep_checkpoints:
		'if it melts down first, you keep only what the checkpoints locked.',
	loop_melt_lose_stake: 'if it melts down first, you lose the {stake}.',
	stat_hottest: 'HOTTEST',
	stat_hottest_value: '{mult}x',
	stat_best_bank: 'BEST HAUL',
	stat_hottest_empty: 'HOTTEST --',
	dial_translate: '{cashOut} at {mult}x',
	a11y_shutdown_temp: 'shutdown temperature',
	dial_scale_safe: 'safe',
	dial_scale_spicy: 'spicy',
	dial_pays_something: '{pays} something: {percent}% of runs',
	label_stake_row: '{stake}:',
	dial_full_send: 'full send {pays} {winPays}, up to {maxPays} on overdrive',
	btn_boot_rig: '>> BOOT RIG <<',
	warn_insufficient_pwr: 'insufficient power reserve -- lower the {stake}',
	hint_space_boot: '[SPACE] to boot',
	settings_sound: 'sound',
	settings_scanlines: 'scanlines',
	settings_flicker: 'flicker',
	a11y_settings: 'display and sound settings',

	// —— Rig names ——
	rig_idle_name: 'IDLE',
	rig_eco_name: 'ECO',
	rig_standard_name: 'STANDARD',
	rig_boost_name: 'BOOST',
	rig_overclock_name: 'OVERCLOCK',
	rig_nitro_name: 'NITRO',
	rig_furnace_name: 'FURNACE',
	rig_inferno_name: 'INFERNO',
	rig_meltdown_name: 'SUPERNOVA',
	rig_reactor_name: 'REACTOR',
	rig_plasma_name: 'PLASMA',

	// —— Rig flavors ——
	flavor_idle: 'barely warm. basically idling.',
	flavor_eco: 'undervolted. boring. pays the rent.',
	flavor_eco_social: 'undervolted. boring. wins the rent.',
	flavor_standard: 'stock cooler, stock nerves.',
	flavor_boost: 'factory overclock. mild sweat.',
	flavor_overclock: 'warranty void. thermal paste optional.',
	flavor_nitro: 'aftermarket fans, screaming.',
	flavor_furnace: 'heats the room. sometimes the house.',
	flavor_inferno: 'the smoke detector is unplugged.',
	flavor_meltdown: 'silicon roulette. bring a fire blanket.',
	flavor_reactor: 'unlicensed fission. tell no one.',
	flavor_plasma: 'this is not mining. this is a star.',

	// —— Checkpoint profiles (rules table) ——
	profile_drip: 'frequent, small',
	profile_balanced: 'steady',
	profile_spike: 'rare, big',

	// —— Run view ——
	run_topline: 'RIG: {rig} | {stakeLabel}: {amount}',
	col_sys_log: '// SYS LOG',
	label_core_temp: 'CORE TEMP',
	tag_limiter_slipped: '!! LIMITER SLIPPED -- OVERDRIVE !!',
	run_cashout_at: '{cashOut} @ {mult}x',
	label_secured_yield: 'SECURED YIELD',
	yield_next_lock: 'next lock @ {nextMult}x → {bankMult}x',
	yield_all_locked: 'all checkpoints locked -- push for the target',
	col_checkpoints: '// CHECKPOINTS',
	ladder_full: 'FULL {mult}x',

	result_meltdown: '** MELTDOWN @ {mult}x **',
	result_near_miss: 'died {delta}x short of the {checkpoint}x checkpoint',
	result_aimed_for: 'aimed for {mult}x',
	result_checkpoints_held: '>> CHECKPOINTS HELD: +{amount} secured',

	win_headline_clean: 'CLEAN SHUTDOWN',
	win_headline_overdrive: 'THERMAL LIMITER SLIPPED -- OVERDRIVE TIER',
	win_headline_critical: 'BREAKER SLAMMED -- CRITICAL TIER',
	win_headline_golden: 'THE SILICON ASCENDED -- GOLDEN TIER',
	win_label_golden: 'GOLDEN SHUTDOWN',
	win_label_legendary: 'LEGENDARY RUN',
	win_label_massive: 'MASSIVE HAUL',
	win_label_huge: 'HUGE HAUL',
	win_label_big: 'BIG HAUL',
	win_label_clean: 'SECURED',
	win_banner: '>>> {label} <<<',
	win_tier_note:
		'tier label only -- the round {pays} the {mult}x shutdown reached, not a flat multiple of your target',
	win_peaked: 'ran clean -- peaked at {mult}x',
	win_survived: '{mult}x survived',
	badge_personal_best: '★ NEW PERSONAL BEST ★',
	badge_personal_best_run: '★ NEW PERSONAL BEST RUN ★',

	btn_replay_again: '>> REPLAY AGAIN <<',
	btn_boot_again: '>> BOOT AGAIN << [SPACE]',
	btn_return_rig_select: 'RETURN TO RIG SELECT',
	btn_return_rig_select_mini: 'RIG SELECT',
	label_round_id: 'round id: {id}',
	status_settling: 'settling round...',

	// —— Rules ——
	a11y_rules: 'game rules',
	rules_title: '// GAME RULES',
	rules_how_to_play: 'HOW TO PLAY',
	rules_howto_body:
		'set your auto {cashOut} target and your {stake}, then boot the rig. the rig climbs on its own and stops at your target automatically -- there is no action to take during the round. if it melts down before the target, you keep only what the checkpoints locked along the way.',
	rules_controls:
		'controls: pick a rig with the slider or the - / + buttons (that sets the {cashOut} target), set the {stake} with - / + or Min / 1/2 / 2x / Max, then press BOOT RIG. on desktop, SPACE boots. results settle automatically; BOOT AGAIN repeats the same round.',
	rules_modes: 'MODES',
	rules_modes_intro:
		'{modeCosts} the {stake} you set{noCostNote}. "{pays} something" is the chance a round returns any {payout} at all.',
	rules_no_cost_multipliers: ' (no cost multipliers)',
	rules_th_rig: 'rig',
	rules_th_cashout_target: '{cashOut} target',
	rules_th_max_win: 'max win',
	rules_th_pays_something: '{pays} something',
	rules_th_checkpoints: 'checkpoints',
	rules_th_cost: '{costAt} {stake}',
	rules_payouts_body:
		'each rig has a ladder of checkpoints below its target. as the rig climbs, every checkpoint it crosses locks a partial {payout} that is kept even if the rig melts down afterwards. reaching the target {pays} the shutdown multiplier the rig actually reached times your {stake} -- on a clean hit that is the target itself.',
	rules_overdrive:
		'OVERDRIVE: on a share of winning rounds the thermal limiter slips past the target. the round still {pays} the multiplier the rig reached at shutdown (the number on the result), not a flat 1.5x / 3x / 10x of the target. those figures are tier bands for how far past the target the run went (overdrive / critical / golden) -- labels only, not the payout formula. overdrive is decided by the round outcome; it needs no input and cannot be triggered manually.',
	rules_max_win_intro:
		'each mode has its own maximum win (up to Nx your {stake}), including overdrive tops. {payouts} never exceed that mode cap. see the max win column below.',
	rules_max_win_note:
		'maximum win is per mode and includes the highest overdrive payout that mode can reach -- see the modes table. {payouts} are capped at that mode\'s max win.',
	rules_rtp_heading: 'RTP',
	rules_rtp_body:
		'the return to player (RTP) is {percent}% on every mode and every {cashOut} target -- the same figure for idle through plasma.',
	rules_disclaimer_heading: 'DISCLAIMER',
	rules_disclaimer:
		'Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser. TM and © 2026 Stake Engine.',
	rules_social_entertainment: 'This game is provided for entertainment purposes only.',
	btn_close: 'CLOSE',

	// —— Errors ——
	error_system_fault: '!! SYSTEM FAULT {code}',
	err_val: 'request rejected: invalid parameters',
	err_ipb: 'insufficient power reserve (balance too low)',
	err_is: 'session invalid or expired -- relaunch the game',
	err_ate: 'authentication token expired -- relaunch the game',
	err_gle: '{gambling} limits exceeded',
	err_loc: 'play not permitted from this location',
	err_be: 'a round is already active on this session',
	err_gen: 'server fault -- try again',
	err_maintenance: 'engine down for maintenance -- try again later',
	err_unexpected: 'unexpected fault -- check console for details',
	btn_acknowledge: 'ACKNOWLEDGE',

	auth_failed_banner: '!! AUTHENTICATION FAILED',
	auth_failed_body: 'Authentication failed. Cannot start game.',
	auth_rgs_rejected: '> rgs handshake rejected -- reload with a valid session to continue',

	// —— Turbo / loader ——
	turbo_tooltip: 'turbo: faster reveal, same odds',
	turbo_on: 'TURBO [ON]',
	turbo_off: 'TURBO [OFF]',
	a11y_loading: 'loading',
	boot_bios: 'OVERHEAT THERMAL BIOS v2.0',
	boot_post: 'POST........................ OK',
	boot_cooling: 'checking cooling loop....... OK',
	boot_rig_array: 'spinning up rig array....... OK',
	boot_rgs: 'RGS handshake...............',

	// —— SYS LOG ——
	log_power_contacting: '> POWER ON -- contacting RGS...',
	log_power_rig: '> POWER ON -- RIG: {rig}',
	log_bios_ok: '> BIOS OK .. volt rails nominal',
	log_hashrate: '> hashrate online: {hashrate} MH/s',
	log_shutdown_locked: '> shutdown temp locked: {mult}x',
	log_mining: '> mining...',
} as const;

export type MessageKey = keyof typeof en;
export default en;
