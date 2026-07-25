import axios from 'axios';
import { ENDPOINTS } from '../config/api';

const ACCESS_TOKEN_KEY = 'ipsec_admin_access_token';
const ROLE_KEY = 'ipsec_user_role';
const TENANT_NAME_KEY = 'ipsec_tenant_name';
const USERNAME_KEY = 'ipsec_username';

let accessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY);

axios.interceptors.request.use((config) => {
  if (accessToken && config?.headers && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

const authService = {
  async login(username, password, totpCode) {
    const body = new URLSearchParams();
    body.append('username', username);
    body.append('password', password);
    body.append('grant_type', 'password');

    if (totpCode) {
      body.append('totp_code', totpCode);
    }

    const response = await axios.post(ENDPOINTS.login, body, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    accessToken = response.data.access_token;
    sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);

    // Store role and tenant info
    if (response.data.role) {
      sessionStorage.setItem(ROLE_KEY, response.data.role);
    }
    if (response.data.tenant_name) {
      sessionStorage.setItem(TENANT_NAME_KEY, response.data.tenant_name);
    }
    sessionStorage.setItem(USERNAME_KEY, username);

    return {
      access_token: response.data.access_token,
      token_type: response.data.token_type,
      role: response.data.role,
      tenant_name: response.data.tenant_name,
    };
  },

  getAuthHeader() {
    if (!accessToken) {
      return {};
    }
    return { Authorization: `Bearer ${accessToken}` };
  },

  getRole() {
    return sessionStorage.getItem(ROLE_KEY) || null;
  },

  getTenantName() {
    return sessionStorage.getItem(TENANT_NAME_KEY) || null;
  },

  getUsername() {
    return sessionStorage.getItem(USERNAME_KEY) || null;
  },

  isMasterAdmin() {
    return this.getRole() === 'master_admin';
  },

  isTenantAdmin() {
    return this.getRole() === 'tenant_admin';
  },

  isTenantViewer() {
    return this.getRole() === 'tenant_viewer';
  },

  canWrite() {
    const role = this.getRole();
    return role === 'master_admin' || role === 'tenant_admin';
  },

  logout() {
    accessToken = null;
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    sessionStorage.removeItem(ROLE_KEY);
    sessionStorage.removeItem(TENANT_NAME_KEY);
    sessionStorage.removeItem(USERNAME_KEY);
    window.location.assign('/login');
  },

  isAuthenticated() {
    return Boolean(accessToken);
  },
};

export default authService;
