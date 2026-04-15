export const API_BASE = 'https://ipsec-lcir.onrender.com';

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
