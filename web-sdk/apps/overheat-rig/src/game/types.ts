export type { RigId, RigInfo } from './constants';

export type Phase = 'idle' | 'booting' | 'heating' | 'banked' | 'fried';

export type LogTone = 'normal' | 'dim' | 'warn' | 'fault' | 'win';

export type LogLine = {
	text: string;
	tone: LogTone;
};
