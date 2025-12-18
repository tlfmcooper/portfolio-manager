const normalizeEnvUrl = (value) => {
  let url = value.trim();

  // Force HTTPS for non-local URLs to prevent mixed content errors
  if (url.startsWith('http://') && !url.includes('localhost') && !url.includes('127.0.0.1')) {
    url = url.replace('http://', 'https://');
  }

  if (!/^https?:\/\//i.test(url)) {
    // Allow protocol-relative strings like //api.example.com
    if (url.startsWith('//')) {
      url = `https:${url}`;
    } else {
      url = `https://${url}`;
    }
  }

  // Remove trailing slash once to keep predictable concatenation
  return url.replace(/\/$/, '');
};

export const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL?.trim();
  if (envUrl) {
    return normalizeEnvUrl(envUrl);
  }

  const hostname = window.location.hostname;
  const isLocalDev = hostname === 'localhost' || hostname === '127.0.0.1';
  const protocol = isLocalDev ? 'http' : 'https';
  const portSegment = isLocalDev ? ':8000' : '';

  return `${protocol}://${hostname}${portSegment}/api/v1`;
};

export const buildApiUrl = (path = '') => {
  const baseUrl = getApiBaseUrl();
  if (!path) {
    return baseUrl;
  }

  return `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
};
