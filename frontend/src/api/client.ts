import axios from 'axios';

function normalizeHost(host: string) {
  if (host === '0.0.0.0') return 'localhost';
  return host;
}

function resolveBaseURL(): string {
  const envUrl = (import.meta as any).env?.VITE_API_BASE_URL as string | undefined;
  if (envUrl) return envUrl;
  const { protocol, hostname } = window.location;
  return `${protocol}//${normalizeHost(hostname)}:8000`;
}

const baseURL = resolveBaseURL();

export const api = axios.create({
  baseURL,
  timeout: 15000,
});

api.interceptors.request.use((cfg) => {
  if (!(cfg as any)._logged) {
    (cfg as any)._logged = true;
    console.debug('[API] ->', cfg.method?.toUpperCase(), baseURL + (cfg.url || ''));
  }
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (e) => {
    const url = e.config ? baseURL + (e.config.url || '') : 'unknown';
    console.error('[API ERROR]', url, e.message, e.response?.status, e.response?.data);
    return Promise.reject(e);
  }
);

export const __API_BASE__ = baseURL;
