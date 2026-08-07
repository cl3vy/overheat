/**
 * Overheat Simplified Chinese locale.
 * Keys match en.ts. Placeholders and brand/units stay as-is.
 */
const zh = {
	// —— Brand / chrome (brand stays OVERHEAT) ——
	brand_overheat: 'OVERHEAT',
	hdr_console_full: 'OVERHEAT // 矿机热控台',
	hdr_console_sub: '矿机热控台',
	btn_rules: '[规则]',
	hdr_session: '会话 {time}',
	hdr_rtp: 'RTP {percent}%',
	hdr_replay: 'REPLAY -- 回合回放',
	hdr_pwr_reserve: '电力储备:',
	hdr_net: '净值 {amount}',
	hdr_turbo: ' [TURBO]',
	status_loading_replay: '正在加载回放...',

	// —— Social / standard lexicon ——
	word_stake: '下注',
	word_stake_social: '游戏金额',
	label_stake: '下注',
	label_stake_social: '游戏金额',
	word_cash_out: '兑现',
	word_cash_out_social: '收取',
	label_cash_out_target: '兑现目标',
	label_cash_out_target_social: '收取目标',
	word_pays: '赔付',
	word_pays_social: '赢得',
	word_pay: '赔付',
	word_pay_social: '赢得',
	word_payout: '派彩',
	word_payout_social: '奖金',
	label_payouts: '派彩',
	label_payouts_social: '奖金',
	word_gambling: '博彩',
	word_gambling_social: '游戏',
	label_cost_at: '当前成本',
	label_cost_at_social: '当前可玩金额为',
	phrase_mode_costs: '每种模式费用正好为',
	phrase_mode_costs_social: '每种模式正好可用此金额游玩',
	word_payouts_plural: '派彩',
	word_payouts_plural_social: '奖金',

	// —— Rig select / how it works ——
	loop_title: '// 玩法说明',
	loop_body_first:
		'设定自动{cashOut}目标。启动矿机。它自行爬升并在该处自动停下。{meltdownClause}',
	loop_body_return:
		'> 设定自动{cashOut}目标 -- 矿机自行爬升并在该处自动停下。{meltdownClause}',
	loop_melt_keep_checkpoints:
		'若先熔毁，你只保留检查点已存入的部分。',
	loop_melt_lose_stake: '若先熔毁，你失去{stake}。',
	stat_hottest: '最高温',
	stat_hottest_value: '{mult}x',
	stat_best_bank: '最佳银行',
	stat_hottest_empty: '最高温 --',
	dial_translate: '{cashOut} @ {mult}x',
	a11y_shutdown_temp: '关断温度',
	dial_scale_safe: '安全',
	dial_scale_spicy: '危险',
	dial_pays_something: '{pays}有回报: {percent}% 的回合',
	label_stake_row: '{stake}:',
	dial_full_send: '全力冲刺 {pays} {winPays}，过驱最高 {maxPays}',
	btn_boot_rig: '>> 启动矿机 <<',
	warn_insufficient_pwr: '电力储备不足 -- 请降低{stake}',
	hint_space_boot: '[空格] 启动',
	settings_sound: '声音',
	settings_scanlines: '扫描线',
	settings_flicker: '闪烁',
	a11y_settings: '显示与声音设置',

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
	flavor_idle: '勉强温热。基本是个存折。',
	flavor_eco: '降压运行。无聊。能付房租。',
	flavor_eco_social: '降压运行。无聊。能赢房租。',
	flavor_standard: '原装散热，原装胆量。',
	flavor_boost: '出厂超频。微微出汗。',
	flavor_overclock: '保修作废。导热膏随意。',
	flavor_nitro: '改装风扇，在尖叫。',
	flavor_furnace: '能暖房。有时能暖整栋楼。',
	flavor_inferno: '烟雾报警器已拔掉。',
	flavor_meltdown: '硅片轮盘。带上防火毯。',
	flavor_reactor: '无证裂变。别告诉任何人。',
	flavor_plasma: '这不是挖矿。这是一颗星。',

	// —— Checkpoint profiles (rules table) ——
	profile_drip: '频繁、小额',
	profile_balanced: '稳定',
	profile_spike: '稀少、大额',

	// —— Run view ——
	run_topline: 'RIG: {rig} | {stakeLabel}: {amount}',
	col_sys_log: '// SYS LOG',
	label_core_temp: '核心温度',
	tag_limiter_slipped: '!! 限幅器失效 -- OVERDRIVE !!',
	run_cashout_at: '{cashOut} @ {mult}x',
	label_secured_yield: '已锁定收益',
	yield_next_lock: '下一锁定 @ {nextMult}x → {bankMult}x',
	yield_all_locked: '全部检查点已锁定 -- 冲向目标',
	col_checkpoints: '// CHECKPOINTS',
	ladder_full: 'FULL {mult}x',

	result_meltdown: '** 熔毁 @ {mult}x **',
	result_near_miss: '距 {checkpoint}x 检查点还差 {delta}x 就挂了',
	result_aimed_for: '目标 {mult}x',
	result_checkpoints_held: '>> 检查点保留: +{amount} 已锁定',

	win_headline_clean: '干净关断',
	win_headline_overdrive: '热限幅器失效 -- 目标 1.5x',
	win_headline_critical: '断路器砸下 -- 目标 3x',
	win_headline_golden: '硅片飞升 -- 目标 10x',
	win_label_golden: '黄金关断',
	win_label_legendary: '传奇回合',
	win_label_massive: '巨额银行',
	win_label_huge: '超大银行',
	win_label_big: '大银行',
	win_label_clean: '干净银行',
	win_banner: '>>> {label} <<<',
	win_bonus_mult: '你的{payout}获得 {mult}x 奖励倍率',
	win_peaked: '干净完跑 -- 峰值 {mult}x',
	win_survived: '{mult}x 存活',
	badge_personal_best: '★ 新个人纪录 ★',
	badge_personal_best_run: '★ 新个人最佳回合 ★',

	btn_replay_again: '>> 再次回放 <<',
	btn_boot_again: '>> 再次启动 << [空格]',
	btn_return_rig_select: '返回矿机选择',
	btn_return_rig_select_mini: '矿机选择',
	label_round_id: '回合 id: {id}',
	status_settling: '正在结算回合...',

	// —— Rules ——
	a11y_rules: '游戏规则',
	rules_title: '// 游戏规则',
	rules_how_to_play: '如何游玩',
	rules_howto_body:
		'设定自动{cashOut}目标和{stake}，然后启动矿机。矿机自行爬升并在目标处自动停下 -- 回合中无需操作。若在目标前熔毁，你只保留沿途检查点已存入的部分。',
	rules_controls:
		'操作：用滑块或 - / + 按钮选择矿机（设定{cashOut}目标），用 - / + 或 Min / 1/2 / 2x / Max 设定{stake}，然后按启动矿机。桌面端按空格启动。结果自动结算；再次启动重复同一回合。',
	rules_modes: '模式',
	rules_modes_intro:
		'{modeCosts}你设定的{stake}{noCostNote}。“{pays}有回报”是回合有任何{payout}的概率。',
	rules_no_cost_multipliers: '（无成本倍率）',
	rules_th_rig: 'rig',
	rules_th_cashout_target: '{cashOut}目标',
	rules_th_pays_something: '{pays}有回报',
	rules_th_checkpoints: '检查点',
	rules_th_cost: '{costAt} {stake}',
	rules_payouts_body:
		'每台矿机在目标下方有检查点阶梯。爬升时每越过一个检查点就存入部分{payout}，之后即使熔毁也会保留。到达目标时{pays}完整目标倍率乘以你的{stake}。',
	rules_overdrive:
		'OVERDRIVE：少数获胜回合中热限幅器会越过目标，关断时{pays}奖励倍率 -- 目标的 1.5x（overdrive）、3x（critical）或 10x（黄金关断）。过驱由回合结果决定；无需输入，也无法手动触发。',
	rules_max_win:
		'最高赢额：{stake}的 {maxWin}x（{mode}的顶级派彩）。{payouts}上限为最高赢额。',
	rules_rtp_heading: 'RTP',
	rules_rtp_body:
		'每种模式和每个{cashOut}目标的玩家返还率为 {percent}%。',
	rules_disclaimer_heading: '免责声明',
	rules_disclaimer:
		'故障将使所有赢取和游玩无效。需要稳定的互联网连接。若断线，请重新加载游戏以完成任何未完成的回合。预期返还按多次游玩计算。游戏画面不代表任何实体设备，仅供说明。赢取金额按远程游戏服务器（Remote Game Server）返回的金额结算，而非浏览器内事件。TM and © 2026 Stake Engine.',
	rules_social_entertainment: '本游戏仅供娱乐。',
	btn_close: '关闭',

	// —— Errors ——
	error_system_fault: '!! 系统故障 {code}',
	err_val: '请求被拒绝：参数无效',
	err_ipb: '电力储备不足（余额过低）',
	err_is: '会话无效或已过期 -- 请重新启动游戏',
	err_ate: '认证令牌已过期 -- 请重新启动游戏',
	err_gle: '{gambling}限额已超出',
	err_loc: '此位置不允许游玩',
	err_be: '本会话已有进行中的回合',
	err_gen: '服务器故障 -- 请重试',
	err_maintenance: '引擎维护中 -- 请稍后再试',
	err_unexpected: '意外故障 -- 请查看控制台详情',
	btn_acknowledge: '确认',

	auth_failed_banner: '!! 认证失败',
	auth_failed_body: '认证失败。无法启动游戏。',
	auth_rgs_rejected: '> RGS 握手被拒绝 -- 请使用有效会话重新加载以继续',

	// —— Turbo / loader ——
	turbo_tooltip: 'turbo：揭晓更快，赔率相同',
	turbo_on: 'TURBO [开]',
	turbo_off: 'TURBO [关]',
	a11y_loading: '加载中',
	boot_bios: 'OVERHEAT THERMAL BIOS v2.0',
	boot_post: 'POST........................ OK',
	boot_cooling: '检查冷却回路....... OK',
	boot_rig_array: '启动矿机阵列....... OK',
	boot_rgs: 'RGS handshake...............',

	// —— SYS LOG ——
	log_power_contacting: '> POWER ON -- 正在连接 RGS...',
	log_power_rig: '> POWER ON -- RIG: {rig}',
	log_bios_ok: '> BIOS OK .. 电压轨正常',
	log_hashrate: '> hashrate online: {hashrate} MH/s',
	log_shutdown_locked: '> 关断温度已锁定: {mult}x',
	log_mining: '> 挖矿中...',
} as const;

export default zh;
