export const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL?.trim();
  if (envUrl) {
    return envUrl.replace(/\/$/, '');
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
