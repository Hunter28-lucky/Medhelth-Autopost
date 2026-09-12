/**
 * Global authenticated API interceptor for Developer Krish Goswami.
 * Transparently attaches Bearer token to all /api/ endpoints.
 */

const originalFetch = window.fetch;

window.fetch = async function (resource, config = {}) {
  const url = typeof resource === 'string' ? resource : resource?.url || '';
  
  if (url.startsWith('/api/') || url.includes('/api/')) {
    const token = localStorage.getItem('pulse_dev_token');
    if (token) {
      config = config || {};
      const headers = new Headers(config.headers || {});
      if (!headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      config.headers = headers;
    }
  }

  const response = await originalFetch(resource, config);

  if (response.status === 401 && !url.includes('/api/auth/login')) {
    console.warn('[Security] Unauthorized developer API call. Session expired or missing.');
    window.dispatchEvent(new CustomEvent('pulse_auth_required'));
  }

  return response;
};

export const getDeveloperToken = () => localStorage.getItem('pulse_dev_token');
export const setDeveloperToken = (token) => localStorage.setItem('pulse_dev_token', token);
export const removeDeveloperToken = () => localStorage.removeItem('pulse_dev_token');
export const authFetch = (resource, config = {}) => fetch(resource, config);
