/**
 * Overheat Spanish locale.
 * Keys match en.ts. Placeholders and brand/units stay as-is.
 */
const es = {
	// —— Brand / chrome (brand stays OVERHEAT) ——
	brand_overheat: 'OVERHEAT',
	hdr_console_full: 'OVERHEAT // CONSOLA TÉRMICA DE RIG DE MINERÍA',
	hdr_console_sub: 'CONSOLA TÉRMICA DE RIG DE MINERÍA',
	btn_rules: '[REGLAS]',
	hdr_session: 'SESIÓN {time}',
	hdr_rtp: 'RTP {percent}%',
	hdr_replay: 'REPLAY -- REPRODUCCIÓN DE RONDA',
	hdr_pwr_reserve: 'RESERVA ENERGÍA:',
	hdr_net: 'NETO {amount}',
	hdr_turbo: ' [TURBO]',
	status_loading_replay: 'cargando replay...',

	// —— Social / standard lexicon ——
	word_stake: 'apuesta',
	word_stake_social: 'importe de juego',
	label_stake: 'APUESTA',
	label_stake_social: 'IMPORTE DE JUEGO',
	word_cash_out: 'cobrar',
	word_cash_out_social: 'recoger',
	label_cash_out_target: 'OBJETIVO DE COBRO',
	label_cash_out_target_social: 'OBJETIVO DE RECOGIDA',
	word_pays: 'paga',
	word_pays_social: 'gana',
	word_pay: 'pagar',
	word_pay_social: 'ganar',
	word_payout: 'pago',
	word_payout_social: 'premio',
	label_payouts: 'PAGOS',
	label_payouts_social: 'PREMIOS',
	word_gambling: 'juego',
	word_gambling_social: 'juego',
	label_cost_at: 'coste al actual',
	label_cost_at_social: 'se puede jugar por al actual',
	phrase_mode_costs: 'cada modo cuesta exactamente',
	phrase_mode_costs_social: 'cada modo se puede jugar por exactamente',
	word_payouts_plural: 'pagos',
	word_payouts_plural_social: 'premios',

	// —— Rig select / how it works ——
	loop_title: '// CÓMO FUNCIONA',
	loop_body_first:
		'fija tu objetivo auto de {cashOut}. arranca el rig. sube solo y se detiene ahí automáticamente. {meltdownClause}',
	loop_body_return:
		'> fija tu objetivo auto de {cashOut} -- el rig sube solo y se detiene ahí automáticamente. {meltdownClause}',
	loop_melt_keep_checkpoints:
		'si se funde antes, solo conservas lo que los checkpoints hayan bancado.',
	loop_melt_lose_stake: 'si se funde antes, pierdes la {stake}.',
	stat_hottest: 'MÁS CALIENTE',
	stat_hottest_value: '{mult}x',
	stat_best_bank: 'MEJOR BANCO',
	stat_hottest_empty: 'MÁS CALIENTE --',
	dial_translate: '{cashOut} a {mult}x',
	a11y_shutdown_temp: 'temperatura de apagado',
	dial_scale_safe: 'seguro',
	dial_scale_spicy: 'picante',
	dial_pays_something: '{pays} algo: {percent}% de rondas',
	label_stake_row: '{stake}:',
	dial_full_send: 'envío total {pays} {winPays}, hasta {maxPays} en overdrive',
	btn_boot_rig: '>> ARRANCAR RIG <<',
	warn_insufficient_pwr: 'reserva de energía insuficiente -- baja la {stake}',
	hint_space_boot: '[ESPACIO] para arrancar',
	settings_sound: 'sonido',
	settings_scanlines: 'líneas de barrido',
	settings_flicker: 'parpadeo',
	btn_fairness: '[EQUIDAD]',
	a11y_settings: 'ajustes de pantalla y sonido',

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
	flavor_idle: 'apenas tibio. básicamente una cuenta de ahorro.',
	flavor_eco: 'subvoltado. aburrido. paga el alquiler.',
	flavor_eco_social: 'subvoltado. aburrido. gana el alquiler.',
	flavor_standard: 'cooler de fábrica, nervios de fábrica.',
	flavor_boost: 'overclock de fábrica. sudor leve.',
	flavor_overclock: 'garantía anulada. pasta térmica opcional.',
	flavor_nitro: 'ventiladores aftermarket, gritando.',
	flavor_furnace: 'calienta la habitación. a veces la casa.',
	flavor_inferno: 'el detector de humo está desenchufado.',
	flavor_meltdown: 'ruleta de silicio. trae una manta ignífuga.',
	flavor_reactor: 'fisión sin licencia. no se lo digas a nadie.',
	flavor_plasma: 'esto no es minería. esto es una estrella.',

	// —— Checkpoint profiles (rules table) ——
	profile_drip: 'frecuentes, pequeños',
	profile_balanced: 'estables',
	profile_spike: 'raros, grandes',

	// —— Run view ——
	run_topline: 'RIG: {rig} | {stakeLabel}: {amount}',
	col_sys_log: '// SYS LOG',
	label_core_temp: 'TEMP NÚCLEO',
	tag_limiter_slipped: '!! LIMITADOR FALLÓ -- OVERDRIVE !!',
	run_cashout_at: '{cashOut} @ {mult}x',
	label_secured_yield: 'RENDIMIENTO ASEGURADO',
	yield_next_lock: 'próximo lock @ {nextMult}x → {bankMult}x',
	yield_all_locked: 'todos los checkpoints bloqueados -- empuja al objetivo',
	col_checkpoints: '// CHECKPOINTS',
	ladder_full: 'FULL {mult}x',

	result_meltdown: '** FUSIÓN @ {mult}x **',
	result_near_miss: 'murió a {delta}x del checkpoint {checkpoint}x',
	result_aimed_for: 'apuntó a {mult}x',
	result_checkpoints_held: '>> CHECKPOINTS RETENIDOS: +{amount} asegurado',

	win_headline_clean: 'APAGADO LIMPIO',
	win_headline_overdrive: 'LIMITADOR TÉRMICO FALLÓ -- OBJETIVO 1.5x',
	win_headline_critical: 'BREAKER GOLPEADO -- OBJETIVO 3x',
	win_headline_golden: 'EL SILICIO ASCENDIÓ -- OBJETIVO 10x',
	win_label_golden: 'APAGADO DORADO',
	win_label_legendary: 'RONDA LEGENDARIA',
	win_label_massive: 'BANCO MASIVO',
	win_label_huge: 'BANCO ENORME',
	win_label_big: 'GRAN BANCO',
	win_label_clean: 'BANCO LIMPIO',
	win_banner: '>>> {label} <<<',
	win_bonus_mult: 'multiplicador bonus {mult}x sobre tu {payout}',
	win_peaked: 'corrido limpio -- pico en {mult}x',
	win_survived: '{mult}x sobrevivido',
	badge_personal_best: '★ NUEVO RÉCORD PERSONAL ★',
	badge_personal_best_run: '★ NUEVA MEJOR RONDA PERSONAL ★',

	btn_replay_again: '>> REPRODUCIR OTRA VEZ <<',
	btn_boot_again: '>> ARRANCAR OTRA VEZ << [ESPACIO]',
	btn_return_rig_select: 'VOLVER A SELECCIÓN DE RIG',
	btn_return_rig_select_mini: 'SELECCIÓN RIG',
	label_round_id: 'id de ronda: {id}',
	status_settling: 'liquidando ronda...',

	// —— Rules ——
	a11y_rules: 'reglas del juego',
	rules_title: '// REGLAS DEL JUEGO',
	rules_how_to_play: 'CÓMO JUGAR',
	rules_howto_body:
		'fija tu objetivo auto de {cashOut} y tu {stake}, luego arranca el rig. el rig sube solo y se detiene en tu objetivo automáticamente -- no hay acción que tomar durante la ronda. si se funde antes del objetivo, solo conservas lo que los checkpoints hayan bancado por el camino.',
	rules_controls:
		'controles: elige un rig con el slider o los botones - / + (eso fija el objetivo de {cashOut}), ajusta la {stake} con - / + o Min / 1/2 / 2x / Max, luego pulsa ARRANCAR RIG. en escritorio, ESPACIO arranca. los resultados se liquidan solos; ARRANCAR OTRA VEZ repite la misma ronda.',
	rules_modes: 'MODOS',
	rules_modes_intro:
		'{modeCosts} la {stake} que fijes{noCostNote}. "{pays} algo" es la probabilidad de que una ronda devuelva algún {payout}.',
	rules_no_cost_multipliers: ' (sin multiplicadores de coste)',
	rules_th_rig: 'rig',
	rules_th_cashout_target: 'objetivo de {cashOut}',
	rules_th_pays_something: '{pays} algo',
	rules_th_checkpoints: 'checkpoints',
	rules_th_cost: '{costAt} {stake}',
	rules_payouts_body:
		'cada rig tiene una escalera de checkpoints por debajo de su objetivo. al subir, cada checkpoint que cruza banca un {payout} parcial que se conserva aunque el rig se funda después. alcanzar el objetivo {pays} el multiplicador completo del objetivo por tu {stake}.',
	rules_overdrive:
		'OVERDRIVE: en una pequeña parte de las rondas ganadoras el limitador térmico se pasa del objetivo y la ronda {pays} un multiplicador bonus al apagar -- 1.5x el objetivo (overdrive), 3x el objetivo (critical), o 10x el objetivo (apagado dorado). el overdrive lo decide el resultado de la ronda; no requiere input y no se puede activar manualmente.',
	rules_max_win:
		'premio máximo: {maxWin}x la {stake} (un pago tope en {mode}). los {payouts} están limitados al premio máximo.',
	rules_rtp_heading: 'RTP',
	rules_rtp_body:
		'el retorno al jugador es {percent}% en cada modo y cada objetivo de {cashOut}.',
	rules_disclaimer_heading: 'AVISO',
	rules_disclaimer:
		'Un fallo anula todos los premios y jugadas. Se requiere una conexión a internet estable. En caso de desconexión, recarga el juego para terminar cualquier ronda incompleta. El retorno esperado se calcula sobre muchas jugadas. La pantalla del juego no representa ningún dispositivo físico y es solo ilustrativa. Los premios se liquidan según el importe recibido del Remote Game Server y no por eventos dentro del navegador. TM y © 2026 Stake Engine.',
	rules_social_entertainment: 'Este juego se ofrece solo con fines de entretenimiento.',
	btn_close: 'CERRAR',

	// —— Fairness ——
	a11y_fairness: 'detalles de equidad demostrable',
	fairness_title: '// EQUIDAD DEMOSTRABLE',
	fairness_rtp: '{percent}% -- cada rig',
	fairness_last_round: 'ID DE ÚLTIMA RONDA',
	fairness_body:
		'cada resultado se extrae de una tabla de resultados precargada y sellada, y se liquida en el servidor por el Stake Engine RGS antes de que se anime la revelación. la revelación no puede cambiar el resultado. cita un id de ronda al operador para auditar cualquier ronda liquidada.',

	// —— Errors ——
	error_system_fault: '!! FALLO DE SISTEMA {code}',
	err_val: 'solicitud rechazada: parámetros inválidos',
	err_ipb: 'reserva de energía insuficiente (saldo demasiado bajo)',
	err_is: 'sesión inválida o caducada -- relanza el juego',
	err_ate: 'token de autenticación caducado -- relanza el juego',
	err_gle: 'límites de {gambling} excedidos',
	err_loc: 'juego no permitido desde esta ubicación',
	err_be: 'ya hay una ronda activa en esta sesión',
	err_gen: 'fallo del servidor -- inténtalo de nuevo',
	err_maintenance: 'motor en mantenimiento -- inténtalo más tarde',
	err_unexpected: 'fallo inesperado -- revisa la consola para detalles',
	btn_acknowledge: 'ACEPTAR',

	auth_failed_banner: '!! AUTENTICACIÓN FALLIDA',
	auth_failed_body: 'Autenticación fallida. No se puede iniciar el juego.',
	auth_rgs_rejected: '> handshake RGS rechazado -- recarga con una sesión válida para continuar',

	// —— Turbo / loader ——
	turbo_tooltip: 'turbo: revelación más rápida, mismas probabilidades',
	turbo_on: 'TURBO [ACTIVADO]',
	turbo_off: 'TURBO [DESACTIVADO]',
	a11y_loading: 'cargando',
	boot_bios: 'OVERHEAT THERMAL BIOS v2.0',
	boot_post: 'POST........................ OK',
	boot_cooling: 'comprobando bucle de refrigeración....... OK',
	boot_rig_array: 'arrancando array de rigs....... OK',
	boot_rgs: 'RGS handshake...............',

	// —— SYS LOG ——
	log_power_contacting: '> POWER ON -- contactando RGS...',
	log_power_rig: '> POWER ON -- RIG: {rig}',
	log_bios_ok: '> BIOS OK .. rails de voltaje nominales',
	log_hashrate: '> hashrate online: {hashrate} MH/s',
	log_shutdown_locked: '> temp de apagado bloqueada: {mult}x',
	log_mining: '> minando...',
} as const;

export default es;
