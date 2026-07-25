import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import TenantAdminLogin from './pages/TenantAdminLogin';
import Dashboard from './pages/Dashboard';
import LandingPage from './pages/LandingPage';
import MasterAdminLogin from './pages/MasterAdminLogin';
import MasterAdminDashboard from './pages/MasterAdminDashboard';
import UserManagement from './pages/UserManagement';
import authService from './services/authService';

function App() {
  const [authenticated, setAuthenticated] = useState(authService.isAuthenticated());

  const handleLogin = () => {
    setAuthenticated(true);
  };

  const handleLogout = () => {
    authService.logout();
    setAuthenticated(false);
  };
  
  const handleMasterLogout = () => {
    localStorage.removeItem('master_admin_username');
    localStorage.removeItem('master_admin_password');
    localStorage.removeItem('master_admin_totp');
    window.location.href = '/_master_admin';
  };

  const isMasterAuthenticated = () => {
     return !!localStorage.getItem('master_admin_totp');
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        
        {/* Tenant Admin Routes */}
        <Route 
          path="/_tenent_admin" 
          element={!authenticated ? <TenantAdminLogin onLogin={handleLogin} /> : <Navigate to="/_tenent_admin/dashboard" />} 
        />
        <Route 
          path="/_tenent_admin/dashboard"
          element={authenticated ? <Dashboard onLogout={handleLogout} /> : <Navigate to="/_tenent_admin" />} 
        />
        <Route 
          path="/_tenent_admin/users"
          element={
            authenticated && authService.canWrite() 
              ? <UserManagement onLogout={handleLogout} /> 
              : <Navigate to={authenticated ? "/_tenent_admin/dashboard" : "/_tenent_admin"} />
          } 
        />

        {/* Master Admin Routes */}
        <Route 
          path="/_master_admin"
          element={!isMasterAuthenticated() ? <MasterAdminLogin /> : <Navigate to="/_master_admin/dashboard" />} 
        />
        <Route 
          path="/_master_admin/dashboard"
          element={isMasterAuthenticated() ? <MasterAdminDashboard onLogout={handleMasterLogout} /> : <Navigate to="/_master_admin" />} 
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
