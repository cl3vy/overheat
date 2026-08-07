/**
 * Overheat Portuguese (Brazilian-friendly) locale.
 * Keys match en.ts. Placeholders and brand/units stay as-is.
 */
const pt = {
	// —— Brand / chrome (brand stays OVERHEAT) ——
	brand_overheat: 'OVERHEAT',
	hdr_console_full: 'OVERHEAT // CONSOLE TÉRMICO DE RIG DE MINERAÇÃO',
	hdr_console_sub: 'CONSOLE TÉRMICO DE RIG DE MINERAÇÃO',
	btn_rules: '[REGRAS]',
	hdr_session: 'SESSÃO {time}',
	hdr_rtp: 'RTP {percent}%',
	hdr_replay: 'REPLAY -- REPRODUÇÃO DA RODADA',
	hdr_pwr_reserve: 'RESERVA DE ENERGIA:',
	hdr_net: 'LÍQ {amount}',
	hdr_turbo: ' [TURBO]',
	status_loading_replay: 'carregando replay...',
	replay_summary_title: '// RESUMO DO REPLAY',
	replay_summary_note:
		'isto é a reprodução de uma rodada anterior. nenhuma aposta real é feita.',
	replay_row_mode: 'Modo',
	replay_row_base_bet: 'Aposta base',
	replay_row_cost_mult: 'Multiplicador de custo',
	replay_row_total_bet: 'Custo total da aposta',
	replay_row_payout_mult: 'Multiplicador de pagamento',
	replay_row_total_win: 'Ganho total',
	btn_start_replay: '>> INICIAR REPLAY <<',
	a11y_replay_summary: 'resumo da aposta do replay',

	// —— Social / standard lexicon ——
	word_stake: 'aposta',
	word_stake_social: 'valor de jogo',
	label_stake: 'APOSTA',
	label_stake_social: 'VALOR DE JOGO',
	word_cash_out: 'sacar',
	word_cash_out_social: 'coletar',
	label_cash_out_target: 'ALVO DE SAQUE',
	label_cash_out_target_social: 'ALVO DE COLETA',
	word_pays: 'paga',
	word_pays_social: 'ganha',
	word_pay: 'pagar',
	word_pay_social: 'ganhar',
	word_payout: 'pagamento',
	word_payout_social: 'prêmio',
	label_payouts: 'PAGAMENTOS',
	label_payouts_social: 'PRÊMIOS',
	word_gambling: 'jogo',
	word_gambling_social: 'jogo',
	label_cost_at: 'custo no atual',
	label_cost_at_social: 'pode ser jogado por no atual',
	phrase_mode_costs: 'cada modo custa exatamente',
	phrase_mode_costs_social: 'cada modo pode ser jogado por exatamente',
	word_payouts_plural: 'pagamentos',
	word_payouts_plural_social: 'prêmios',

	// —— Rig select / how it works ——
	loop_title: '// COMO FUNCIONA',
	loop_body_first:
		'defina seu alvo auto de {cashOut}. ligue o rig. ele sobe sozinho e para lá automaticamente. {meltdownClause}',
	loop_body_return:
		'> defina seu alvo auto de {cashOut} -- o rig sobe sozinho e para lá automaticamente. {meltdownClause}',
	loop_melt_keep_checkpoints:
		'se der meltdown antes, você fica só com o que os checkpoints bancaram.',
	loop_melt_lose_stake: 'se der meltdown antes, você perde a {stake}.',
	stat_hottest: 'MAIS QUENTE',
	stat_hottest_value: '{mult}x',
	stat_best_bank: 'MELHOR BANCO',
	stat_hottest_empty: 'MAIS QUENTE --',
	dial_translate: '{cashOut} a {mult}x',
	a11y_shutdown_temp: 'temperatura de desligamento',
	dial_scale_safe: 'seguro',
	dial_scale_spicy: 'picante',
	dial_pays_something: '{pays} algo: {percent}% das rodadas',
	label_stake_row: '{stake}:',
	dial_full_send: 'envio total {pays} {winPays}, até {maxPays} no overdrive',
	btn_boot_rig: '>> LIGAR RIG <<',
	warn_insufficient_pwr: 'reserva de energia insuficiente -- diminua a {stake}',
	hint_space_boot: '[ESPAÇO] para ligar',
	settings_sound: 'som',
	settings_scanlines: 'scanlines',
	settings_flicker: 'flicker',
	a11y_settings: 'ajustes de tela e som',

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
	flavor_idle: 'quase morno. basicamente uma poupança.',
	flavor_eco: 'undervoltado. chato. paga o aluguel.',
	flavor_eco_social: 'undervoltado. chato. ganha o aluguel.',
	flavor_standard: 'cooler de fábrica, nervos de fábrica.',
	flavor_boost: 'overclock de fábrica. suor leve.',
	flavor_overclock: 'garantia anulada. pasta térmica opcional.',
	flavor_nitro: 'fans aftermarket, gritando.',
	flavor_furnace: 'esquenta o quarto. às vezes a casa.',
	flavor_inferno: 'o detector de fumaça está desligado.',
	flavor_meltdown: 'roleta de silício. traga um cobertor anti-fogo.',
	flavor_reactor: 'fissão sem licença. não conte pra ninguém.',
	flavor_plasma: 'isso não é mineração. isso é uma estrela.',

	// —— Checkpoint profiles (rules table) ——
	profile_drip: 'frequentes, pequenos',
	profile_balanced: 'estáveis',
	profile_spike: 'raros, grandes',

	// —— Run view ——
	run_topline: 'RIG: {rig} | {stakeLabel}: {amount}',
	col_sys_log: '// SYS LOG',
	label_core_temp: 'TEMP NÚCLEO',
	tag_limiter_slipped: '!! LIMITADOR FALHOU -- OVERDRIVE !!',
	run_cashout_at: '{cashOut} @ {mult}x',
	label_secured_yield: 'RENDIMENTO GARANTIDO',
	yield_next_lock: 'próximo lock @ {nextMult}x → {bankMult}x',
	yield_all_locked: 'todos os checkpoints travados -- empurre pro alvo',
	col_checkpoints: '// CHECKPOINTS',
	ladder_full: 'FULL {mult}x',

	result_meltdown: '** MELTDOWN @ {mult}x **',
	result_near_miss: 'morreu a {delta}x do checkpoint {checkpoint}x',
	result_aimed_for: 'mirava {mult}x',
	result_checkpoints_held: '>> CHECKPOINTS RETIDOS: +{amount} garantido',

	win_headline_clean: 'DESLIGAMENTO LIMPO',
	win_headline_overdrive: 'LIMITADOR TÉRMICO FALHOU -- FAIXA OVERDRIVE',
	win_headline_critical: 'BREAKER BATEU -- FAIXA CRITICAL',
	win_headline_golden: 'O SILÍCIO ASCENDEU -- FAIXA GOLDEN',
	win_label_golden: 'DESLIGAMENTO DOURADO',
	win_label_legendary: 'RODADA LENDÁRIA',
	win_label_massive: 'BANCO MASSIVO',
	win_label_huge: 'BANCO ENORME',
	win_label_big: 'GRANDE BANCO',
	win_label_clean: 'BANCO LIMPO',
	win_banner: '>>> {label} <<<',
	win_tier_note:
		'só rótulo de faixa -- a rodada {pays} o desligamento de {mult}x alcançado, não um múltiplo fixo do seu alvo',
	win_peaked: 'rodada limpa -- pico em {mult}x',
	win_survived: '{mult}x sobrevivido',
	badge_personal_best: '★ NOVO RECORDE PESSOAL ★',
	badge_personal_best_run: '★ NOVA MELHOR RODADA PESSOAL ★',

	btn_replay_again: '>> REPRODUZIR DE NOVO <<',
	btn_boot_again: '>> LIGAR DE NOVO << [ESPAÇO]',
	btn_return_rig_select: 'VOLTAR À SELEÇÃO DE RIG',
	btn_return_rig_select_mini: 'SELEÇÃO RIG',
	label_round_id: 'id da rodada: {id}',
	status_settling: 'liquidando rodada...',

	// —— Rules ——
	a11y_rules: 'regras do jogo',
	rules_title: '// REGRAS DO JOGO',
	rules_how_to_play: 'COMO JOGAR',
	rules_howto_body:
		'defina seu alvo auto de {cashOut} e sua {stake}, depois ligue o rig. o rig sobe sozinho e para no seu alvo automaticamente -- não há ação a tomar durante a rodada. se der meltdown antes do alvo, você fica só com o que os checkpoints bancaram no caminho.',
	rules_controls:
		'controles: escolha um rig com o slider ou os botões - / + (isso define o alvo de {cashOut}), ajuste a {stake} com - / + ou Min / 1/2 / 2x / Max, depois pressione LIGAR RIG. no desktop, ESPAÇO liga. os resultados liquidam sozinhos; LIGAR DE NOVO repete a mesma rodada.',
	rules_modes: 'MODOS',
	rules_modes_intro:
		'{modeCosts} a {stake} que você definir{noCostNote}. "{pays} algo" é a chance de uma rodada devolver algum {payout}.',
	rules_no_cost_multipliers: ' (sem multiplicadores de custo)',
	rules_th_rig: 'rig',
	rules_th_cashout_target: 'alvo de {cashOut}',
	rules_th_max_win: 'vitória máx.',
	rules_th_pays_something: '{pays} algo',
	rules_th_checkpoints: 'checkpoints',
	rules_th_cost: '{costAt} {stake}',
	rules_payouts_body:
		'cada rig tem uma escada de checkpoints abaixo do alvo. conforme sobe, cada checkpoint cruzado banca um {payout} parcial que fica mesmo se o rig der meltdown depois. atingir o alvo {pays} o multiplicador de desligamento que o rig realmente alcançou vezes sua {stake} -- num acerto limpo, isso é o próprio alvo.',
	rules_overdrive:
		'OVERDRIVE: em parte das rodadas vencedoras o limitador térmico passa do alvo. a rodada ainda {pays} o multiplicador que o rig alcançou no desligamento (o número do resultado), não um 1.5x / 3x / 10x fixo do alvo. esses números são faixas de quão longe passou do alvo (overdrive / critical / golden) -- só rótulos, não a fórmula do pagamento. o overdrive é decidido pelo resultado da rodada; não precisa de input e não pode ser ativado manualmente.',
	rules_max_win_intro:
		'cada modo tem sua própria vitória máxima (até Nx sua {stake}), incluindo os topos de overdrive. os {payouts} nunca passam desse teto. veja a coluna de vitória máx. abaixo.',
	rules_max_win_note:
		'a vitória máxima é por modo e inclui o overdrive mais alto que esse modo pode alcançar -- veja a tabela de modos. os {payouts} são limitados à vitória máxima desse modo.',
	rules_rtp_heading: 'RTP',
	rules_rtp_body:
		'o retorno ao jogador (RTP) é {percent}% em cada modo e cada alvo de {cashOut} -- o mesmo valor de idle a plasma.',
	rules_disclaimer_heading: 'AVISO',
	rules_disclaimer:
		'Malfuncionamento anula todos os prêmios e jogadas. É necessária uma conexão de internet estável. Em caso de desconexão, recarregue o jogo para concluir rodadas incompletas. O retorno esperado é calculado sobre muitas jogadas. A tela do jogo não representa nenhum dispositivo físico e é apenas ilustrativa. Os prêmios são liquidados conforme o valor recebido do Remote Game Server e não por eventos no navegador. TM e © 2026 Stake Engine.',
	rules_social_entertainment: 'Este jogo é fornecido apenas para fins de entretenimento.',
	btn_close: 'FECHAR',

	// —— Errors ——
	error_system_fault: '!! FALHA DE SISTEMA {code}',
	err_val: 'solicitação rejeitada: parâmetros inválidos',
	err_ipb: 'reserva de energia insuficiente (saldo muito baixo)',
	err_is: 'sessão inválida ou expirada -- reinicie o jogo',
	err_ate: 'token de autenticação expirado -- reinicie o jogo',
	err_gle: 'limites de {gambling} excedidos',
	err_loc: 'jogo não permitido neste local',
	err_be: 'já há uma rodada ativa nesta sessão',
	err_gen: 'falha do servidor -- tente de novo',
	err_maintenance: 'motor em manutenção -- tente mais tarde',
	err_unexpected: 'falha inesperada -- confira o console para detalhes',
	btn_acknowledge: 'RECONHECER',

	auth_failed_banner: '!! AUTENTICAÇÃO FALHOU',
	auth_failed_body: 'Autenticação falhou. Não é possível iniciar o jogo.',
	auth_rgs_rejected: '> handshake RGS rejeitado -- recarregue com uma sessão válida para continuar',

	// —— Turbo / loader ——
	turbo_tooltip: 'turbo: revelação mais rápida, mesmas chances',
	turbo_on: 'TURBO [LIGADO]',
	turbo_off: 'TURBO [DESLIGADO]',
	a11y_loading: 'carregando',
	boot_bios: 'OVERHEAT THERMAL BIOS v2.0',
	boot_post: 'POST........................ OK',
	boot_cooling: 'verificando loop de refrigeração....... OK',
	boot_rig_array: 'iniciando array de rigs....... OK',
	boot_rgs: 'RGS handshake...............',

	// —— SYS LOG ——
	log_power_contacting: '> POWER ON -- contactando RGS...',
	log_power_rig: '> POWER ON -- RIG: {rig}',
	log_bios_ok: '> BIOS OK .. trilhos de tensão nominais',
	log_hashrate: '> hashrate online: {hashrate} MH/s',
	log_shutdown_locked: '> temp de desligamento travada: {mult}x',
	log_mining: '> minerando...',
} as const;

export default pt;
