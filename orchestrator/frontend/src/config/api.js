const DEV_DEFAULT_BASE = 'http://localhost:8000';
const configuredBase = (import.meta.env.VITE_API_URL || '').trim();

// In production (Vercel), prefer same-origin paths and proxy via vercel.json rewrites.
// This avoids browser CORS edge cases from cross-origin requests.
export const API_BASE = import.meta.env.PROD
  ? ''
  : (configuredBase || DEV_DEFAULT_BASE);

export const ENDPOINTS = {
  // Auth
  login: `${API_BASE}/api/auth/login`,
  totpSetup: `${API_BASE}/api/auth/totp/setup`,
  totpVerify: `${API_BASE}/api/auth/totp/verify`,

  // Devices
  devices: `${API_BASE}/api/devices/`,
  enrollDevice: `${API_BASE}/api/devices/enroll`,
  registerDevice: `${API_BASE}/api/devices/register`,
  deviceById: (id) => `${API_BASE}/api/devices/${id}`,
  deviceConfig: (id, os) => `${API_BASE}/api/devices/${id}/config${os ? `?os_type=${os}` : ''}`,
  deviceHeartbeat: (id) => `${API_BASE}/api/devices/${id}/heartbeat`,
  deviceCompliance: (id) => `${API_BASE}/api/devices/${id}/compliance`,

  // Policies
  policies: `${API_BASE}/api/policies/`,
  policyById: (id) => `${API_BASE}/api/policies/${id}`,
  uploadPolicy: `${API_BASE}/api/policies/upload`,
  assignPolicy: (policyId, deviceId) => `${API_BASE}/api/policies/${policyId}/assign/${deviceId}`,
  unassignPolicy: (deviceId) => `${API_BASE}/api/policies/unassign/${deviceId}`,

  // Health
  ping: `${API_BASE}/api/ping`,
  health: `${API_BASE}/health`,
};
