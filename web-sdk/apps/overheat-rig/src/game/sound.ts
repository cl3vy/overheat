/**
 * Synthesized terminal audio via Web Audio -- no asset files. Everything is
 * guarded by the session sound toggle and wrapped so audio failures can never
 * break the game.
 */

import { stateSession } from './stateSession.svelte';

let audioContext: AudioContext | null = null;
let humOscillator: OscillatorNode | null = null;
let humGain: GainNode | null = null;

const getContext = () => {
	if (!audioContext) audioContext = new AudioContext();
	if (audioContext.state === 'suspended') audioContext.resume();
	return audioContext;
};

const enabled = () => stateSession.soundEnabled && typeof AudioContext !== 'undefined';

const beep = (
	frequency: number,
	durationMs: number,
	options: { type?: OscillatorType; volume?: number; delayMs?: number } = {},
) => {
	const { type = 'square', volume = 0.05, delayMs = 0 } = options;
	const ctx = getContext();
	const startAt = ctx.currentTime + delayMs / 1000;
	const oscillator = ctx.createOscillator();
	const gain = ctx.createGain();
	oscillator.type = type;
	oscillator.frequency.value = frequency;
	gain.gain.setValueAtTime(volume, startAt);
	gain.gain.exponentialRampToValueAtTime(0.001, startAt + durationMs / 1000);
	oscillator.connect(gain).connect(ctx.destination);
	oscillator.start(startAt);
	oscillator.stop(startAt + durationMs / 1000);
};

export const playBoot = () => {
	if (!enabled()) return;
	try {
		beep(440, 60);
		beep(660, 60, { delayMs: 90 });
		beep(880, 90, { delayMs: 180 });
	} catch {}
};

/** Low rig hum that rises in pitch with the temperature. */
export const startHum = () => {
	if (!enabled()) return;
	try {
		const ctx = getContext();
		stopHum();
		humOscillator = ctx.createOscillator();
		humGain = ctx.createGain();
		humOscillator.type = 'sawtooth';
		humOscillator.frequency.value = 55;
		humGain.gain.value = 0.025;
		humOscillator.connect(humGain).connect(ctx.destination);
		humOscillator.start();
	} catch {}
};

/** fillFraction 0..1 = progress toward the shutdown temperature. */
export const setHumLevel = (fillFraction: number) => {
	if (!humOscillator || !humGain || !audioContext) return;
	try {
		const clamped = Math.min(Math.max(fillFraction, 0), 1);
		humOscillator.frequency.setTargetAtTime(55 + clamped * 260, audioContext.currentTime, 0.05);
		humGain.gain.setTargetAtTime(0.02 + clamped * 0.04, audioContext.currentTime, 0.05);
	} catch {}
};

export const stopHum = () => {
	try {
		if (humGain && audioContext) {
			humGain.gain.setTargetAtTime(0.0001, audioContext.currentTime, 0.03);
		}
		if (humOscillator) {
			humOscillator.stop(audioContext ? audioContext.currentTime + 0.15 : undefined);
		}
	} catch {}
	humOscillator = null;
	humGain = null;
};

export const playMeltdown = () => {
	if (!enabled()) return;
	try {
		const ctx = getContext();
		// descending buzz
		const oscillator = ctx.createOscillator();
		const gain = ctx.createGain();
		oscillator.type = 'sawtooth';
		oscillator.frequency.setValueAtTime(320, ctx.currentTime);
		oscillator.frequency.exponentialRampToValueAtTime(35, ctx.currentTime + 0.7);
		gain.gain.setValueAtTime(0.09, ctx.currentTime);
		gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
		oscillator.connect(gain).connect(ctx.destination);
		oscillator.start();
		oscillator.stop(ctx.currentTime + 0.8);
		// crackle: short burst of filtered noise
		const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.4, ctx.sampleRate);
		const channel = noiseBuffer.getChannelData(0);
		for (let i = 0; i < channel.length; i += 1) {
			channel[i] = (Math.random() * 2 - 1) * (1 - i / channel.length);
		}
		const noise = ctx.createBufferSource();
		noise.buffer = noiseBuffer;
		const noiseGain = ctx.createGain();
		noiseGain.gain.value = 0.06;
		noise.connect(noiseGain).connect(ctx.destination);
		noise.start();
	} catch {}
};

/** Mechanical toggle-switch clack: low thock + brief metallic tick. */
export const playSwitchClick = (on: boolean) => {
	if (!enabled()) return;
	try {
		beep(on ? 180 : 130, 45, { type: 'square', volume: 0.06 });
		beep(on ? 2400 : 1800, 18, { type: 'square', volume: 0.03 });
	} catch {}
};

/** Rising two-note chirp when the climb crosses a milestone rung. */
export const playMilestoneChirp = (rungIndex: number) => {
	if (!enabled()) return;
	try {
		const base = 620 + Math.min(rungIndex, 8) * 90;
		beep(base, 55, { type: 'square', volume: 0.04 });
		beep(base * 1.5, 75, { type: 'square', volume: 0.045, delayMs: 60 });
	} catch {}
};

/** Tiny coin blip for yield toasts. Quiet: it fires often mid-climb. */
export const playCoinTick = () => {
	if (!enabled()) return;
	try {
		beep(1560, 30, { type: 'triangle', volume: 0.03 });
		beep(2080, 45, { type: 'triangle', volume: 0.025, delayMs: 30 });
	} catch {}
};

/** Rising alarm sweep when the limiter slips and the temp punches past the
 * target. Bigger multiple = longer, angrier sweep. */
export const playOverdriveSurge = (multiple: number) => {
	if (!enabled()) return;
	try {
		const ctx = getContext();
		const durationS = multiple >= 6 ? 1.1 : multiple >= 2.5 ? 0.8 : 0.55;
		const oscillator = ctx.createOscillator();
		const gain = ctx.createGain();
		oscillator.type = 'sawtooth';
		oscillator.frequency.setValueAtTime(220, ctx.currentTime);
		oscillator.frequency.exponentialRampToValueAtTime(220 * 6, ctx.currentTime + durationS);
		gain.gain.setValueAtTime(0.05, ctx.currentTime);
		gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + durationS + 0.15);
		oscillator.connect(gain).connect(ctx.destination);
		oscillator.start();
		oscillator.stop(ctx.currentTime + durationS + 0.15);
		// warning blips over the sweep
		const blips = multiple >= 6 ? 5 : 3;
		for (let i = 0; i < blips; i += 1) {
			beep(1200 + i * 200, 60, { type: 'square', volume: 0.04, delayMs: 120 + i * 170 });
		}
	} catch {}
};

/** Checkpoint rung locked mid-climb: vault click + coin ding, rising with
 * every rung crossed so a deep run literally sounds like an ascent. */
export const playBankTick = (rungIndex: number) => {
	if (!enabled()) return;
	try {
		const base = 660 + Math.min(rungIndex, 10) * 70;
		beep(150, 40, { type: 'square', volume: 0.05 });
		beep(base, 60, { type: 'triangle', volume: 0.045, delayMs: 45 });
		beep(base * 1.5, 90, { type: 'triangle', volume: 0.04, delayMs: 110 });
	} catch {}
};

/** "Ka-chunk" vault lock when the win banks. */
export const playBankLock = () => {
	if (!enabled()) return;
	try {
		beep(95, 90, { type: 'square', volume: 0.09 });
		beep(70, 130, { type: 'square', volume: 0.08, delayMs: 100 });
		beep(2400, 25, { type: 'square', volume: 0.03, delayMs: 110 });
		beep(1200, 220, { type: 'sine', volume: 0.05, delayMs: 240 });
	} catch {}
};

/** Escalating victory arpeggio; higher tier = longer and brighter. */
export const playWinFanfare = (level: number) => {
	if (!enabled()) return;
	try {
		const scale = [523, 659, 784, 1047, 1319, 1568, 2093]; // C major run
		const notes = Math.min(3 + level, scale.length);
		for (let i = 0; i < notes; i += 1) {
			beep(scale[i], 140, { type: 'sine', volume: 0.07, delayMs: i * 110 });
			beep(scale[i] / 2, 140, { type: 'triangle', volume: 0.04, delayMs: i * 110 });
		}
		// closing chord
		const chordAt = notes * 110 + 80;
		beep(scale[notes - 1], 500, { type: 'sine', volume: 0.08, delayMs: chordAt });
		beep(scale[Math.max(notes - 3, 0)], 500, { type: 'sine', volume: 0.06, delayMs: chordAt });
		if (level >= 4) beep(scale[notes - 1] * 2, 500, { type: 'sine', volume: 0.04, delayMs: chordAt });
	} catch {}
};
