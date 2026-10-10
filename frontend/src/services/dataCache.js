/** Persist only this account's session, never cache a failed request. */
export function createDataCache(userId, storage = window.sessionStorage, now = Date.now) {
  const storageKey = userId ? `portfolio-cache:v2:${userId}` : null;
  let entries = {};
  let generation = 0;
  const pending = new Map();
  const versions = new Map();
  try {
    if (storageKey) entries = JSON.parse(storage.getItem(storageKey) || '{}');
    if (!entries || typeof entries !== 'object' || Array.isArray(entries)) entries = {};
  } catch { entries = {}; }

  const keyFor = (key, currency) => currency ? `${key}_${currency}` : key;
  const persist = () => {
    // What-if results are ephemeral and can contain thousands of chart points.
    // Keep them in memory so every edit does not serialize those arrays to storage.
    try { if (storageKey) storage.setItem(storageKey, JSON.stringify(Object.fromEntries(
      Object.entries(entries).filter(([key]) => !key.startsWith('portfolio_analysis:scenario:'))))); } catch { /* Memory cache still works. */ }
  };
  const getFromCache = (key, currency = null, { allowStale = false } = {}) => {
    const entry = entries[keyFor(key, currency)];
    if (!entry || !Number.isFinite(entry.timestamp) || !Number.isFinite(entry.ttl)) return null;
    // Keep stale snapshots for at most one day; the caller discloses freshness.
    return now() - entry.timestamp < (allowStale ? 86400000 : entry.ttl) ? entry.data : null;
  };
  const setInCache = (key, data, ttl, currency = null) => {
    entries[keyFor(key, currency)] = { data, timestamp: now(), ttl };
    const scenarioKeys = Object.keys(entries).filter(value => value.startsWith('portfolio_analysis:scenario:'));
    if (scenarioKeys.length > 60) {
      scenarioKeys.sort((a, b) => entries[a].timestamp - entries[b].timestamp);
      for (const oldest of scenarioKeys.slice(0, scenarioKeys.length - 60)) delete entries[oldest];
    }
    persist();
  };
  const fetchWithCache = (key, fetchFn, ttl, currency = null, { force = false } = {}) => {
    const cacheKey = keyFor(key, currency);
    if (!force) {
      const cached = getFromCache(key, currency);
      if (cached !== null) return Promise.resolve(cached);
    }
    if (pending.has(cacheKey)) return pending.get(cacheKey);
    const startedGeneration = generation;
    const version = versions.get(cacheKey) || 0;
    const request = Promise.resolve().then(fetchFn).then(data => {
      if (generation === startedGeneration && (versions.get(cacheKey) || 0) === version) {
        setInCache(key, data, ttl, currency);
      }
      return data;
    }).finally(() => {
      if (pending.get(cacheKey) === request) pending.delete(cacheKey);
    });
    pending.set(cacheKey, request);
    return request;
  };
  const invalidateCache = keys => {
    const prefixes = Array.isArray(keys) ? keys : [keys];
    for (const key of new Set([...Object.keys(entries), ...pending.keys()])) {
      if (prefixes.some(prefix => key.startsWith(prefix))) {
        delete entries[key];
        pending.delete(key);
        versions.set(key, (versions.get(key) || 0) + 1);
      }
    }
    persist();
  };
  const clearCache = () => {
    generation++;
    entries = {};
    pending.clear();
    versions.clear();
    try { if (storageKey) storage.removeItem(storageKey); } catch { /* Storage is optional. */ }
  };
  // Disposal blocks late writes while preserving the session across a page refresh.
  const dispose = () => { generation++; pending.clear(); };
  const prefetch = (key, fetchFn, ttl, currency) => fetchWithCache(key, fetchFn, ttl, currency).catch(() => {});
  return { getFromCache, setInCache, fetchWithCache, invalidateCache, clearCache, dispose, prefetch };
}
