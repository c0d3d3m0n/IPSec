import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  ArrowLeft,
  Building2,
  Monitor,
  Users,
  ShieldCheck,
  Plus,
  X,
  ToggleLeft,
  ToggleRight,
  Activity,
  TrendingUp,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ENDPOINTS } from '../config/api';

import ToastStack from '../components/ToastStack';

function MasterAdminDashboard({ onLogout }) {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toasts, setToasts] = useState([]);

  const [createForm, setCreateForm] = useState({
    name: '', slug: '', plan: 'free', max_devices: 5, max_users: 2,
    contact_email: '', admin_username: '', admin_email: '', admin_password: '',
  });

  const addToast = (type, message) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get(ENDPOINTS.adminPlatformStats, { headers: authService.getAuthHeader() });
      setStats(res.data);
    } catch (err) {
      addToast('error', 'Failed to fetch platform stats');
    }
  };

  const fetchTenants = async () => {
    try {
      const res = await axios.get(ENDPOINTS.adminTenants, { headers: authService.getAuthHeader() });
      setTenants(res.data || []);
    } catch (err) {
      addToast('error', 'Failed to fetch tenants');
    }
  };

  const fetchTenantDetail = async (tenantId) => {
    try {
      const res = await axios.get(ENDPOINTS.adminTenantById(tenantId), { headers: authService.getAuthHeader() });
      setSelectedTenant(res.data);
    } catch (err) {
      addToast('error', 'Failed to fetch tenant detail');
    }
  };

  const handleCreateTenant = async (e) => {
    e.preventDefault();
    try {
      await axios.post(ENDPOINTS.adminTenants, createForm, {
        headers: { ...authService.getAuthHeader(), 'Content-Type': 'application/json' },
      });
      addToast('success', `Tenant "${createForm.name}" created successfully`);
      setShowCreateModal(false);
      setCreateForm({
        name: '', slug: '', plan: 'free', max_devices: 5, max_users: 2,
        contact_email: '', admin_username: '', admin_email: '', admin_password: '',
      });
      fetchTenants();
      fetchStats();
    } catch (err) {
      addToast('error', err?.response?.data?.detail || 'Failed to create tenant');
    }
  };

  const handleToggleActive = async (tenant) => {
    try {
      await axios.put(ENDPOINTS.adminTenantById(tenant.id), { is_active: !tenant.is_active }, {
        headers: { ...authService.getAuthHeader(), 'Content-Type': 'application/json' },
      });
      addToast('success', `Tenant "${tenant.name}" ${tenant.is_active ? 'deactivated' : 'activated'}`);
      fetchTenants();
      fetchStats();
    } catch (err) {
      addToast('error', 'Failed to toggle tenant status');
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchStats(), fetchTenants()]).finally(() => setLoading(false));
  }, []);

  const statCards = stats ? [
    { label: 'Total Tenants', value: stats.total_tenants, icon: Building2, tone: 'primary' },
    { label: 'Active Tenants', value: stats.active_tenants, icon: Activity, tone: 'success' },
    { label: 'Total Devices', value: stats.total_devices, icon: Monitor, tone: 'primary' },
    { label: 'Active Devices', value: stats.active_devices, icon: TrendingUp, tone: 'success' },
    { label: 'Compliance Rate', value: `${stats.compliance_rate}%`, icon: ShieldCheck, tone: stats.compliance_rate >= 80 ? 'success' : 'danger' },
    { label: 'Violations Today', value: stats.violations_today, icon: ShieldCheck, tone: stats.violations_today > 0 ? 'danger' : 'neutral' },
  ] : [];

  return (
    <div className="app-shell" style={{ flexDirection: 'column' }}>
      <header className="top-bar glass-surface" style={{ position: 'sticky', top: 0, zIndex: 10 }}>
        <div className="top-left">
          <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={16} />
            <span>Dashboard</span>
          </button>
          <h1 style={{ marginLeft: '1rem' }}>Platform Admin</h1>
        </div>
        <div className="top-actions">
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={16} />
            <span>Create Tenant</span>
          </button>
        </div>
      </header>

      <main style={{ padding: '1.5rem', flex: 1, overflow: 'auto' }}>
        {/* Stats Cards */}
        {stats && (
          <div className="summary-grid" style={{ marginBottom: '2rem' }}>
            {statCards.map((card) => {
              const Icon = card.icon;
              return (
                <article key={card.label} className={`summary-card glass-surface tone-${card.tone}`}>
                  <div className="summary-icon"><Icon size={22} /></div>
                  <div className="summary-value">{card.value}</div>
                  <div className="summary-label">{card.label}</div>
                </article>
              );
            })}
          </div>
        )}

        {/* Tenants Table */}
        <section className="glass-surface" style={{ borderRadius: '1rem', padding: '1.5rem' }}>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Tenants</h2>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem', opacity: 0.5 }}>Loading…</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Name</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Plan</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Devices</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Users</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Policies</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Compliance</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Status</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tenants.map((t) => {
                    const compRate = t.device_count > 0 ? Math.round(t.compliant_device_count / t.device_count * 100) : 0;
                    return (
                      <tr
                        key={t.id}
                        style={{
                          borderBottom: '1px solid rgba(255,255,255,0.05)',
                          cursor: 'pointer',
                          transition: 'background 0.2s',
                        }}
                        onClick={() => fetchTenantDetail(t.id)}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>{t.name}</td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>
                          <span className={`chip os-${t.plan}`}>{t.plan}</span>
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>{t.device_count} / {t.max_devices}</td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>{t.user_count} / {t.max_users}</td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>{t.policy_count}</td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>
                          <span className={`chip compliance-${compRate >= 80 ? 'success' : compRate > 0 ? 'danger' : 'neutral'}`}>
                            {compRate}%
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>
                          <span className={`chip compliance-${t.is_active ? 'success' : 'danger'}`}>
                            {t.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={(e) => { e.stopPropagation(); handleToggleActive(t); }}
                          >
                            {t.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                            <span>{t.is_active ? 'Deactivate' : 'Activate'}</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {tenants.length === 0 && (
                    <tr>
                      <td colSpan={8} style={{ padding: '2rem', textAlign: 'center', opacity: 0.5 }}>
                        No tenants yet. Create one to get started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Tenant Detail Panel */}
        {selectedTenant && (
          <section className="glass-surface" style={{ borderRadius: '1rem', padding: '1.5rem', marginTop: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.1rem' }}>{selectedTenant.name} — Detail</h2>
              <button className="icon-btn" onClick={() => setSelectedTenant(null)}><X size={18} /></button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
              <div className="glass-surface" style={{ padding: '1rem', borderRadius: '0.75rem', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{selectedTenant.compliance_summary?.total_devices || 0}</div>
                <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Total Devices</div>
              </div>
              <div className="glass-surface" style={{ padding: '1rem', borderRadius: '0.75rem', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{selectedTenant.compliance_summary?.compliant || 0}</div>
                <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Compliant</div>
              </div>
              <div className="glass-surface" style={{ padding: '1rem', borderRadius: '0.75rem', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{selectedTenant.compliance_summary?.violations_24h || 0}</div>
                <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Violations (24h)</div>
              </div>
            </div>

            {selectedTenant.users?.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>Users</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {selectedTenant.users.map((u) => (
                    <span key={u.id} className="chip" style={{ padding: '0.25rem 0.75rem' }}>
                      {u.username} ({u.role})
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedTenant.devices?.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>Devices</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {selectedTenant.devices.map((d) => (
                    <span key={d.id} className={`chip compliance-${d.latest_compliance === true ? 'success' : d.latest_compliance === false ? 'danger' : 'neutral'}`}>
                      {d.hostname || d.enrollment_number || `Device ${d.id}`} — {d.status}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </main>

      {/* Create Tenant Modal */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal glass-surface" style={{ maxWidth: '480px' }}>
            <h3>Create Tenant</h3>
            <form className="stack-form" onSubmit={handleCreateTenant}>
              <input className="input-field" placeholder="Company name" value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} required />
              <input className="input-field" placeholder="Slug (url-safe, e.g. acme-corp)" value={createForm.slug} onChange={(e) => setCreateForm({ ...createForm, slug: e.target.value })} required />
              <select className="input-field" value={createForm.plan} onChange={(e) => setCreateForm({ ...createForm, plan: e.target.value })}>
                <option value="free">Free</option>
                <option value="pro">Pro</option>
                <option value="enterprise">Enterprise</option>
              </select>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <input className="input-field" type="number" placeholder="Max devices" value={createForm.max_devices} onChange={(e) => setCreateForm({ ...createForm, max_devices: parseInt(e.target.value) || 5 })} style={{ flex: 1 }} />
                <input className="input-field" type="number" placeholder="Max users" value={createForm.max_users} onChange={(e) => setCreateForm({ ...createForm, max_users: parseInt(e.target.value) || 2 })} style={{ flex: 1 }} />
              </div>
              <input className="input-field" type="email" placeholder="Contact email (optional)" value={createForm.contact_email} onChange={(e) => setCreateForm({ ...createForm, contact_email: e.target.value })} />

              <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)', margin: '0.5rem 0' }} />
              <p className="sub-text" style={{ margin: 0 }}>First Admin User</p>

              <input className="input-field" placeholder="Admin username" value={createForm.admin_username} onChange={(e) => setCreateForm({ ...createForm, admin_username: e.target.value })} required />
              <input className="input-field" type="email" placeholder="Admin email" value={createForm.admin_email} onChange={(e) => setCreateForm({ ...createForm, admin_email: e.target.value })} required />
              <input className="input-field" type="password" placeholder="Admin password" value={createForm.admin_password} onChange={(e) => setCreateForm({ ...createForm, admin_password: e.target.value })} required />

              <div className="modal-actions">
                <button className="btn btn-secondary" type="button" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button className="btn btn-primary" type="submit">Create Tenant</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))} />
    </div>
  );
}

export default MasterAdminDashboard;
