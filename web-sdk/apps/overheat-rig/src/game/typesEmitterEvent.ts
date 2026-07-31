export type EmitterEventGame =
	| { type: 'bet' }
	| { type: 'autoBet' }
	| { type: 'resumeBet' }
	| { type: 'stopButtonEnable' };
