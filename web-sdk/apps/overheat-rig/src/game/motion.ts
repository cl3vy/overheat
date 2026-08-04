/** Shared motion gates for visual-feel polish (Phase 4). */

export const prefersReducedMotion = () =>
	typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

export const isCoarsePointer = () =>
	typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches;
