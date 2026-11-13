import assert from 'node:assert/strict';
import test from 'node:test';
import { createPageLoadingState } from '../../src/components/ui/pageLoadingState.ts';

test('initial screen waits for all registered visible dependencies', () => {
  const state = createPageLoadingState();
  const list = Symbol(), detail = Symbol();
  state.setPending(list, true);
  state.setPending(detail, true);
  state.revealIfReady();
  assert.equal(state.isReady(), false);
  state.setPending(list, false);
  state.revealIfReady();
  assert.equal(state.isReady(), false);
  state.setPending(detail, false);
  state.revealIfReady();
  assert.equal(state.isReady(), true);
});

test('a waterfall can replace its first dependency before revealing the page', () => {
  const state = createPageLoadingState();
  const list = Symbol(), selected = Symbol();
  state.setPending(list, true);
  state.setPending(list, false);
  state.setPending(selected, true);
  state.revealIfReady();
  assert.equal(state.isReady(), false);
});

test('settled errors and unmounted dependencies release initial waiting', () => {
  const state = createPageLoadingState();
  const request = Symbol();
  state.setPending(request, true);
  state.setPending(request, false);
  state.revealIfReady();
  assert.equal(state.isReady(), true);
});

test('cached pages reveal without a request; later refreshes never hide them', () => {
  const state = createPageLoadingState();
  state.revealIfReady();
  const version = state.snapshot();
  state.setPending(Symbol(), true);
  state.revealIfReady();
  assert.equal(state.isReady(), true);
  assert.equal(state.snapshot(), version);
});

test('independent pages do not share readiness and subscriptions clean up', () => {
  const first = createPageLoadingState(), second = createPageLoadingState();
  let updates = 0;
  const unsubscribe = first.subscribe(() => updates++);
  const request = Symbol();
  first.setPending(request, true);
  first.setPending(request, true);
  assert.equal(updates, 1);
  unsubscribe();
  first.setPending(request, false);
  first.revealIfReady();
  assert.equal(updates, 1);
  assert.equal(second.isReady(), false);
});
