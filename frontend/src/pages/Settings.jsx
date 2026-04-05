import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Copy, KeyRound, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';

import { useAuth } from '../contexts/AuthContext';

const formatDate = (value) => {
  if (!value) {
    return 'Never';
  }
  return new Date(value).toLocaleString();
};

const Settings = () => {
  const { api, user } = useAuth();
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [rotatingId, setRotatingId] = useState(null);
  const [revokingId, setRevokingId] = useState(null);
  const [name, setName] = useState('Primary MCP Key');
  const [expiresInDays, setExpiresInDays] = useState('');
  const [revealedKey, setRevealedKey] = useState(null);

  const loadKeys = async () => {
    try {
      setLoading(true);
      const response = await api.get('/users/me/mcp-api-keys');
      setKeys(response.data);
    } catch (error) {
      console.error('Failed to load MCP API keys', error);
      toast.error('Failed to load MCP API keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKeys();
  }, []);

  const copyKey = async (value) => {
    try {
      await navigator.clipboard.writeText(value);
      toast.success('API key copied');
    } catch (error) {
      toast.error('Failed to copy API key');
    }
  };

  const createKey = async (event) => {
    event.preventDefault();
    try {
      setCreating(true);
      const response = await api.post('/users/me/mcp-api-keys', {
        name,
        expires_in_days: expiresInDays ? Number(expiresInDays) : null,
      });
      setRevealedKey(response.data);
      setName('Primary MCP Key');
      setExpiresInDays('');
      await loadKeys();
      toast.success('MCP API key created');
    } catch (error) {
      console.error('Failed to create MCP API key', error);
      toast.error(error.response?.data?.detail || 'Failed to create MCP API key');
    } finally {
      setCreating(false);
    }
  };

  const rotateKey = async (key) => {
    try {
      setRotatingId(key.id);
      const response = await api.post(`/users/me/mcp-api-keys/${key.id}/rotate`, {
        name: key.name,
        expires_in_days: key.expires_at ? Math.max(1, Math.ceil((new Date(key.expires_at) - Date.now()) / 86400000)) : null,
      });
      setRevealedKey(response.data);
      await loadKeys();
      toast.success('MCP API key rotated');
    } catch (error) {
      console.error('Failed to rotate MCP API key', error);
      toast.error(error.response?.data?.detail || 'Failed to rotate MCP API key');
    } finally {
      setRotatingId(null);
    }
  };

  const revokeKey = async (key) => {
    try {
      setRevokingId(key.id);
      await api.delete(`/users/me/mcp-api-keys/${key.id}`);
      await loadKeys();
      toast.success('MCP API key revoked');
    } catch (error) {
      console.error('Failed to revoke MCP API key', error);
      toast.error(error.response?.data?.detail || 'Failed to revoke MCP API key');
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border p-6" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-secondary)' }}>Account</p>
            <h2 className="mt-2 text-2xl font-semibold" style={{ color: 'var(--color-text)' }}>MCP Access</h2>
            <p className="mt-2 max-w-2xl text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Create a personal MCP API key for tools that need direct access to your portfolio. Keys are shown exactly once when created or rotated.
            </p>
          </div>
          <div className="rounded-xl border px-4 py-3 text-right" style={{ borderColor: 'var(--color-border)' }}>
            <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--color-text-secondary)' }}>Signed in as</p>
            <p className="mt-1 text-sm font-medium" style={{ color: 'var(--color-text)' }}>{user?.display_name || user?.username}</p>
            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{user?.email}</p>
          </div>
        </div>
      </section>

      {revealedKey && (
        <section className="rounded-2xl border p-6" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-primary)' }}>
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Copy this key now</h3>
          </div>
          <p className="mt-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            This is the only time the full secret will be shown. Store it in your MCP client config or a password manager.
          </p>
          <div className="mt-4 rounded-xl border p-4" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-background)' }}>
            <p className="break-all font-mono text-sm" style={{ color: 'var(--color-text)' }}>{revealedKey.api_key}</p>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              onClick={() => copyKey(revealedKey.api_key)}
              className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold"
              style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-btn-primary-text)' }}
            >
              <Copy className="h-4 w-4" />
              Copy API Key
            </button>
            <button
              onClick={() => setRevealedKey(null)}
              className="rounded-lg px-4 py-2 text-sm font-semibold"
              style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text)', border: '1px solid var(--color-border)' }}
            >
              Dismiss
            </button>
          </div>
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border p-6" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
          <div className="flex items-center gap-3">
            <KeyRound className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Existing Keys</h3>
          </div>
          <div className="mt-4 space-y-4">
            {loading ? (
              <p style={{ color: 'var(--color-text-secondary)' }}>Loading MCP API keys...</p>
            ) : keys.length === 0 ? (
              <p style={{ color: 'var(--color-text-secondary)' }}>No MCP API keys yet.</p>
            ) : (
              keys.map((key) => (
                <div key={key.id} className="rounded-xl border p-4" style={{ borderColor: 'var(--color-border)' }}>
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{key.name}</p>
                      <p className="mt-1 font-mono text-xs" style={{ color: 'var(--color-text-secondary)' }}>{key.key_preview}</p>
                      <div className="mt-3 grid gap-1 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                        <p>Created: {formatDate(key.created_at)}</p>
                        <p>Last used: {formatDate(key.last_used_at)}</p>
                        <p>Expires: {formatDate(key.expires_at)}</p>
                        <p>Status: {key.is_active ? 'Active' : 'Revoked'}</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => rotateKey(key)}
                        disabled={!key.is_active || rotatingId === key.id}
                        className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
                        style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-btn-primary-text)' }}
                      >
                        <RefreshCw className="h-4 w-4" />
                        {rotatingId === key.id ? 'Rotating...' : 'Rotate'}
                      </button>
                      <button
                        onClick={() => revokeKey(key)}
                        disabled={!key.is_active || revokingId === key.id}
                        className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
                        style={{ backgroundColor: 'var(--color-error)', color: 'var(--color-white)' }}
                      >
                        <Trash2 className="h-4 w-4" />
                        {revokingId === key.id ? 'Revoking...' : 'Revoke'}
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border p-6" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
          <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Create New Key</h3>
          <form className="mt-4 space-y-4" onSubmit={createKey}>
            <div>
              <label className="mb-2 block text-sm font-medium" style={{ color: 'var(--color-text)' }}>Key name</label>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-full rounded-lg border px-3 py-2"
                style={{ backgroundColor: 'var(--color-background)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                placeholder="Primary MCP Key"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium" style={{ color: 'var(--color-text)' }}>Expires in days</label>
              <input
                value={expiresInDays}
                onChange={(event) => setExpiresInDays(event.target.value)}
                className="w-full rounded-lg border px-3 py-2"
                style={{ backgroundColor: 'var(--color-background)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                placeholder="Leave blank for no expiry"
                inputMode="numeric"
              />
            </div>
            <div className="rounded-xl border p-4 text-sm" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
              This key grants access to your own portfolio MCP tools only. The backend stores a hash, not the raw secret.
            </div>
            <button
              type="submit"
              disabled={creating || !name.trim()}
              className="w-full rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50"
              style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-btn-primary-text)' }}
            >
              {creating ? 'Creating key...' : 'Create MCP API Key'}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
};

export default Settings;