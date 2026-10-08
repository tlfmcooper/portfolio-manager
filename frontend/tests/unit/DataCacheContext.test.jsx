import React, { useEffect, useState } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DataCacheProvider, useDataCache } from '../../src/contexts/DataCacheContext';

vi.mock('../../src/contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 42 } }) }));

describe('DataCacheProvider effect stability', () => {
  it('does not retrigger loading effects when another cache entry changes', async () => {
    sessionStorage.clear();
    const effects = vi.fn();
    const fetch = vi.fn(async () => ({ value: 100 }));
    function Consumer() {
      const { fetchWithCache, setInCache, CACHE_TTL } = useDataCache();
      const [value, setValue] = useState(null);
      useEffect(() => {
        effects();
        fetchWithCache('probe', fetch, CACHE_TTL.DASHBOARD).then(result => setValue(result.value));
      }, [fetchWithCache, CACHE_TTL]);
      return <><span>{value}</span><button onClick={() => setInCache('unrelated', 1, 1000)}>Cache another response</button></>;
    }
    render(<DataCacheProvider><Consumer /></DataCacheProvider>);
    await screen.findByText('100');
    screen.getByText('Cache another response').click();
    await waitFor(() => expect(effects).toHaveBeenCalledTimes(1));
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
