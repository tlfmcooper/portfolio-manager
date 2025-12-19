const isLocalHost = (value) => {
  try {
    const host = new URL(value).hostname;
    return host === 'localhost' || host === '127.0.0.1';
  } catch (_) {
    return value === 'localhost' || value === '127.0.0.1';
  }
};

let resolvedBaseUrl;
let loggedBaseUrl = false;

const normalizeEnvUrl = (value) => {
  let url = value.trim();

  if (url.startsWith('http://') && !isLocalHost(url)) {
    url = url.replace('http://', 'https://');
  }

  if (!/^https?:\/\//i.test(url)) {
    if (url.startsWith('//')) {
      url = `https:${url}`;
    } else {
      url = `https://${url}`;
    }
  }

  return url.replace(/\/$/, '');
};

const assertHttpsInProd = (url) => {
  const parsed = new URL(url);
  const local = isLocalHost(parsed.hostname);
  if (!local && parsed.protocol !== 'https:') {
    throw new Error('API base URL must be HTTPS in production');
  }
};

export const getApiBaseUrl = () => {
  if (resolvedBaseUrl) {
    return resolvedBaseUrl;
  }

  const envUrl = import.meta.env.VITE_API_URL?.trim();
  if (envUrl) {
    resolvedBaseUrl = normalizeEnvUrl(envUrl);
  } else {
    const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
    const local = isLocalHost(hostname);
    const protocol = local ? 'http' : 'https';
    const portSegment = local ? ':8000' : '';
    resolvedBaseUrl = `${protocol}://${hostname}${portSegment}/api/v1`;
  }

  assertHttpsInProd(resolvedBaseUrl);

  if (!loggedBaseUrl) {
    console.info('Using API base URL:', resolvedBaseUrl);
    loggedBaseUrl = true;
  }

  return resolvedBaseUrl;
};

export const buildApiUrl = (path = '') => {
  const baseUrl = getApiBaseUrl();
  if (!path) {
    return baseUrl;
  }

  return `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
};
