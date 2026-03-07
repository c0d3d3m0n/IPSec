import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Plus, RefreshCw, LogOut, LayoutDashboard, 
  Smartphone, Shield, Power, Server, Cpu
} from 'lucide-react';

function Dashboard({ onLogout }) {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  
  // Registration Form
  const [enrollNo, setEnrollNo] = useState('');
  const [enrollToken, setEnrollToken] = useState('');

  const token = localStorage.getItem('token');
  const apiBaseUrl = import.meta.env.VITE_API_URL || ''; 
  const api = axios.create({
    baseURL: apiBaseUrl + '/api',
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const resp = await api.get('/devices/');
      setDevices(resp.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await api.post('/devices/register', {
        enrollment_number: enrollNo,
        enrollment_token: enrollToken
      });
      setShowModal(false);
      setEnrollNo('');
      setEnrollToken('');
      fetchDevices();
    } catch (err) {
      alert(err.response?.data?.detail || 'Registration failed');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>
      {/* Sidebar */}
      <div style={{ 
        width: '280px', 
        borderRight: '1px solid var(--glass-border)', 
        padding: '2rem',
        display: 'flex',
        flexDirection: 'column',
        background: 'rgba(15, 23, 42, 0.5)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '3rem' }}>
          <div style={{ padding: '8px', background: 'var(--primary)', borderRadius: '10px' }}>
            <Shield size={24} color="white" />
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>IPsec Console</h2>
        </div>

        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '12px', 
            padding: '12px', 
            background: 'rgba(99, 102, 241, 0.1)', 
            borderRadius: '12px',
            color: 'var(--primary)',
            fontWeight: 500
          }}>
            <LayoutDashboard size={20} />
            Overview
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <Server size={20} />
            Policies
          </div>
        </nav>

        <button onClick={onLogout} style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '12px', 
          padding: '12px', 
          color: 'var(--danger)', 
          background: 'none', 
          border: 'none', 
          cursor: 'pointer',
          fontWeight: 500
        }}>
          <LogOut size={20} />
          Sign Out
        </button>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: '3rem', position: 'relative' }}>
        <div className="glow" style={{ top: '-10%', right: '10%', width: '600px', height: '600px', background: 'var(--accent)', opacity: 0.1 }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
          <div>
            <h1 style={{ fontSize: '2.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Fleet Manager</h1>
            <p style={{ color: 'var(--text-secondary)' }}>Monitoring {devices.length} network endpoints across all platforms</p>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button onClick={fetchDevices} className="btn" style={{ background: 'var(--glass)', border: '1px solid var(--glass-border)', color: 'white' }}>
              <RefreshCw size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
              Refresh
            </button>
            <button onClick={() => setShowModal(true)} className="btn btn-primary">
              <Plus size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
              Pre-activate Device
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
          {[
            { label: 'Active Endpoints', val: devices.filter(d => d.status === 'ACTIVE').length, icon: Power, color: 'var(--success)' },
            { label: 'Pending Setup', val: devices.filter(d => d.status === 'PENDING').length, icon: Smartphone, color: 'var(--primary)' },
            { label: 'Revoked/Faulty', val: devices.filter(d => d.status === 'REVOKED').length, icon: Cpu, color: 'var(--danger)' }
          ].map((stat, i) => (
            <div key={i} className="glass-card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
              <div style={{ padding: '12px', background: `${stat.color}15`, color: stat.color, borderRadius: '12px' }}>
                <stat.icon size={28} />
              </div>
              <div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{stat.label}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{stat.val}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Device Table */}
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ background: 'rgba(255,255,255,0.02)' }}>
              <tr>
                {['Identifier', 'Platform', 'Public IP', 'Status', 'Last Seen'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {devices.map((device) => (
                <tr key={device.id} style={{ borderTop: '1px solid var(--glass-border)', transition: 'background 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'} onMouseLeave={(e) => e.currentTarget.style.background = 'none'}>
                  <td style={{ padding: '1.25rem 1.5rem' }}>
                    <div style={{ fontWeight: 600 }}>{device.enrollment_number}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{device.hostname || 'Unregistered'}</div>
                  </td>
                  <td style={{ padding: '1.25rem 1.5rem' }}>{device.os_type || 'N/A'}</td>
                  <td style={{ padding: '1.25rem 1.5rem', fontFamily: 'monospace' }}>{device.public_ip || '---.---.---.---'}</td>
                  <td style={{ padding: '1.25rem 1.5rem' }}>
                    <span style={{ 
                      padding: '4px 10px', 
                      borderRadius: '100px', 
                      fontSize: '0.75rem', 
                      fontWeight: 600,
                      background: device.status === 'ACTIVE' ? 'var(--success)20' : device.status === 'PENDING' ? 'var(--primary)20' : 'var(--danger)20',
                      color: device.status === 'ACTIVE' ? 'var(--success)' : device.status === 'PENDING' ? 'var(--primary)' : 'var(--danger)'
                    }}>
                      {device.status}
                    </span>
                  </td>
                  <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    {device.last_seen ? new Date(device.last_seen).toLocaleString() : 'Never'}
                  </td>
                </tr>
              ))}
              {devices.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>No devices found. Pre-activate a device to get started.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, backdropFilter: 'blur(4px)' }}>
          <div className="glass-card" style={{ padding: '2.5rem', width: '100%', maxWidth: '400px', background: '#0f172a' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Pre-activate Device</h2>
            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'block' }}>Enrollment Number (e.g. EP-001)</label>
                <input className="input-field" value={enrollNo} onChange={e => setEnrollNo(e.target.value)} required />
              </div>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'block' }}>Secret Activation Token</label>
                <input className="input-field" type="password" value={enrollToken} onChange={e => setEnrollToken(e.target.value)} required />
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setShowModal(false)} className="btn" style={{ flex: 1, background: 'rgba(255,255,255,0.05)', color: 'white' }}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Register</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
