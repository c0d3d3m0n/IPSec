import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
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
  Shield,
  Activity,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileJson,
  Copy,
} from 'lucide-react';
import { ENDPOINTS } from '../config/api';
import authService from '../services/authService';
import ToastStack from '../components/ToastStack';
import AnimatedCounter from '../components/AnimatedCounter';
import TrustScoreBar from '../components/TrustScoreBar';
import StatusDot from '../components/StatusDot';
import SkeletonLoader from '../components/SkeletonLoader';
import HashDisplay from '../components/HashDisplay';

const NAV_ITEMS = [
  { key: 'dashboard', icon: Home, label: 'Dashboard' },
  { key: 'devices', icon: Monitor, label: 'Devices' },
  { key: 'policies', icon: ClipboardList, label: 'Policies' },
  { key: 'compliance', icon: BadgeCheck, label: 'Compliance' },
  { key: 'settings', icon: Settings, label: 'Settings' },
];

/* Per-card summary icons for visual differentiation */
const SUMMARY_ICONS = [Server, Activity, Shield, ClipboardList, AlertTriangle];

/* ── Framer Motion presets ── */
const fadeUp = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
};

const staggerContainer = {
  animate: { transition: { staggerChildren: 0.06 } },
};

const staggerChild = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] },
};

const modalOverlayVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

const modalCardVariants = {
  initial: { opacity: 0, y: 24, scale: 0.96 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: 24, scale: 0.96 },
  transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
};

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
  const [totpSetupData, setTotpSetupData] = useState(null);
  const [totpCodeInput, setTotpCodeInput] = useState('');
  const [totpLoading, setTotpLoading] = useState(false);
  const [totpVerifying, setTotpVerifying] = useState(false);

  /* Expandable device cards — track which device IDs are expanded */
  const [expandedDevices, setExpandedDevices] = useState({});

  /* Drag-and-drop state for policy upload */
  const [dragActive, setDragActive] = useState(false);

  const [enrollForm, setEnrollForm] = useState({
    enrollment_number: '',
    enrollment_token: '',
    pre_shared_key: '',
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

  const toErrorText = (value, fallback = 'Request failed') => {
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
    if (Array.isArray(value)) {
      const parts = value
        .map((item) => (typeof item === 'string' ? item : JSON.stringify(item)))
        .filter(Boolean);
      return parts.length > 0 ? parts.join('; ') : fallback;
    }
    if (value && typeof value === 'object') {
      if (typeof value.message === 'string' && value.message.trim()) {
        return value.message;
      }
      if (Array.isArray(value.errors) && value.errors.length > 0) {
        return toErrorText(value.errors, fallback);
      }
      return JSON.stringify(value);
    }
    return fallback;
  };

  const normalizeMessages = (value, fallback) => {
    if (Array.isArray(value)) {
      const messages = value.map((v) => toErrorText(v, '')).filter(Boolean);
      return messages.length > 0 ? messages : [fallback];
    }
    if (value === undefined || value === null) {
      return [fallback];
    }
    return [toErrorText(value, fallback)];
  };

  const handleApiError = (error, fallback) => {
    const status = error?.response?.status;
    const message = toErrorText(error?.response?.data?.detail, fallback);
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
      // Compliance endpoint returns { device_id, total_records, records, ... }
      // Extract the records array
      return response.data?.records || [];
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
    if (!input) return 'Never';
    try {
      let date;
      if (input instanceof Date) {
        date = input;
      } else if (typeof input === 'number') {
        date = new Date(input);
      } else {
        const str = String(input).trim();
        if (str.endsWith('Z') || /[+-]\d{2}(:\d{2})?$/.test(str)) {
          date = new Date(str);
        } else if (str.includes('T')) {
          date = new Date(`${str}Z`);
        } else {
          date = new Date(str.replace(' ', 'T') + 'Z');
        }
      }
      const ms = date.getTime();
      if (isNaN(ms)) {
        const raw = new Date(input);
        if (!isNaN(raw.getTime())) {
          date = raw;
        } else {
          return 'Recent';
        }
      }
      const deltaSeconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
      if (deltaSeconds < 60) return `${deltaSeconds}s ago`;
      if (deltaSeconds < 3600) return `${Math.floor(deltaSeconds / 60)}m ago`;
      if (deltaSeconds < 86400) return `${Math.floor(deltaSeconds / 3600)}h ago`;
      return `${Math.floor(deltaSeconds / 86400)}d ago`;
    } catch {
      return 'Recent';
    }
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

  /**
   * Derive a synthetic trust score from compliance history.
   * 100 if all records compliant, minus 10 per violation, minus 30 for leaks.
   */
  const getDeviceTrustScore = (deviceId) => {
    const records = complianceByDevice[deviceId] || [];
    if (records.length === 0) return 50; // Neutral when no data
    let score = 100;
    records.forEach((r) => {
      if (!r.is_compliant) score -= 10;
      if (r.plaintext_leak_detected) score -= 30;
    });
    return Math.max(0, Math.min(100, score));
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
      await axios.post(ENDPOINTS.registerDevice, enrollForm, {
        headers: {
          ...authService.getAuthHeader(),
          'Content-Type': 'application/json',
        },
      });
      addToast('success', 'Device pre-registered successfully');
      setShowEnrollModal(false);
      setEnrollForm({
        enrollment_number: '',
        enrollment_token: '',
        pre_shared_key: '',
      });
      fetchAllData();
    } catch (error) {
      handleApiError(error, 'Failed to pre-register device');
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
      const detail = data?.detail;
      setUploadResult({
        errors: normalizeMessages(data?.errors || detail?.errors || detail, 'Policy upload failed'),
        warnings: normalizeMessages(data?.warnings || detail?.warnings, '').filter(Boolean),
      });
      setShowUploadResultModal(true);
      handleApiError(error, 'Policy upload failed');
    }
  };

  /* Drag-and-drop handlers for policy upload */
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer?.files?.[0];
    if (file && (file.type === 'application/json' || file.name.endsWith('.json'))) {
      setUploadFile(file);
    } else {
      addToast('warning', 'Please drop a JSON file');
    }
  };

  const normalizeQrImageSrc = (base64OrDataUrl) => {
    if (!base64OrDataUrl) {
      return '';
    }
    if (String(base64OrDataUrl).startsWith('data:image')) {
      return String(base64OrDataUrl);
    }
    return `data:image/png;base64,${base64OrDataUrl}`;
  };

  const handleTotpSetup = async () => {
    setTotpLoading(true);
    try {
      const response = await axios.post(
        ENDPOINTS.totpSetup,
        {},
        { headers: authService.getAuthHeader() }
      );
      setTotpSetupData(response.data || null);
      addToast('success', 'TOTP setup initialized. Scan the QR and verify your code.');
    } catch (error) {
      handleApiError(error, 'Failed to initialize TOTP setup');
    } finally {
      setTotpLoading(false);
    }
  };

  const handleTotpVerify = async (event) => {
    event.preventDefault();
    if (!totpCodeInput.trim()) {
      addToast('warning', 'Enter the authenticator code to verify.');
      return;
    }

    setTotpVerifying(true);
    try {
      await axios.post(
        ENDPOINTS.totpVerify,
        { totp_code: totpCodeInput.trim() },
        {
          headers: {
            ...authService.getAuthHeader(),
            'Content-Type': 'application/json',
          },
        }
      );
      addToast('success', 'TOTP enabled successfully. Future logins will require code verification.');
      setTotpCodeInput('');
    } catch (error) {
      handleApiError(error, 'TOTP verification failed');
    } finally {
      setTotpVerifying(false);
    }
  };

  const getAssignedCount = (policyId) => devices.filter((d) => d.policy_id === policyId).length;

  const toggleDeviceExpanded = (deviceId) => {
    setExpandedDevices((prev) => ({ ...prev, [deviceId]: !prev[deviceId] }));
  };

  /* ═══════════════════════════════════════════
     Render helpers
     ═══════════════════════════════════════════ */

  const renderSidebar = () => (
    <aside className={`sidebar glass-surface ${mobileNavOpen ? 'open' : ''}`}>
      <div className="sidebar-brand">
        <span className="brand-icon" role="img" aria-label="lock">
          🔐
        </span>
        <div>
          <h2>IPsec Vault</h2>
          <small>Zero Trust Console</small>
        </div>
      </div>

      <nav className="nav-list">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <motion.button
              key={item.key}
              className={`nav-item ${activeTab === item.key ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(item.key);
                setMobileNavOpen(false);
              }}
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.98 }}
              layout
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </motion.button>
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
    if (loading && devices.length === 0) {
      return <SkeletonLoader variant="stat" count={5} />;
    }

    const cards = [
      { label: 'Total Devices', value: summary.total, tone: 'primary', Icon: Server },
      { label: 'Active Devices', value: summary.active, tone: 'success', Icon: Activity },
      { label: 'Compliant Devices', value: summary.compliant, tone: 'success', Icon: Shield },
      { label: 'Policies', value: summary.policies, tone: 'primary', Icon: ClipboardList },
      {
        label: 'Violations (24h)',
        value: summary.violations24h,
        tone: summary.violations24h > 0 ? 'danger' : 'neutral',
        Icon: AlertTriangle,
      },
    ];

    return (
      <motion.div className="summary-grid" variants={staggerContainer} initial="initial" animate="animate">
        {cards.map((card) => {
          const CardIcon = card.Icon;
          return (
            <motion.article
              key={card.label}
              className={`summary-card glass-surface tone-${card.tone}`}
              variants={staggerChild}
              whileHover={{ y: -2, transition: { duration: 0.2 } }}
            >
              <div className="summary-icon"><CardIcon size={22} /></div>
              <div className="summary-value">
                <AnimatedCounter value={card.value} duration={1.0} />
              </div>
              <div className="summary-label">{card.label}</div>
            </motion.article>
          );
        })}
      </motion.div>
    );
  };

  const renderDevices = () => {
    if (loading && devices.length === 0) {
      return <SkeletonLoader variant="card" count={4} />;
    }

    if (devices.length === 0) {
      return (
        <div className="empty-state-action glass-surface">
          <div className="empty-icon">💻</div>
          <div className="empty-msg">No devices enrolled yet.</div>
          <button className="btn btn-primary" onClick={() => setShowEnrollModal(true)}>
            <Plus size={16} /> Pre-register Device
          </button>
        </div>
      );
    }

    return (
      <motion.section className="card-grid two-col" variants={staggerContainer} initial="initial" animate="animate">
        {devices.map((device) => {
          const compliance = getDeviceComplianceInfo(device.id);
          const trustScore = getDeviceTrustScore(device.id);
          const isExpanded = expandedDevices[device.id];
          const deviceRecords = complianceByDevice[device.id] || [];
          const last3Records = deviceRecords.slice(0, 3);

          return (
            <motion.article
              key={device.id}
              className={`entity-card glass-surface interactive-card ${isExpanded ? 'dropdown-active' : ''}`}
              style={{ zIndex: isExpanded ? 40 : 1 }}
              variants={staggerChild}
            >
              <div className="card-head">
                <div>
                  <h3>{device.hostname || device.enrollment_number || `Device ${device.id}`}</h3>
                  <div className="mono-text">last_seen: {formatRelativeTime(device.last_seen)}</div>
                </div>
                <span className={`chip os-${(device.os_type || 'unknown').toLowerCase()}`}>{device.os_type || 'unknown'}</span>
              </div>

              <div className="device-meta">
                <div className="device-status-row">
                  <strong>Status:</strong>
                  <StatusDot
                    status={device.is_active ? 'online' : 'inactive'}
                    label={device.is_active ? 'Active' : 'Inactive'}
                  />
                </div>
                <div>
                  <strong>Compliance:</strong>{' '}
                  <motion.span
                    className={`chip compliance-${compliance.tone}`}
                    key={compliance.label}
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.25 }}
                  >
                    {compliance.label}
                  </motion.span>
                </div>
              </div>

              {/* Trust Score Bar */}
              <TrustScoreBar score={trustScore} />

              {compliance.leakDetected ? (
                <motion.div
                  className="leak-alert"
                  animate={{
                    boxShadow: [
                      '0 0 0px rgba(255,68,102,0)',
                      '0 0 16px rgba(255,68,102,0.4)',
                      '0 0 0px rgba(255,68,102,0)',
                    ],
                  }}
                  transition={{ duration: 1.8, repeat: Infinity }}
                >
                  <ShieldAlert size={16} /> Plaintext leak detected
                </motion.div>
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
                <button className="btn btn-danger" onClick={() => handleAssignPolicy(device.id, '')}>
                  Unassign
                </button>
              </div>

              {/* Floating dropdown for inline compliance preview */}
              {deviceRecords.length > 0 && (
                <div className="device-dropdown-container" style={{ position: 'relative', marginTop: 'auto' }}>
                  <button
                    type="button"
                    className={`expand-toggle ${isExpanded ? 'active' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleDeviceExpanded(device.id);
                    }}
                    style={{ width: '100%', justifyContent: 'center', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    {isExpanded ? ' Hide history' : ` Last ${last3Records.length} records`}
                  </button>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        className="device-expanded-compliance-dropdown"
                        initial={{ opacity: 0, y: -6, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -6, scale: 0.98 }}
                        transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', paddingBottom: '6px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                          <span className="mono-text" style={{ color: 'var(--accent-primary)', fontSize: '0.74rem', fontWeight: 600, letterSpacing: '0.04em' }}>
                            RECENT ATTESTATIONS ({last3Records.length})
                          </span>
                          <button
                            type="button"
                            onClick={() => toggleDeviceExpanded(device.id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--text-muted)',
                              cursor: 'pointer',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '0.85rem',
                              lineHeight: 1,
                            }}
                            aria-label="Close"
                          >
                            ✕
                          </button>
                        </div>

                        {last3Records.map((rec, idx) => (
                          <div
                            key={`${rec.timestamp}-${idx}`}
                            className={`mini-compliance-record ${rec.is_compliant ? 'compliant' : 'violation'}`}
                          >
                            <span className="mono-text">{formatRelativeTime(rec.timestamp)}</span>
                            <span>{formatBytes(rec.total_bytes_encrypted)} encrypted</span>
                            <span className={`chip compliance-${rec.is_compliant ? 'success' : 'danger'}`}>
                              {rec.is_compliant ? '✓' : '✗'}
                            </span>
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </motion.article>
          );
        })}
      </motion.section>
    );
  };

  const renderPolicies = () => {
    if (loading && policies.length === 0) {
      return <SkeletonLoader variant="card" count={4} />;
    }

    if (policies.length === 0) {
      return (
        <div className="empty-state-action glass-surface">
          <div className="empty-icon">📋</div>
          <div className="empty-msg">No policies uploaded yet.</div>
          <button className="btn btn-primary" onClick={() => setShowUploadModal(true)}>
            <Upload size={16} /> Upload Policy
          </button>
        </div>
      );
    }

    return (
      <motion.section className="card-grid two-col" variants={staggerContainer} initial="initial" animate="animate">
        {policies.map((policy) => {
          const targetOS = policy?.config_data?.target?.os || [];
          const crypto = policy?.config_data?.ipsec_policy?.crypto || {};
          const ike = crypto.ike || {};
          const esp = crypto.esp || {};

          return (
            <motion.article key={policy.id} className="entity-card glass-surface interactive-card" variants={staggerChild}>
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
                <div><strong>Version:</strong> <span className="chip os-unknown">{policy?.config_data?.version || 'N/A'}</span></div>
                <div><strong>Created:</strong> {new Date(policy.created_at).toLocaleString()}</div>
                <div><strong>Assigned Devices:</strong> <span className="sa-badge">{getAssignedCount(policy.id)}</span></div>
              </div>

              <div className="chip-row">
                {targetOS.length ? targetOS.map((os) => (
                  <span key={`${policy.id}-${os}`} className={`chip os-${String(os).toLowerCase()}`}>{os}</span>
                )) : <span className="chip os-unknown">No target OS</span>}
              </div>

              <div className="algo-block mono-text">IKE: {ike.encryption || 'N/A'} / {ike.integrity || 'N/A'} / {ike.dh_group || 'N/A'}</div>
              <div className="algo-block mono-text">ESP: {esp.encryption || 'N/A'} / {esp.integrity || 'N/A'} / {esp.dh_group || 'N/A'}</div>
            </motion.article>
          );
        })}
      </motion.section>
    );
  };

  const selectedTimeline = complianceByDevice[selectedComplianceDevice] || [];

  const renderComplianceTimeline = () => (
    <motion.section className="glass-surface timeline-wrap" {...fadeUp}>
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

      {loading && selectedTimeline.length === 0 ? (
        <SkeletonLoader variant="timeline" count={4} />
      ) : (
        <div className="timeline-list">
          {selectedTimeline.map((record, index) => {
            const violations = record?.raw_report?.violations || [];
            const chainHash = record?.chain_hash || record?.raw_report?.chain_hash;
            const activeSaCount = record.active_sa_count ?? (record.active_sas?.length || 0);

            return (
              <motion.article
                key={`${record.timestamp}-${index}`}
                className={`timeline-item ${record.is_compliant ? 'ok' : 'bad'}`}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05, duration: 0.3 }}
              >
                <div className="timeline-top">
                  <span className="mono-text">{new Date(record.timestamp).toLocaleString()}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="sa-badge">{activeSaCount} SA{activeSaCount !== 1 ? 's' : ''}</span>
                    <motion.span
                      className={`chip compliance-${record.is_compliant ? 'success' : 'danger'}`}
                      initial={{ scale: 0.8 }}
                      animate={{ scale: 1 }}
                      transition={{ duration: 0.2 }}
                    >
                      {record.is_compliant ? 'Compliant' : 'Violation'}
                    </motion.span>
                  </div>
                </div>
                <div className="timeline-metrics">
                  <span>{formatBytes(record.total_bytes_encrypted)} encrypted</span>
                  {chainHash && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                      Chain: <HashDisplay hash={chainHash} truncateAt={16} />
                    </span>
                  )}
                </div>
                {violations.length > 0 ? (
                  <ul className="violations-list">
                    {violations.map((violation, vIndex) => (
                      <li key={`${record.timestamp}-${vIndex}`}>{String(violation)}</li>
                    ))}
                  </ul>
                ) : null}
              </motion.article>
            );
          })}

          {selectedTimeline.length === 0 ? (
            <div className="empty-state-action">
              <div className="empty-icon">📊</div>
              <div className="empty-msg">No compliance records found for this device.</div>
            </div>
          ) : null}
        </div>
      )}
    </motion.section>
  );

  const renderContent = () => {
    if (activeTab === 'devices') return renderDevices();
    if (activeTab === 'policies') return renderPolicies();
    if (activeTab === 'compliance') return renderComplianceTimeline();
    if (activeTab === 'settings') {
      return (
        <motion.section className="glass-surface settings-card" {...fadeUp}>
          <h3>Settings</h3>
          <p className="sub-text">Backend: {backendOnline ? 'Online' : 'Offline'}</p>
          <p className="sub-text">Theme: Glassmorphism enabled</p>

          <div className="totp-settings-block">
            <div className="totp-settings-head">
              <h4>Time-based One-Time Password (TOTP)</h4>
              <button className="btn btn-secondary" onClick={handleTotpSetup} disabled={totpLoading}>
                {totpLoading ? 'Generating...' : 'Generate QR'}
              </button>
            </div>

            <p className="sub-text">
              Use your authenticator app to scan the QR code, then enter the 6-digit code to enable MFA.
            </p>

            {totpSetupData ? (
              <div className="totp-setup-panel">
                <div className="totp-qr-wrap glass-surface">
                  <img
                    src={normalizeQrImageSrc(totpSetupData.qr_code_png_base64)}
                    alt="TOTP QR"
                    className="totp-qr"
                  />
                </div>
                <div className="totp-meta">
                  <div className="mono-text">Secret: {totpSetupData.secret || 'N/A'}</div>
                  <div className="mono-text">URI: {totpSetupData.provisioning_uri || 'N/A'}</div>
                </div>

                <form className="totp-verify-form" onSubmit={handleTotpVerify}>
                  <input
                    className="input-field"
                    placeholder="Enter 6-digit code"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={totpCodeInput}
                    onChange={(e) => setTotpCodeInput(e.target.value)}
                    required
                  />
                  <button className="btn btn-primary" type="submit" disabled={totpVerifying}>
                    {totpVerifying ? 'Verifying...' : 'Verify & Enable'}
                  </button>
                </form>
              </div>
            ) : null}
          </div>
        </motion.section>
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
                <strong>
                  <span className={`chip os-${String(os).toLowerCase()}`}>{os}</span>
                </strong>
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

  /* ═══════════════════════════════════════════
     Modal wrapper (shared)
     ═══════════════════════════════════════════ */
  const ModalWrap = ({ show, onClose, children }) => (
    <AnimatePresence>
      {show ? (
        <motion.div
          className="modal-overlay"
          variants={modalOverlayVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
          <motion.div
            className="modal glass-surface"
            variants={modalCardVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={modalCardVariants.transition}
          >
            {children}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );

  return (
    <div className="app-shell">
      {renderSidebar()}

      <main className="main-content">
        <motion.header className="top-bar glass-surface" {...fadeUp}>
          <div className="top-left">
            <button className="icon-btn mobile-menu-btn" onClick={() => setMobileNavOpen((prev) => !prev)}>
              <Menu size={20} />
            </button>
            <h1>{NAV_ITEMS.find((item) => item.key === activeTab)?.label || 'Dashboard'}</h1>
          </div>

          <div className="top-actions">
            {/* Backend status indicator in top bar for visibility */}
            <StatusDot
              status={backendOnline ? 'online' : 'offline'}
              label={backendOnline ? 'API Online' : 'API Offline'}
            />
            <motion.button
              className="btn btn-secondary"
              onClick={fetchAllData}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <RefreshCw size={16} className={loading ? 'spin-icon' : ''} />
              <span>{loading ? 'Refreshing...' : 'Refresh'}</span>
            </motion.button>
            <motion.button
              className="btn btn-primary"
              onClick={() => setShowEnrollModal(true)}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <Plus size={16} />
              <span>Pre-register Device</span>
            </motion.button>
            <motion.button
              className="btn btn-primary"
              onClick={() => setShowUploadModal(true)}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <Upload size={16} />
              <span>Upload Policy</span>
            </motion.button>
          </div>
        </motion.header>

        <AnimatePresence mode="wait">
          <motion.div key={activeTab} {...fadeUp}>
            {renderContent()}
          </motion.div>
        </AnimatePresence>
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

      {/* ── Modals ── */}
      <ModalWrap show={showEnrollModal} onClose={() => setShowEnrollModal(false)}>
        <h3>Pre-register Device</h3>
        <p className="sub-text">
          Register the device record first. The agent will use this enrollment number and token later to enroll itself.
        </p>
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
            placeholder="Pre-shared key"
            value={enrollForm.pre_shared_key}
            onChange={(e) => setEnrollForm((prev) => ({ ...prev, pre_shared_key: e.target.value }))}
            required
          />
          <div className="modal-actions">
            <button className="btn btn-secondary" type="button" onClick={() => setShowEnrollModal(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" type="submit">Register</button>
          </div>
        </form>
      </ModalWrap>

      <ModalWrap show={showUploadModal} onClose={() => setShowUploadModal(false)}>
        <h3>Upload Policy JSON</h3>
        <form className="stack-form" onSubmit={handleUploadPolicy}>
          <div
            className={`drop-zone ${dragActive ? 'active' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('policy-file-input')?.click()}
          >
            <div className="drop-zone-inner">
              <span className="drop-zone-icon"><FileJson size={32} /></span>
              <span className="drop-zone-text">
                {uploadFile ? uploadFile.name : 'Drop JSON file here or click to browse'}
              </span>
              <span className="drop-zone-hint">Accepts .json policy files</span>
            </div>
          </div>
          <input
            id="policy-file-input"
            className="input-field"
            type="file"
            accept="application/json,.json"
            onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
            style={{ display: 'none' }}
          />
          {uploadFile && (
            <div className="selected-file-chip">
              <FileJson size={14} /> {uploadFile.name}
            </div>
          )}
          <div className="modal-actions">
            <button className="btn btn-secondary" type="button" onClick={() => { setShowUploadModal(false); setUploadFile(null); }}>
              Cancel
            </button>
            <button className="btn btn-primary" type="submit">Upload</button>
          </div>
        </form>
      </ModalWrap>

      <ModalWrap show={showUploadResultModal} onClose={() => setShowUploadResultModal(false)}>
        {renderUploadSummary()}
        <div className="modal-actions">
          <button className="btn btn-primary" type="button" onClick={() => setShowUploadResultModal(false)}>
            Close
          </button>
        </div>
      </ModalWrap>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default Dashboard;
