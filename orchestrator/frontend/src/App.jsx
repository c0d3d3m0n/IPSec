import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
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
        <Route 
          path="/login" 
          element={!authenticated ? <Login onLogin={handleLogin} /> : <Navigate to="/" />} 
        />
        <Route 
          path="/" 
          element={authenticated ? <Dashboard onLogout={handleLogout} /> : <Navigate to="/login" />} 
        />
      </Routes>
    </Router>
  );
}

export default App;
