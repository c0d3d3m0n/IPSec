import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Plus, RefreshCw, LogOut, LayoutDashboard, 
  Smartphone, Shield, Power, Server, Cpu,
  Settings, ChevronRight, CheckCircle2, Trash2
} from 'lucide-react';

function Dashboard({ onLogout }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [devices, setDevices] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Modals
  const [showDeviceModal, setShowDeviceModal] = useState(false);
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  
  // Registration Form
  const [enrollNo, setEnrollNo] = useState('');
  const [enrollToken, setEnrollToken] = useState('');

  // JSON Upload State
  const [uploadFile, setUploadFile] = useState(null);

  const token = localStorage.getItem('token');
  const apiBaseUrl = import.meta.env.VITE_API_URL || ''; 
  const api = axios.create({
    baseURL: apiBaseUrl + '/api',
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [devResp, polResp] = await Promise.all([
        api.get('/devices/'),
        api.get('/policies/')
      ]);
      setDevices(devResp.data);
      setPolicies(polResp.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await api.post('/devices/register', {
        enrollment_number: enrollNo.trim(),
        enrollment_token: enrollToken.trim()
      });
      setShowDeviceModal(false);
      setEnrollNo('');
      setEnrollToken('');
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Registration failed');
    }
  };

  const handleUploadJson = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;

    const formData = new FormData();
    formData.append('file', uploadFile);

    try {
      const resp = await api.post('/policies/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert(resp.data.message);
      setShowPolicyModal(false);
      setUploadFile(null);
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Policy upload failed');
    }
  };

  const handleAssignPolicy = async (deviceId, policyId) => {
    try {
      if (policyId === "") {
        await api.delete(`/policies/unassign/${deviceId}`);
      } else {
        await api.post(`/policies/${policyId}/assign/${deviceId}`);
      }
      fetchData();
    } catch (err) {
      alert('Failed to update policy assignment');
    }
  };

  const handleDeletePolicy = async (id) => {
    if (!window.confirm('Are you sure you want to delete this policy? This will unassign it from all devices.')) return;
    try {
      await api.delete(`/policies/${id}`);
      fetchData();
    } catch (err) {
      alert('Failed to delete policy');
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
          <div 
            onClick={() => setActiveTab('overview')}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              padding: '12px', 
              background: activeTab === 'overview' ? 'rgba(99, 102, 241, 0.1)' : 'transparent', 
              borderRadius: '12px',
              color: activeTab === 'overview' ? 'var(--primary)' : 'var(--text-secondary)',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            <LayoutDashboard size={20} />
            Overview
          </div>
          <div 
            onClick={() => setActiveTab('policies')}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              padding: '12px', 
              background: activeTab === 'policies' ? 'rgba(99, 102, 241, 0.1)' : 'transparent', 
              borderRadius: '12px',
              color: activeTab === 'policies' ? 'var(--primary)' : 'var(--text-secondary)',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
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

        {activeTab === 'overview' ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
              <div>
                <h1 style={{ fontSize: '2.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Fleet Manager</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Monitoring {devices.length} network endpoints</p>
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button 
                  onClick={fetchData} 
                  className="btn" 
                  disabled={loading}
                  style={{ background: 'var(--glass)', border: '1px solid var(--glass-border)', color: 'white', opacity: loading ? 0.7 : 1 }}
                >
                  <RefreshCw size={18} style={{ 
                    marginRight: '8px', 
                    verticalAlign: 'middle',
                    animation: loading ? 'spin 2s linear infinite' : 'none'
                  }} />
                  {loading ? 'Refreshing...' : 'Refresh'}
                </button>
                <button onClick={() => setShowDeviceModal(true)} className="btn btn-primary">
                  <Plus size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                  Pre-activate Device
                </button>
              </div>
            </div>

            {/* Stats Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
              {[
                { 
                  label: 'Online Endpoints', 
                  val: devices.filter(d => d.last_seen && (new Date() - new Date(d.last_seen.endsWith('Z') ? d.last_seen : d.last_seen + 'Z') < 60000)).length, 
                  icon: Power, 
                  color: 'var(--success)' 
                },
                { label: 'Pending Setup', val: devices.filter(d => d.status === 'PENDING').length, icon: Smartphone, color: 'var(--primary)' },
                { label: 'Total Policies', val: policies.length, icon: Shield, color: 'var(--accent)' }
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
                    {['Identifier', 'Platform', 'Status', 'Assigned Policy', 'Actions'].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '1.25rem 1.5rem', color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {devices.map((device) => {
                    const lastSeenStr = device.last_seen ? (device.last_seen.endsWith('Z') ? device.last_seen : device.last_seen + 'Z') : null;
                    const lastSeen = lastSeenStr ? new Date(lastSeenStr) : null;
                    const isOnline = lastSeen && (new Date() - lastSeen < 60000); // 1 minute threshold
                    const status = device.status === 'PENDING' ? 'PENDING' : (isOnline ? 'ONLINE' : 'OFFLINE');

                    return (
                      <tr key={device.id} style={{ borderTop: '1px solid var(--glass-border)' }}>
                        <td style={{ padding: '1.25rem 1.5rem' }}>
                          <div style={{ fontWeight: 600 }}>{device.enrollment_number}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {device.hostname || 'Unregistered'}
                            {isOnline && <span style={{ marginLeft: '8px', color: 'var(--success)', fontSize: '0.6rem' }}>●</span>}
                          </div>
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem' }}>{device.os_type || 'N/A'}</td>
                        <td style={{ padding: '1.25rem 1.5rem' }}>
                          <span style={{ 
                            padding: '4px 10px', 
                            borderRadius: '100px', 
                            fontSize: '0.75rem', 
                            fontWeight: 600,
                            background: status === 'ONLINE' ? 'var(--success)20' : 
                                       status === 'PENDING' ? 'var(--primary)20' : 'var(--danger)20',
                            color: status === 'ONLINE' ? 'var(--success)' : 
                                   status === 'PENDING' ? 'var(--primary)' : 'var(--danger)'
                          }}>
                            {status}
                          </span>
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem' }}>
                        <select 
                          className="input-field" 
                          style={{ padding: '8px', fontSize: '0.85rem' }}
                          value={device.policy_id || ''}
                          onChange={(e) => handleAssignPolicy(device.id, e.target.value)}
                        >
                          <option value="">No Policy</option>
                          {policies.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>
                      </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
              <div>
                <h1 style={{ fontSize: '2.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>IPsec Policies</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Define secure tunnel configurations for your fleet</p>
              </div>
              <button onClick={() => setShowPolicyModal(true)} className="btn btn-primary">
                <Plus size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                Upload Policies JSON
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem' }}>
              {policies.map(policy => (
                <div key={policy.id} className="glass-card" style={{ padding: '2rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                    <div>
                      <h3 style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>{policy.name}</h3>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{policy.description}</p>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <div style={{ padding: '8px', background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', borderRadius: '8px' }}>
                        <CheckCircle2 size={20} />
                      </div>
                      <button 
                        onClick={() => handleDeletePolicy(policy.id)}
                        style={{ padding: '8px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
                      >
                        <Trash2 size={20} />
                      </button>
                    </div>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '12px' }}>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Local Network</div>
                      <div style={{ fontWeight: 500 }}>{policy.config_data?.ipsec_policy?.connections?.[0]?.local_subnet || 'N/A'}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Remote Network</div>
                      <div style={{ fontWeight: 500 }}>{policy.config_data?.ipsec_policy?.connections?.[0]?.remote_subnet || 'N/A'}</div>
                    </div>
                  </div>
                  <div style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    Policy ID: {policy.config_data?.policy_id || policy.name}
                  </div>
                </div>
              ))}
              {policies.length === 0 && (
                <div style={{ gridColumn: 'span 2', padding: '4rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  No policies defined. Create one to start securing your devices.
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Device Registration Modal */}
      {showDeviceModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, backdropFilter: 'blur(4px)' }}>
          <div className="glass-card" style={{ padding: '2.5rem', width: '100%', maxWidth: '400px', background: '#0f172a' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Pre-activate Device</h2>
            <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'block' }}>Enrollment Number</label>
                <input className="input-field" value={enrollNo} onChange={e => setEnrollNo(e.target.value)} required />
              </div>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'block' }}>Secret Activation Token</label>
                <input className="input-field" type="password" value={enrollToken} onChange={e => setEnrollToken(e.target.value)} required />
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setShowDeviceModal(false)} className="btn" style={{ flex: 1, background: 'rgba(255,255,255,0.05)', color: 'white' }}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Register</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Policy JSON Upload Modal */}
      {showPolicyModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, backdropFilter: 'blur(4px)' }}>
          <div className="glass-card" style={{ padding: '2.5rem', width: '100%', maxWidth: '500px', background: '#0f172a' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Upload Policies</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
              Upload a JSON file containing the policies and their device assignments.
            </p>
            <form onSubmit={handleUploadJson} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <input 
                  type="file" 
                  accept=".json,application/json"
                  className="input-field" 
                  onChange={e => setUploadFile(e.target.files[0])} 
                  required 
                />
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => {setShowPolicyModal(false); setUploadFile(null);}} className="btn" style={{ flex: 1, background: 'rgba(255,255,255,0.05)', color: 'white' }}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Upload JSON</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
