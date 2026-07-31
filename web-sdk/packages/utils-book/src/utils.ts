import { PUBLIC_CHROMATIC } from 'envs';
import { stateUrlDerived } from 'state-shared';
import { requestEndEvent } from 'rgs-requests';

import type { BaseBookEvent } from './types';

// /bet/event progress reports are resume markers: only the LATEST index
// matters. Coalesce them -- one request in flight, newest index wins -- so a
// fast (turbo) round can't burst 5-6 requests and trip the RGS rate limiter
// (429s there also take down /wallet/end-round, stranding the round open).
let pendingEventIndex: number | null = null;
let eventRequestInFlight = false;

const flushBookEventProgress = async () => {
	if (eventRequestInFlight || pendingEventIndex === null) return;
	const eventIndex = pendingEventIndex;
	pendingEventIndex = null;
	eventRequestInFlight = true;
	try {
		await requestEndEvent({
			eventIndex,
			rgsUrl: stateUrlDerived.rgsUrl(),
			sessionID: stateUrlDerived.sessionID(),
		});
	} catch (error) {
		console.error(error);
	}
	eventRequestInFlight = false;
	// a newer index may have arrived while this one was in flight
	void flushBookEventProgress();
};

export function recordBookEvent<TBookEvent extends BaseBookEvent>({
	bookEvent,
}: {
	bookEvent: TBookEvent;
}) {
	if (PUBLIC_CHROMATIC || stateUrlDerived.replay()) {
		console.log('mock request end-event:', { index: bookEvent.index, type: bookEvent.type });
		return;
	}

	pendingEventIndex = bookEvent.index;
	void flushBookEventProgress();
}

export function checkIsMultipleRevealEvents<TBookEvent extends BaseBookEvent>({
	bookEvents,
}: {
	bookEvents: TBookEvent[];
}) {
	const revealEventCount = bookEvents.filter((bookEvent) => bookEvent.type === 'reveal').length;
	const isMultipleReveals = revealEventCount > 1;
	return isMultipleReveals;
}
