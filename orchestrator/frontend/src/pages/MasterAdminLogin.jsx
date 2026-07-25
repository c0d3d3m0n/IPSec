import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function MasterAdminLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  
  const [step, setStep] = useState('login'); // 'login' | 'totp' | 'setup_totp'
  const [setupData, setSetupData] = useState(null);
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();

  const getBasicAuthHeader = () => {
    return 'Basic ' + btoa(`${username}:${password}`);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const authHeader = getBasicAuthHeader();
      const res = await fetch('/api/_master_admin/totp/status', {
        headers: {
          'Authorization': authHeader
        }
      });
      
      if (!res.ok) {
        throw new Error('Invalid master admin credentials');
      }

      const data = await res.json();
      
      if (data.totp_enabled) {
        setStep('totp');
      } else {
        // Fetch setup data
        const setupRes = await fetch('/api/_master_admin/totp/setup', {
          method: 'POST',
          headers: { 'Authorization': authHeader }
        });
        const sData = await setupRes.json();
        setSetupData(sData);
        setStep('setup_totp');
      }

    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTotpSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const authHeader = getBasicAuthHeader();
      
      if (step === 'setup_totp') {
        const res = await fetch('/api/_master_admin/totp/verify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authHeader
          },
          body: JSON.stringify({ code: totpCode, secret: setupData.secret })
        });
        
        if (!res.ok) {
          throw new Error('Invalid TOTP code during setup');
        }
      } else {
        // Just verify standard TOTP header
        const res = await fetch('/api/_master_admin/tenants/', {
          headers: {
            'Authorization': authHeader,
            'X-TOTP-Code': totpCode
          }
        });
        
        if (res.status === 401 || res.status === 403) {
          throw new Error('Invalid TOTP code');
        }
      }

      // Success
      localStorage.setItem('master_admin_username', username);
      localStorage.setItem('master_admin_password', password);
      localStorage.setItem('master_admin_totp', totpCode);
      
      navigate('/_master_admin/dashboard');

    } catch (err) {
      setError(err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white dark:bg-slate-800 p-8 rounded-xl shadow-2xl border border-gray-100 dark:border-slate-700">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">
            Master Admin Portal
          </h2>
        </div>
        
        {error && (
          <div className="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 p-4 rounded-md">
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </div>
        )}

        {step === 'login' && (
          <form className="mt-8 space-y-6" onSubmit={handleLogin}>
            <div className="space-y-4">
              <div>
                <input
                  type="text"
                  required
                  className="appearance-none relative block w-full px-3 py-3 border border-gray-300 dark:border-slate-600 placeholder-gray-500 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm dark:bg-slate-700 transition-all duration-200"
                  placeholder="Master Admin Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
              <div>
                <input
                  type="password"
                  required
                  className="appearance-none relative block w-full px-3 py-3 border border-gray-300 dark:border-slate-600 placeholder-gray-500 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm dark:bg-slate-700 transition-all duration-200"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 shadow-md"
              >
                {loading ? 'Authenticating...' : 'Sign In'}
              </button>
            </div>
          </form>
        )}

        {step === 'setup_totp' && (
          <form className="mt-8 space-y-6" onSubmit={handleTotpSubmit}>
            <div className="text-center">
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                First time login requires setting up Two-Factor Authentication. Scan this QR code with Google Authenticator or Authy.
              </p>
              {setupData?.qr_base64 && (
                <img src={`data:image/png;base64,${setupData.qr_base64}`} alt="TOTP QR Code" className="mx-auto border-4 border-white rounded-lg shadow-lg mb-4" />
              )}
              <p className="text-xs font-mono bg-gray-100 dark:bg-slate-700 p-2 rounded break-all select-all">
                {setupData?.secret}
              </p>
            </div>
            
            <div>
              <input
                type="text"
                required
                className="appearance-none relative block w-full px-3 py-3 border border-gray-300 dark:border-slate-600 placeholder-gray-500 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm dark:bg-slate-700 transition-all duration-200 text-center tracking-widest text-xl"
                placeholder="000000"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                maxLength={6}
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-all duration-200 shadow-md"
            >
              Verify & Complete Setup
            </button>
          </form>
        )}

        {step === 'totp' && (
          <form className="mt-8 space-y-6" onSubmit={handleTotpSubmit}>
            <div className="text-center">
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                Enter your Authenticator Code
              </p>
            </div>
            <div>
              <input
                type="text"
                required
                autoFocus
                className="appearance-none relative block w-full px-3 py-3 border border-gray-300 dark:border-slate-600 placeholder-gray-500 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm dark:bg-slate-700 transition-all duration-200 text-center tracking-widest text-xl"
                placeholder="000000"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                maxLength={6}
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-all duration-200 shadow-md"
            >
              Verify
            </button>
          </form>
        )}

      </div>
    </div>
  );
}

export default MasterAdminLogin;
