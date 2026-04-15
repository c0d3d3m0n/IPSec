import axios from 'axios';
import { ENDPOINTS } from '../config/api';

let accessToken = null;

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
    window.location.assign('/login');
  },

  isAuthenticated() {
    return Boolean(accessToken);
  },
};

export default authService;
