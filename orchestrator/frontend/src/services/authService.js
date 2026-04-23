import axios from 'axios';
import { ENDPOINTS } from '../config/api';

const ACCESS_TOKEN_KEY = 'ipsec_admin_access_token';
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
    return {
      access_token: response.data.access_token,
      token_type: response.data.token_type,
    };
  },

  getAuthHeader() {
    if (!accessToken) {
      return {};
    }
    return { Authorization: `Bearer ${accessToken}` };
  },

  logout() {
    accessToken = null;
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    window.location.assign('/login');
  },

  isAuthenticated() {
    return Boolean(accessToken);
  },
};

export default authService;
