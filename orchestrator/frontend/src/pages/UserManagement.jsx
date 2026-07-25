import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { ArrowLeft, Users, Plus, X, Trash2, Edit2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ENDPOINTS } from '../config/api';
import authService from '../services/authService';
import ToastStack from '../components/ToastStack';

function UserManagement({ onLogout }) {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [toasts, setToasts] = useState([]);

  const [createForm, setCreateForm] = useState({
    username: '', email: '', password: '', role: 'tenant_viewer',
  });

  const tenantName = authService.getTenantName();
  const currentUserRole = authService.getRole();
  const currentUsername = authService.getUsername();

  const addToast = (type, message) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await axios.get(ENDPOINTS.users, { headers: authService.getAuthHeader() });
      setUsers(res.data || []);
    } catch (err) {
      addToast('error', 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await axios.post(ENDPOINTS.users, createForm, {
        headers: { ...authService.getAuthHeader(), 'Content-Type': 'application/json' },
      });
      addToast('success', `User "${createForm.username}" created successfully`);
      setShowCreateModal(false);
      setCreateForm({ username: '', email: '', password: '', role: 'tenant_viewer' });
      fetchUsers();
    } catch (err) {
      addToast('error', err?.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleChangeRole = async (userId, newRole) => {
    try {
      await axios.put(ENDPOINTS.userRole(userId), { role: newRole }, {
        headers: { ...authService.getAuthHeader(), 'Content-Type': 'application/json' },
      });
      addToast('success', 'User role updated');
      fetchUsers();
    } catch (err) {
      addToast('error', err?.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!window.confirm(`Are you sure you want to deactivate user "${username}"?`)) return;
    try {
      await axios.delete(ENDPOINTS.userById(userId), { headers: authService.getAuthHeader() });
      addToast('success', `User "${username}" deactivated`);
      fetchUsers();
    } catch (err) {
      addToast('error', err?.response?.data?.detail || 'Failed to delete user');
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  return (
    <div className="app-shell" style={{ flexDirection: 'column' }}>
      <header className="top-bar glass-surface" style={{ position: 'sticky', top: 0, zIndex: 10 }}>
        <div className="top-left">
          <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={16} />
            <span>Dashboard</span>
          </button>
          <h1 style={{ marginLeft: '1rem' }}>Users — {tenantName || 'Tenant'}</h1>
        </div>
        <div className="top-actions">
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={16} />
            <span>Add User</span>
          </button>
        </div>
      </header>

      <main style={{ padding: '1.5rem', flex: 1, overflow: 'auto' }}>
        <section className="glass-surface" style={{ borderRadius: '1rem', padding: '1.5rem' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem', opacity: 0.5 }}>Loading users…</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                    <th style={{ padding: '1rem 0.5rem' }}>Username</th>
                    <th style={{ padding: '1rem 0.5rem' }}>Email</th>
                    <th style={{ padding: '1rem 0.5rem' }}>Role</th>
                    <th style={{ padding: '1rem 0.5rem' }}>Status</th>
                    <th style={{ padding: '1rem 0.5rem' }}>Last Login</th>
                    <th style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const isSelf = u.username === currentUsername;
                    const isMaster = u.role === 'master_admin';
                    
                    return (
                      <tr key={u.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '1rem 0.5rem', fontWeight: 600 }}>
                          {u.username} {isSelf && <span className="chip" style={{ marginLeft: '0.5rem' }}>You</span>}
                        </td>
                        <td style={{ padding: '1rem 0.5rem', opacity: 0.8 }}>{u.email}</td>
                        <td style={{ padding: '1rem 0.5rem' }}>
                          <select
                            className="input-field"
                            value={u.role}
                            disabled={isSelf || isMaster || (currentUserRole !== 'master_admin' && currentUserRole !== 'tenant_admin')}
                            onChange={(e) => handleChangeRole(u.id, e.target.value)}
                            style={{ padding: '0.25rem', height: 'auto', minHeight: 'auto', backgroundColor: 'transparent' }}
                          >
                            <option value="master_admin" disabled>Master Admin</option>
                            <option value="tenant_admin">Tenant Admin</option>
                            <option value="tenant_viewer">Tenant Viewer</option>
                          </select>
                        </td>
                        <td style={{ padding: '1rem 0.5rem' }}>
                          <span className={`chip compliance-${u.is_active ? 'success' : 'danger'}`}>
                            {u.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td style={{ padding: '1rem 0.5rem', opacity: 0.6, fontSize: '0.8rem' }}>
                          {u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}
                        </td>
                        <td style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>
                          {!isSelf && !isMaster && u.is_active && (
                            <button
                              className="btn btn-danger"
                              style={{ padding: '0.25rem 0.5rem' }}
                              onClick={() => handleDeleteUser(u.id, u.username)}
                            >
                              <Trash2 size={14} />
                              <span style={{ fontSize: '0.75rem' }}>Delete</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan={6} style={{ padding: '2rem', textAlign: 'center', opacity: 0.5 }}>
                        No users found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal glass-surface" style={{ maxWidth: '400px' }}>
            <h3>Add User</h3>
            <form className="stack-form" onSubmit={handleCreateUser}>
              <input
                className="input-field"
                placeholder="Username"
                value={createForm.username}
                onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                required
              />
              <input
                className="input-field"
                type="email"
                placeholder="Email address"
                value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                required
              />
              <input
                className="input-field"
                type="password"
                placeholder="Temporary password"
                value={createForm.password}
                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                required
              />
              <select
                className="input-field"
                value={createForm.role}
                onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}
              >
                <option value="tenant_viewer">Tenant Viewer</option>
                <option value="tenant_admin">Tenant Admin</option>
              </select>

              <div className="modal-actions">
                <button className="btn btn-secondary" type="button" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" type="submit">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))} />
    </div>
  );
}

export default UserManagement;
