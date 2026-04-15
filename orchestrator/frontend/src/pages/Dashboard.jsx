import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Menu,
  Home,
  Monitor,
  ClipboardList,
  BadgeCheck,
  Settings,
  LogOut,
  Upload,
  Plus,
  RefreshCw,
  ShieldAlert,
  Server,
} from 'lucide-react';
import { ENDPOINTS } from '../config/api';
import authService from '../services/authService';
import ToastStack from '../components/ToastStack';

const NAV_ITEMS = [
  { key: 'dashboard', icon: Home, label: 'Dashboard' },
  { key: 'devices', icon: Monitor, label: 'Devices' },
  { key: 'policies', icon: ClipboardList, label: 'Policies' },
  { key: 'compliance', icon: BadgeCheck, label: 'Compliance' },
  { key: 'settings', icon: Settings, label: 'Settings' },
];

function Dashboard({ onLogout }) {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [devices, setDevices] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [complianceByDevice, setComplianceByDevice] = useState({});
  const [selectedComplianceDevice, setSelectedComplianceDevice] = useState(null);

  const [showEnrollModal, setShowEnrollModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showUploadResultModal, setShowUploadResultModal] = useState(false);

  const [uploadResult, setUploadResult] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [toasts, setToasts] = useState([]);

  const [enrollForm, setEnrollForm] = useState({
    enrollment_number: '',
    enrollment_token: '',
    os_fingerprint: '',
    agent_signature: '',
    hostname: '',
    os_type: 'linux',
    public_ip: '',
  });

  const authHeaders = useMemo(() => authService.getAuthHeader(), []);

  const addToast = (type, message) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleApiError = (error, fallback) => {
    const status = error?.response?.status;
    const message = error?.response?.data?.detail || fallback;
    if (status === 401) {
      addToast('error', 'Session expired. Please login again.');
      onLogout();
      return;
    }
    addToast('error', message);
  };

  const pingBackend = async () => {
    try {
      await axios.get(ENDPOINTS.ping);
      setBackendOnline((prev) => {
        if (!prev) {
          addToast('success', 'Backend is online');
        }
        return true;
      });
    } catch {
      setBackendOnline((prev) => {
        if (prev) {
          addToast('error', 'Backend is offline');
        }
        return false;
      });
    }
  };

  const fetchComplianceForDevice = async (deviceId) => {
    try {
      const response = await axios.get(`${ENDPOINTS.deviceCompliance(deviceId)}?limit=10`, {
        headers: authService.getAuthHeader(),
      });
      return response.data || [];
    } catch (error) {
      handleApiError(error, 'Failed to load compliance history');
      return [];
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    await pingBackend();

    try {
      const [devicesResponse, policiesResponse] = await Promise.all([
        axios.get(ENDPOINTS.devices, { headers: authHeaders }),
        axios.get(ENDPOINTS.policies, { headers: authHeaders }),
      ]);

      const deviceList = devicesResponse.data || [];
      setDevices(deviceList);
      setPolicies(policiesResponse.data || []);

      const complianceEntries = await Promise.all(
        deviceList.map(async (device) => ({
          deviceId: device.id,
          records: await fetchComplianceForDevice(device.id),
        }))
      );

      const complianceMap = {};
      complianceEntries.forEach(({ deviceId, records }) => {
        complianceMap[deviceId] = records;
      });
      setComplianceByDevice(complianceMap);

      if (!selectedComplianceDevice && deviceList.length > 0) {
        setSelectedComplianceDevice(deviceList[0].id);
      }
    } catch (error) {
      handleApiError(error, 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    const intervalId = window.setInterval(fetchAllData, 30000);
    return () => window.clearInterval(intervalId);
  }, []);

  const formatRelativeTime = (input) => {
    if (!input) {
      return 'Never';
    }
    const timestamp = new Date(input.endsWith('Z') ? input : `${input}Z`);
    const deltaSeconds = Math.max(0, Math.floor((Date.now() - timestamp.getTime()) / 1000));

    if (deltaSeconds < 60) return `${deltaSeconds}s ago`;
    if (deltaSeconds < 3600) return `${Math.floor(deltaSeconds / 60)} min ago`;
    if (deltaSeconds < 86400) return `${Math.floor(deltaSeconds / 3600)} h ago`;
    return `${Math.floor(deltaSeconds / 86400)} d ago`;
  };

  const formatBytes = (value) => {
    const bytes = Number(value || 0);
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  const getDeviceComplianceInfo = (deviceId) => {
    const records = complianceByDevice[deviceId] || [];
    if (records.length === 0) {
      return { label: 'No data', tone: 'neutral', leakDetected: false };
    }

    const latest = records[0];
    const leakDetected = records.some((r) => r.plaintext_leak_detected);

    if (latest.is_compliant) {
      return { label: 'Compliant', tone: 'success', leakDetected };
    }
    return { label: 'Violations', tone: 'danger', leakDetected };
  };

  const summary = useMemo(() => {
    const total = devices.length;
    const active = devices.filter((d) => d.is_active).length;
    const compliant = devices.filter((d) => (complianceByDevice[d.id]?.[0]?.is_compliant)).length;

    let violations24h = 0;
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    Object.values(complianceByDevice).forEach((records) => {
      (records || []).forEach((record) => {
        const at = new Date(record.timestamp).getTime();
        if (at >= cutoff && !record.is_compliant) {
          violations24h += 1;
        }
      });
    });

    return {
      total,
      active,
      compliant,
      policies: policies.length,
      violations24h,
    };
  }, [devices, complianceByDevice, policies]);

  const handleEnrollDevice = async (event) => {
    event.preventDefault();
    try {
      await axios.post(ENDPOINTS.enrollDevice, enrollForm, {
        headers: {
          ...authService.getAuthHeader(),
          'Content-Type': 'application/json',
        },
      });
      addToast('success', 'Device enrolled successfully');
      setShowEnrollModal(false);
      setEnrollForm({
        enrollment_number: '',
        enrollment_token: '',
        os_fingerprint: '',
        agent_signature: '',
        hostname: '',
        os_type: 'linux',
        public_ip: '',
      });
      fetchAllData();
    } catch (error) {
      handleApiError(error, 'Failed to enroll device');
    }
  };

  const handleAssignPolicy = async (deviceId, policyId) => {
    try {
      if (!policyId) {
        await axios.delete(ENDPOINTS.unassignPolicy(deviceId), {
          headers: authService.getAuthHeader(),
        });
        addToast('success', 'Policy unassigned');
      } else {
        await axios.post(
          ENDPOINTS.assignPolicy(policyId, deviceId),
          {},
          { headers: authService.getAuthHeader() }
        );
        addToast('success', 'Policy assigned');
      }
      fetchAllData();
    } catch (error) {
      handleApiError(error, 'Failed to update policy assignment');
    }
  };

  const handleDeletePolicy = async (policyId) => {
    try {
      await axios.delete(ENDPOINTS.policyById(policyId), {
        headers: authService.getAuthHeader(),
      });
      addToast('success', 'Policy deleted successfully');
      fetchAllData();
    } catch (error) {
      handleApiError(error, 'Failed to delete policy');
    }
  };

  const handleUploadPolicy = async (event) => {
    event.preventDefault();
    if (!uploadFile) {
      addToast('warning', 'Select a JSON file first');
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadFile);

    try {
      const response = await axios.post(ENDPOINTS.uploadPolicy, formData, {
        headers: {
          ...authService.getAuthHeader(),
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadResult(response.data || null);
      setShowUploadResultModal(true);
      setShowUploadModal(false);
      setUploadFile(null);
      addToast('success', 'Policy upload completed');
      fetchAllData();
    } catch (error) {
      const data = error?.response?.data;
      setUploadResult({
        errors: data?.errors || [data?.detail || 'Policy upload failed'],
        warnings: data?.warnings || [],
      });
      setShowUploadResultModal(true);
      handleApiError(error, 'Policy upload failed');
    }
  };

  const getAssignedCount = (policyId) => devices.filter((d) => d.policy_id === policyId).length;

  const renderSidebar = () => (
    <aside className={`sidebar glass-surface ${mobileNavOpen ? 'open' : ''}`}>
      <div className="sidebar-brand">
        <span className="brand-icon" role="img" aria-label="lock">
          🔐
        </span>
        <div>
          <h2>IPsec ZT</h2>
          <small>Zero Trust Console</small>
        </div>
      </div>

      <nav className="nav-list">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.key}
              className={`nav-item ${activeTab === item.key ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(item.key);
                setMobileNavOpen(false);
              }}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="backend-status">
          <span className={`status-dot ${backendOnline ? 'online' : 'offline'}`} />
          <span>{backendOnline ? 'Online' : 'Offline'}</span>
        </div>
        <div className="sidebar-user">admin</div>
        <button className="btn btn-secondary" onClick={onLogout}>
          <LogOut size={16} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );

  const renderSummaryCards = () => {
    const cards = [
      { label: 'Total Devices', value: summary.total, tone: 'primary' },
      { label: 'Active Devices', value: summary.active, tone: 'success' },
      { label: 'Compliant Devices', value: summary.compliant, tone: 'success' },
      { label: 'Policies', value: summary.policies, tone: 'primary' },
      {
        label: 'Violations (24h)',
        value: summary.violations24h,
        tone: summary.violations24h > 0 ? 'danger' : 'neutral',
      },
    ];

    return (
      <div className="summary-grid">
        {cards.map((card) => (
          <article key={card.label} className={`summary-card glass-surface tone-${card.tone}`}>
            <div className="summary-icon"><Server size={22} /></div>
            <div className="summary-value">{card.value}</div>
            <div className="summary-label">{card.label}</div>
          </article>
        ))}
      </div>
    );
  };

  const renderDevices = () => (
    <section className="card-grid two-col">
      {devices.map((device) => {
        const compliance = getDeviceComplianceInfo(device.id);

        return (
          <article key={device.id} className="entity-card glass-surface interactive-card">
            <div className="card-head">
              <div>
                <h3>{device.hostname || device.enrollment_number || `Device ${device.id}`}</h3>
                <div className="mono-text">last_seen: {formatRelativeTime(device.last_seen)}</div>
              </div>
              <span className={`chip os-${(device.os_type || 'unknown').toLowerCase()}`}>{device.os_type || 'unknown'}</span>
            </div>

            <div className="device-meta">
              <div><strong>Status:</strong> {device.status || 'unknown'}</div>
              <div><strong>Active:</strong> {device.is_active ? 'Yes' : 'No'}</div>
              <div>
                <strong>Compliance:</strong>
                <span className={`chip compliance-${compliance.tone}`}>{compliance.label}</span>
              </div>
            </div>

            {compliance.leakDetected ? (
              <div className="leak-alert">⚠ Plaintext leak detected</div>
            ) : null}

            <div className="device-controls">
              <select
                className="input-field"
                value={device.policy_id || ''}
                onChange={(e) => handleAssignPolicy(device.id, e.target.value)}
              >
                <option value="">Select policy</option>
                {policies.map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policy.name}
                  </option>
                ))}
              </select>
              <button className="btn btn-secondary" onClick={() => handleAssignPolicy(device.id, '')}>
                Unassign
              </button>
            </div>
          </article>
        );
      })}
    </section>
  );

  const renderPolicies = () => (
    <section className="card-grid two-col">
      {policies.map((policy) => {
        const targetOS = policy?.config_data?.target?.os || [];
        const crypto = policy?.config_data?.ipsec_policy?.crypto || {};
        const ike = crypto.ike || {};
        const esp = crypto.esp || {};

        return (
          <article key={policy.id} className="entity-card glass-surface interactive-card">
            <div className="card-head">
              <div>
                <h3>{policy.name}</h3>
                <p className="sub-text">{policy.description || 'No description'}</p>
              </div>
              <button className="btn btn-danger" onClick={() => handleDeletePolicy(policy.id)}>
                Delete
              </button>
            </div>

            <div className="policy-meta">
              <div><strong>Version:</strong> {policy?.config_data?.version || 'N/A'}</div>
              <div><strong>Created:</strong> {new Date(policy.created_at).toLocaleString()}</div>
              <div><strong>Assigned Devices:</strong> {getAssignedCount(policy.id)}</div>
            </div>

            <div className="chip-row">
              {targetOS.length ? targetOS.map((os) => (
                <span key={`${policy.id}-${os}`} className={`chip os-${String(os).toLowerCase()}`}>{os}</span>
              )) : <span className="chip os-unknown">No target OS</span>}
            </div>

            <div className="algo-block mono-text">IKE: {ike.encryption || 'N/A'} / {ike.integrity || 'N/A'} / {ike.dh_group || 'N/A'}</div>
            <div className="algo-block mono-text">ESP: {esp.encryption || 'N/A'} / {esp.integrity || 'N/A'} / {esp.dh_group || 'N/A'}</div>
          </article>
        );
      })}
    </section>
  );

  const selectedTimeline = complianceByDevice[selectedComplianceDevice] || [];

  const renderComplianceTimeline = () => (
    <section className="glass-surface timeline-wrap">
      <div className="timeline-head">
        <h3>Compliance Timeline</h3>
        <select
          className="input-field"
          value={selectedComplianceDevice || ''}
          onChange={(e) => setSelectedComplianceDevice(Number(e.target.value) || null)}
        >
          <option value="">Select device</option>
          {devices.map((device) => (
            <option key={device.id} value={device.id}>
              {device.hostname || device.enrollment_number || `Device ${device.id}`}
            </option>
          ))}
        </select>
      </div>

      <div className="timeline-list">
        {selectedTimeline.map((record, index) => {
          const violations = record?.raw_report?.violations || [];
          return (
            <article key={`${record.timestamp}-${index}`} className={`timeline-item ${record.is_compliant ? 'ok' : 'bad'}`}>
              <div className="timeline-top">
                <span className="mono-text">{new Date(record.timestamp).toLocaleString()}</span>
                <span className={`chip compliance-${record.is_compliant ? 'success' : 'danger'}`}>
                  {record.is_compliant ? 'Compliant' : 'Violation'}
                </span>
              </div>
              <div className="timeline-metrics">
                <span>Total encrypted: {formatBytes(record.total_bytes_encrypted)}</span>
                <span>Active SAs: {record.active_sa_count ?? (record.active_sas?.length || 0)}</span>
              </div>
              {violations.length > 0 ? (
                <ul className="violations-list">
                  {violations.map((violation, vIndex) => (
                    <li key={`${record.timestamp}-${vIndex}`}>{String(violation)}</li>
                  ))}
                </ul>
              ) : null}
            </article>
          );
        })}

        {selectedTimeline.length === 0 ? (
          <div className="empty-state">No compliance records found for this device.</div>
        ) : null}
      </div>
    </section>
  );

  const renderContent = () => {
    if (activeTab === 'devices') return renderDevices();
    if (activeTab === 'policies') return renderPolicies();
    if (activeTab === 'compliance') return renderComplianceTimeline();
    if (activeTab === 'settings') {
      return (
        <section className="glass-surface settings-card">
          <h3>Settings</h3>
          <p className="sub-text">Backend: {backendOnline ? 'Online' : 'Offline'}</p>
          <p className="sub-text">Theme: Glassmorphism enabled</p>
        </section>
      );
    }

    return (
      <>
        {renderSummaryCards()}
        <h3 className="section-title">Fleet Devices</h3>
        {renderDevices()}
      </>
    );
  };

  const renderUploadSummary = () => {
    if (!uploadResult) {
      return null;
    }

    const osSummary = uploadResult.os_summary || uploadResult.summary || {};
    const errors = uploadResult.errors || [];
    const warnings = uploadResult.warnings || [];

    return (
      <div className="upload-summary">
        <h4>Upload Summary</h4>
        {Object.keys(osSummary).length > 0 ? (
          <div className="summary-table">
            {Object.entries(osSummary).map(([os, summaryInfo]) => (
              <div key={os} className="summary-row">
                <strong>{os}</strong>
                <span className="mono-text">{JSON.stringify(summaryInfo)}</span>
              </div>
            ))}
          </div>
        ) : null}

        {errors.length > 0 ? (
          <div className="upload-errors">
            <h5>Errors</h5>
            <ul>{errors.map((e, i) => <li key={`e-${i}`}>{String(e)}</li>)}</ul>
          </div>
        ) : null}

        {warnings.length > 0 ? (
          <div className="upload-warnings">
            <h5>Warnings</h5>
            <ul>{warnings.map((w, i) => <li key={`w-${i}`}>{String(w)}</li>)}</ul>
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className="app-shell">
      {renderSidebar()}

      <main className="main-content">
        <header className="top-bar glass-surface">
          <div className="top-left">
            <button className="icon-btn mobile-menu-btn" onClick={() => setMobileNavOpen((prev) => !prev)}>
              <Menu size={20} />
            </button>
            <h1>{NAV_ITEMS.find((item) => item.key === activeTab)?.label || 'Dashboard'}</h1>
          </div>

          <div className="top-actions">
            <button className="btn btn-secondary" onClick={fetchAllData}>
              <RefreshCw size={16} />
              <span>{loading ? 'Refreshing...' : 'Refresh'}</span>
            </button>
            <button className="btn btn-primary" onClick={() => setShowEnrollModal(true)}>
              <Plus size={16} />
              <span>Enroll Device</span>
            </button>
            <button className="btn btn-primary" onClick={() => setShowUploadModal(true)}>
              <Upload size={16} />
              <span>Upload Policy</span>
            </button>
          </div>
        </header>

        {renderContent()}
      </main>

      <nav className="mobile-bottom-nav glass-surface">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={`mobile-${item.key}`}
              className={`mobile-nav-item ${activeTab === item.key ? 'active' : ''}`}
              onClick={() => setActiveTab(item.key)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {showEnrollModal ? (
        <div className="modal-overlay">
          <div className="modal glass-surface">
            <h3>Enroll Device</h3>
            <form className="stack-form" onSubmit={handleEnrollDevice}>
              <input
                className="input-field"
                placeholder="Enrollment number"
                value={enrollForm.enrollment_number}
                onChange={(e) => setEnrollForm((prev) => ({ ...prev, enrollment_number: e.target.value }))}
                required
              />
              <input
                className="input-field"
                placeholder="Enrollment token"
                value={enrollForm.enrollment_token}
                onChange={(e) => setEnrollForm((prev) => ({ ...prev, enrollment_token: e.target.value }))}
                required
              />
              <input
                className="input-field"
                placeholder="OS fingerprint"
                value={enrollForm.os_fingerprint}
                onChange={(e) => setEnrollForm((prev) => ({ ...prev, os_fingerprint: e.target.value }))}
                required
              />
              <input
                className="input-field"
                placeholder="Agent signature"
                value={enrollForm.agent_signature}
                onChange={(e) => setEnrollForm((prev) => ({ ...prev, agent_signature: e.target.value }))}
                required
              />
              <input
                className="input-field"
                placeholder="Hostname"
                value={enrollForm.hostname}
                onChange={(e) => setEnrollForm((prev) => ({ ...prev, hostname: e.target.value }))}
              />
              <input
                className="input-field"
                placeholder="Public IP"
                value={enrollForm.public_ip}
                onChange={(e) => setEnrollForm((prev) => ({ ...prev, public_ip: e.target.value }))}
              />
              <select
                className="input-field"
                value={enrollForm.os_type}
                onChange={(e) => setEnrollForm((prev) => ({ ...prev, os_type: e.target.value }))}
              >
                <option value="linux">linux</option>
                <option value="windows">windows</option>
                <option value="macos">macos</option>
              </select>
              <div className="modal-actions">
                <button className="btn btn-secondary" type="button" onClick={() => setShowEnrollModal(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" type="submit">Submit</button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showUploadModal ? (
        <div className="modal-overlay">
          <div className="modal glass-surface">
            <h3>Upload Policy JSON</h3>
            <form className="stack-form" onSubmit={handleUploadPolicy}>
              <input
                className="input-field"
                type="file"
                accept="application/json,.json"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                required
              />
              <div className="modal-actions">
                <button className="btn btn-secondary" type="button" onClick={() => setShowUploadModal(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary" type="submit">Upload</button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showUploadResultModal ? (
        <div className="modal-overlay">
          <div className="modal glass-surface">
            {renderUploadSummary()}
            <div className="modal-actions">
              <button className="btn btn-primary" type="button" onClick={() => setShowUploadResultModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default Dashboard;
