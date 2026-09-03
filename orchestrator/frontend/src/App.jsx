import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import LandingPage from './pages/LandingPage';
import authService from './services/authService';
import Settings from './pages/Settings';
import ProfileCard from './pages/Profile';
import ToastStack from './components/ToastStack';
import CyberBackground from './components/CyberBackground';
import './styles/theme.css';
import './styles/global.css';
import './styles/glass.css';
import './styles/toast.css';

function App() {
  const [authenticated, setAuthenticated] = useState(authService.isAuthenticated());
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  };

  const dismissToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  const handleLogin = () => {
    setAuthenticated(true);
  };

  const handleLogout = () => {
    authService.logout();
    setAuthenticated(false);
  };

  return (
    <Router>
      <CyberBackground />
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
        <Route path="/settings" element={<Settings addToast={addToast} />} />
        <Route path="/profile" element={<ProfileCard />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </Router>
  );
}

export default App;
