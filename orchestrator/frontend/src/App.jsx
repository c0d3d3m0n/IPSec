import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import LandingPage from './pages/LandingPage';
import PlatformAdmin from './pages/PlatformAdmin';
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

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route 
          path="/login" 
          element={!authenticated ? <Login onLogin={handleLogin} /> : <Navigate to="/dashboard" />} 
        />
        <Route 
          path="/dashboard"
          element={authenticated ? <Dashboard onLogout={handleLogout} /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/admin"
          element={
            authenticated && authService.isMasterAdmin() 
              ? <PlatformAdmin onLogout={handleLogout} /> 
              : <Navigate to={authenticated ? "/dashboard" : "/login"} />
          } 
        />
        <Route 
          path="/users"
          element={
            authenticated && authService.canWrite() 
              ? <UserManagement onLogout={handleLogout} /> 
              : <Navigate to={authenticated ? "/dashboard" : "/login"} />
          } 
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
