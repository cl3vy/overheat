/**
 * Overheat Japanese locale.
 * Keys match en.ts. Placeholders and brand/units stay as-is.
 */
const ja = {
	// —— Brand / chrome (brand stays OVERHEAT) ——
	brand_overheat: 'OVERHEAT',
	hdr_console_full: 'OVERHEAT // マイニングリグ熱管理コンソール',
	hdr_console_sub: 'マイニングリグ熱管理コンソール',
	btn_rules: '[ルール]',
	hdr_session: 'セッション {time}',
	hdr_rtp: 'RTP {percent}%',
	hdr_replay: 'REPLAY -- ラウンド再生',
	hdr_pwr_reserve: '電力予備:',
	hdr_net: 'NET {amount}',
	hdr_turbo: ' [TURBO]',
	status_loading_replay: 'リプレイ読込中...',

	// —— Social / standard lexicon ——
	word_stake: 'ステーク',
	word_stake_social: 'プレイ額',
	label_stake: 'ステーク',
	label_stake_social: 'プレイ額',
	word_cash_out: 'キャッシュアウト',
	word_cash_out_social: '回収',
	label_cash_out_target: 'キャッシュアウト目標',
	label_cash_out_target_social: '回収目標',
	word_pays: '払い',
	word_pays_social: '勝ち',
	word_pay: '払う',
	word_pay_social: '勝つ',
	word_payout: 'ペイアウト',
	word_payout_social: '勝利金',
	label_payouts: 'ペイアウト',
	label_payouts_social: '勝利金',
	word_gambling: 'ギャンブル',
	word_gambling_social: 'プレイ',
	label_cost_at: '現在のコスト',
	label_cost_at_social: '現在のプレイ可能額',
	phrase_mode_costs: '各モードのコストはちょうど',
	phrase_mode_costs_social: '各モードはちょうどこの額でプレイ可能',
	word_payouts_plural: 'ペイアウト',
	word_payouts_plural_social: '勝利金',

	// —— Rig select / how it works ——
	loop_title: '// 遊び方',
	loop_body_first:
		'自動{cashOut}目標を設定。リグを起動。自力で上昇し、そこで自動停止。{meltdownClause}',
	loop_body_return:
		'> 自動{cashOut}目標を設定 -- リグは自力で上昇し、そこで自動停止。{meltdownClause}',
	loop_melt_keep_checkpoints:
		'先にメルトダウンした場合、チェックポイントで確保した分だけ残る。',
	loop_melt_lose_stake: '先にメルトダウンした場合、{stake}を失う。',
	stat_hottest: '最高温度',
	stat_hottest_value: '{mult}x',
	stat_best_bank: '最高バンク',
	stat_hottest_empty: '最高温度 --',
	dial_translate: '{cashOut} @ {mult}x',
	a11y_shutdown_temp: 'シャットダウン温度',
	dial_scale_safe: '安全',
	dial_scale_spicy: '危険',
	dial_pays_something: '{pays}あり: ラウンドの{percent}%',
	label_stake_row: '{stake}:',
	dial_full_send: 'フルセンド {pays} {winPays}、オーバードライブで最大{maxPays}',
	btn_boot_rig: '>> リグ起動 <<',
	warn_insufficient_pwr: '電力予備不足 -- {stake}を下げてください',
	hint_space_boot: '[SPACE] で起動',
	settings_sound: 'サウンド',
	settings_scanlines: 'スキャンライン',
	settings_flicker: 'フリッカー',
	btn_fairness: '[フェアネス]',
	a11y_settings: '表示とサウンド設定',

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
	flavor_idle: 'ほんのり温かい。ほぼ貯金口座。',
	flavor_eco: 'アンダーボルト。地味。家賃は払える。',
	flavor_eco_social: 'アンダーボルト。地味。家賃分は勝つ。',
	flavor_standard: '純正クーラー、純正の度胸。',
	flavor_boost: '工場オーバークロック。軽い汗。',
	flavor_overclock: '保証無効。サーマルグリス任意。',
	flavor_nitro: '社外ファン、絶叫中。',
	flavor_furnace: '部屋を暖める。時には家ごと。',
	flavor_inferno: '煙感知器は抜いてある。',
	flavor_meltdown: 'シリコンルーレット。防火ブランケット持参。',
	flavor_reactor: '無許可核分裂。誰にも言うな。',
	flavor_plasma: 'これは採掘じゃない。これは恒星だ。',

	// —— Checkpoint profiles (rules table) ——
	profile_drip: '頻繁・少額',
	profile_balanced: '安定',
	profile_spike: '稀・大額',

	// —— Run view ——
	run_topline: 'RIG: {rig} | {stakeLabel}: {amount}',
	col_sys_log: '// SYS LOG',
	label_core_temp: 'コア温度',
	tag_limiter_slipped: '!! リミッター逸脱 -- OVERDRIVE !!',
	run_cashout_at: '{cashOut} @ {mult}x',
	label_secured_yield: '確保済み利得',
	yield_next_lock: '次ロック @ {nextMult}x → {bankMult}x',
	yield_all_locked: '全チェックポイントロック済 -- 目標へ押し切れ',
	col_checkpoints: '// CHECKPOINTS',
	ladder_full: 'FULL {mult}x',

	result_meltdown: '** メルトダウン @ {mult}x **',
	result_near_miss: 'チェックポイント{checkpoint}xまであと{delta}xで死んだ',
	result_aimed_for: '目標は{mult}x',
	result_checkpoints_held: '>> チェックポイント保持: +{amount} 確保',

	win_headline_clean: 'クリーンシャットダウン',
	win_headline_overdrive: '熱リミッター逸脱 -- 目標の1.5x',
	win_headline_critical: 'ブレーカー作動 -- 目標の3x',
	win_headline_golden: 'シリコン昇華 -- 目標の10x',
	win_label_golden: 'ゴールデンシャットダウン',
	win_label_legendary: '伝説のラン',
	win_label_massive: '超巨大バンク',
	win_label_huge: '巨大バンク',
	win_label_big: 'ビッグバンク',
	win_label_clean: 'クリーンバンク',
	win_banner: '>>> {label} <<<',
	win_bonus_mult: '{payout}に{mult}xボーナス倍率',
	win_peaked: 'クリーン完走 -- ピーク{mult}x',
	win_survived: '{mult}x 生存',
	badge_personal_best: '★ 自己ベスト更新 ★',
	badge_personal_best_run: '★ 自己ベストラン更新 ★',

	btn_replay_again: '>> もう一度リプレイ <<',
	btn_boot_again: '>> 再起動 << [SPACE]',
	btn_return_rig_select: 'リグ選択に戻る',
	btn_return_rig_select_mini: 'リグ選択',
	label_round_id: 'ラウンドID: {id}',
	status_settling: 'ラウンド精算中...',

	// —— Rules ——
	a11y_rules: 'ゲームルール',
	rules_title: '// ゲームルール',
	rules_how_to_play: '遊び方',
	rules_howto_body:
		'自動{cashOut}目標と{stake}を設定し、リグを起動。リグは自力で上昇し、目標で自動停止 -- ラウンド中の操作は不要。目標前にメルトダウンした場合、途中のチェックポイントで確保した分だけ残る。',
	rules_controls:
		'操作: スライダーまたは - / + でリグを選択（{cashOut}目標を設定）、- / + または Min / 1/2 / 2x / Max で{stake}を設定し、リグ起動を押す。デスクトップではSPACEで起動。結果は自動精算；再起動で同じラウンドを繰り返す。',
	rules_modes: 'モード',
	rules_modes_intro:
		'{modeCosts}設定した{stake}{noCostNote}。「{pays}あり」はラウンドが何らかの{payout}を返す確率。',
	rules_no_cost_multipliers: '（コスト倍率なし）',
	rules_th_rig: 'rig',
	rules_th_cashout_target: '{cashOut}目標',
	rules_th_pays_something: '{pays}あり',
	rules_th_checkpoints: 'チェックポイント',
	rules_th_cost: '{costAt} {stake}',
	rules_payouts_body:
		'各リグには目標未満のチェックポイント梯子がある。上昇中に通過したチェックポイントごとに部分{payout}が確保され、その後メルトダウンしても残る。目標到達で目標倍率×{stake}を{pays}。',
	rules_overdrive:
		'OVERDRIVE: 勝利ラウンドの一部で熱リミッターが目標を超え、シャットダウン時にボーナス倍率を{pays} -- 目標の1.5x（overdrive）、3x（critical）、または10x（ゴールデンシャットダウン）。オーバードライブはラウンド結果で決まり、入力不要・手動起動不可。',
	rules_max_win:
		'最大勝利: {stake}の{maxWin}x（{mode}の最高ペイアウト）。{payouts}は最大勝利で上限。',
	rules_rtp_heading: 'RTP',
	rules_rtp_body:
		'プレイヤー還元率は全モード・全{cashOut}目標で{percent}%。',
	rules_disclaimer_heading: '免責事項',
	rules_disclaimer:
		'不具合が発生した場合、すべての勝利およびプレイは無効となります。安定したインターネット接続が必要です。切断時はゲームを再読み込みし、未完了ラウンドを完了してください。期待還元は多数のプレイから算出されます。ゲーム画面は物理デバイスを再現するものではなく、説明用です。勝利金はブラウザ内イベントではなく、Remote Game Serverから受け取った金額に基づき精算されます。TM and © 2026 Stake Engine.',
	rules_social_entertainment: '本ゲームは娯楽目的のみで提供されています。',
	btn_close: '閉じる',

	// —— Fairness ——
	a11y_fairness: '証明可能な公平性の詳細',
	fairness_title: '// 証明可能な公平性',
	fairness_rtp: '{percent}% -- 全リグ',
	fairness_last_round: '最終ラウンドID',
	fairness_body:
		'すべての結果は封印済みの事前計算結果テーブルから抽選され、リビール演出の前にStake Engine RGSがサーバー側で精算する。リビールでは結果は変わらない。精算済みラウンドの監査にはラウンドIDをオペレーターに提示せよ。',

	// —— Errors ——
	error_system_fault: '!! システム故障 {code}',
	err_val: 'リクエスト拒否: パラメータ無効',
	err_ipb: '電力予備不足（残高不足）',
	err_is: 'セッション無効または期限切れ -- ゲームを再起動',
	err_ate: '認証トークン期限切れ -- ゲームを再起動',
	err_gle: '{gambling}限度超過',
	err_loc: 'この場所からのプレイは許可されていません',
	err_be: 'このセッションで既にラウンド進行中',
	err_gen: 'サーバー故障 -- 再試行してください',
	err_maintenance: 'エンジンメンテナンス中 -- 後で再試行',
	err_unexpected: '予期せぬ故障 -- コンソールを確認',
	btn_acknowledge: '確認',

	auth_failed_banner: '!! 認証失敗',
	auth_failed_body: '認証に失敗しました。ゲームを開始できません。',
	auth_rgs_rejected: '> RGSハンドシェイク拒否 -- 有効なセッションで再読み込みして続行',

	// —— Turbo / loader ——
	turbo_tooltip: 'turbo: リビール高速、確率は同じ',
	turbo_on: 'TURBO [オン]',
	turbo_off: 'TURBO [オフ]',
	a11y_loading: '読込中',
	boot_bios: 'OVERHEAT THERMAL BIOS v2.0',
	boot_post: 'POST........................ OK',
	boot_cooling: '冷却ループ確認中....... OK',
	boot_rig_array: 'リグアレイ起動中....... OK',
	boot_rgs: 'RGS handshake...............',

	// —— SYS LOG ——
	log_power_contacting: '> POWER ON -- RGS接続中...',
	log_power_rig: '> POWER ON -- RIG: {rig}',
	log_bios_ok: '> BIOS OK .. 電圧レール正常',
	log_hashrate: '> hashrate online: {hashrate} MH/s',
	log_shutdown_locked: '> シャットダウン温度ロック: {mult}x',
	log_mining: '> マイニング中...',
} as const;

export default ja;
