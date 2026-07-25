const DEV_DEFAULT_BASE = 'http://localhost:8000';
const configuredBase = (import.meta.env.VITE_API_URL || '').trim().replace(/\/$/, '');

// In production, default directly to the API subdomain unless VITE_API_URL overrides it.
export const API_BASE = configuredBase || (import.meta.env.PROD
  ? 'https://api.ipsecvault.tech'
  : DEV_DEFAULT_BASE);

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

  // Admin (master_admin only)
  adminTenants: `${API_BASE}/api/admin/tenants/`,
  adminTenantById: (id) => `${API_BASE}/api/admin/tenants/${id}`,
  adminPlatformStats: `${API_BASE}/api/admin/platform/stats`,

  // Users
  users: `${API_BASE}/api/users/`,
  userById: (id) => `${API_BASE}/api/users/${id}`,
  userRole: (id) => `${API_BASE}/api/users/${id}/role`,
  userMe: `${API_BASE}/api/users/me`,

  // Health
  ping: `${API_BASE}/api/ping`,
  health: `${API_BASE}/health`,
};
