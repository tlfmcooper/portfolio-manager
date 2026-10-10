import { describe, expect, it, vi } from 'vitest';
import { createDataCache } from '../../src/services/dataCache';

const storage = () => {
  const values = new Map();
  return { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
};

describe('account-scoped data cache', () => {
  it('keeps what-if chart arrays out of storage and bounds scenario variants', () => {
    const session = storage();
    let now = 1;
    const cache = createDataCache(1, session, () => now++);
    for (let i = 0; i < 65; i++) cache.setInCache(`portfolio_analysis:scenario:${i}`, { paths: [i] }, 1000);
    expect(cache.getFromCache('portfolio_analysis:scenario:0')).toBeNull();
    expect(cache.getFromCache('portfolio_analysis:scenario:64')).toEqual({ paths: [64] });
    expect(createDataCache(1, session).getFromCache('portfolio_analysis:scenario:64')).toBeNull();
  });
  it('coalesces concurrent requests, preserves falsy values, and expires entries', async () => {
    let now = 1000;
    const cache = createDataCache(1, storage(), () => now);
    const fetch = vi.fn(async () => 0);
    expect(await Promise.all([cache.fetchWithCache('metrics', fetch, 100), cache.fetchWithCache('metrics', fetch, 100)])).toEqual([0, 0]);
    await cache.fetchWithCache('metrics', fetch, 100);
    expect(fetch).toHaveBeenCalledTimes(1);
    now += 101;
    await cache.fetchWithCache('metrics', fetch, 100);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it('survives reload for the same account and separates accounts and currencies', () => {
    const session = storage();
    const cache = createDataCache(1, session);
    cache.setInCache('snapshot', { value: 100 }, 1000, 'USD');
    cache.dispose();
    expect(createDataCache(1, session).getFromCache('snapshot', 'USD')).toEqual({ value: 100 });
    expect(createDataCache(1, session).getFromCache('snapshot', 'CAD')).toBeNull();
    expect(createDataCache(2, session).getFromCache('snapshot', 'USD')).toBeNull();
    cache.clearCache();
    expect(createDataCache(1, session).getFromCache('snapshot', 'USD')).toBeNull();
  });
  it('does not restore a request invalidated during a trade or logout', async () => {
    const cache = createDataCache(1, storage());
    let complete;
    const result = cache.fetchWithCache('metrics', () => new Promise(resolve => { complete = resolve; }), 1000);
    await Promise.resolve();
    cache.invalidateCache('metrics');
    complete({ old: true });
    await result;
    expect(cache.getFromCache('metrics')).toBeNull();
    let finish;
    const late = cache.fetchWithCache('metrics', () => new Promise(resolve => { finish = resolve; }), 1000);
    await Promise.resolve();
    cache.clearCache();
    finish({ old: true });
    await late;
    expect(cache.getFromCache('metrics')).toBeNull();
  });
  it('retries failed requests and supports explicit refresh', async () => {
    const cache = createDataCache(1, storage());
    await expect(cache.fetchWithCache('x', () => Promise.reject(new Error('offline')), 1000)).rejects.toThrow('offline');
    expect(cache.getFromCache('x')).toBeNull();
    await cache.fetchWithCache('x', async () => 'new', 1000);
    expect(await cache.fetchWithCache('x', async () => 'refreshed', 1000, null, { force: true })).toBe('refreshed');
  });
});
