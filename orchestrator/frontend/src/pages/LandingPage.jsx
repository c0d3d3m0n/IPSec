import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Shield,
  Terminal,
  Lock,
  Key,
  Activity,
  Cpu,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  ArrowRight,
  Zap,
  RefreshCw,
  AlertTriangle,
  Layers,
  FileCode,
  Radio,
} from 'lucide-react';

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.05 },
  transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] },
};

const staggerContainer = {
  initial: {},
  whileInView: { transition: { staggerChildren: 0.08 } },
  viewport: { once: true, amount: 0.05 },
};

const staggerChild = {
  initial: { opacity: 0, y: 14 },
  whileInView: { opacity: 1, y: 0 },
  transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
};

/* 6 Core Feature Flash Cards */
const FEATURE_FLASHCARDS = [
  {
    id: 'kernel-enforce',
    tag: 'NATIVE COMPILATION',
    title: 'Cross-Platform Native Kernel Engine',
    desc: 'Translates a single high-level JSON policy into platform-native configurations: strongSwan on Linux (XFRM), WFP PowerShell on Windows, and pfctl on macOS without foreign driver bloat.',
    icon: Cpu,
    chips: ['strongSwan XFRM', 'Windows WFP.sys', 'macOS pfctl', 'Zero Overhead'],
  },
  {
    id: 'plaintext-leak',
    tag: 'KERNEL AUDIT',
    title: 'Real-Time Plaintext Leak Detection',
    desc: 'Continuous kernel-level packet inspection monitors raw socket states. If any unencrypted payload bypasses the ESP tunnel, the node is quarantined and telemetry flags immediate violations.',
    icon: AlertTriangle,
    chips: ['Socket Polling', 'Zero Plaintext Egress', 'Automated Isolation', '< 500ms Trigger'],
  },
  {
    id: 'mtls-pki',
    tag: 'ZERO TRUST IDENTITY',
    title: 'mTLS Authentication & Internal PKI',
    desc: 'Eliminates fragile shared passwords. Every endpoint authenticates with unique x509 certificates issued by an internal Root CA, cryptographically bound to device enrollment tokens.',
    icon: Key,
    chips: ['Mutual TLS v1.3', 'Hardware Bound', 'Auto Cert Rotation', 'Internal Root CA'],
  },
  {
    id: 'audit-chain',
    tag: 'CRYPTOGRAPHIC AUDIT',
    title: 'Tamper-Evident SHA-512 Ledger',
    desc: 'Every policy compilation, SA rekeying event, and compliance heartbeat is hashed into an immutable cryptographic chain. Provides mathematical audit integrity for SOC compliance.',
    icon: Layers,
    chips: ['SHA-512 Chaining', 'Immutable History', 'NIST SP 800-77', 'Non-Repudiation'],
  },
  {
    id: 'trust-engine',
    tag: 'DYNAMIC SCORING',
    title: 'Continuous Posture Trust Engine',
    desc: 'Calculates dynamic trust scores (0–100) per device in real time based on active SA uptime, encrypted byte throughput, and compliance attestation. Degraded nodes lose route permissions.',
    icon: Activity,
    chips: ['30s Telemetry Loop', 'Adaptive Access', 'SA Byte Counters', 'Graceful Fallback'],
  },
  {
    id: 'crypto-agility',
    tag: 'MODERN CIPHERS',
    title: 'Cryptographic Suite Agility',
    desc: 'Enforce enterprise-grade AEAD and CBC encryption algorithms with perfect forward secrecy. Cross-platform support for AES-256-GCM, AES-CBC-256, SHA-512 integrity, and ECP-384 / DH14 key exchange.',
    icon: Lock,
    chips: ['AES-256-GCM', 'AES-CBC-256', 'SHA-512', 'ECP-384', 'DH14'],
  },
];

/* 4-Step Orchestration Pipeline */
const PIPELINE_STEPS = [
  {
    step: '01 // DECLARE',
    title: 'Unified JSON Policy',
    desc: 'Define security associations, allowed subnets, algorithms, and target operating systems in a declarative schema.',
    icon: FileCode,
  },
  {
    step: '02 // DISTRIBUTE',
    title: 'mTLS Secure Delivery',
    desc: 'FastAPI orchestrator signs and pushes cryptographic configuration bundles to authenticated node daemons.',
    icon: Radio,
  },
  {
    step: '03 // COMPILE',
    title: 'Native OS Kernel Rules',
    desc: 'Endpoint agents translate policies directly into kernel IPsec rules via strongSwan, PowerShell, or pfctl.',
    icon: Cpu,
  },
  {
    step: '04 // ATTEST',
    title: 'Continuous Audit Loop',
    desc: '30-second heartbeat verifies active SAs, validates byte counters, and appends to the SHA-512 audit chain.',
    icon: RefreshCw,
  },
];

/* Endpoint Agent Enrollment Steps */
const ENROLLMENT_STEPS = {
  linux: {
    label: 'Linux',
    title: 'agent@linux-node:~/IPSec/agent$',
    prompt: '$',
    lines: [
      'git clone https://github.com/c0d3d3m0n/IPSec',
      'cd IPSec/agent',
      'python3 -m venv .venv && source .venv/bin/activate',
      'pip install -r requirements.txt',
      'sudo -E python3 main.py',
    ],
  },
  windows: {
    label: 'Windows (Admin PowerShell)',
    title: 'PS C:\\IPSec\\agent>',
    prompt: '>',
    lines: [
      'git clone https://github.com/c0d3d3m0n/IPSec',
      'cd IPSec\\agent',
      'python -m venv .venv',
      '.venv\\Scripts\\Activate.ps1',
      'pip install -r requirements.txt',
      'python main.py',
    ],
  },
};

function LandingPage() {
  const navigate = useNavigate();
  const [enrollmentOs, setEnrollmentOs] = useState('linux');
  const [copied, setCopied] = useState(false);

  const activeSteps = ENROLLMENT_STEPS[enrollmentOs];

  const handleCopy = () => {
    navigator.clipboard.writeText(activeSteps.lines.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  };

  return (
    <div className="landing-page">
      {/* ── HERO SECTION ── */}
      <div className="landing-hero">
        <motion.div
          className="landing-icon-wrap"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <Shield size={74} className="landing-icon" />
        </motion.div>

        <div className="chip os-linux" style={{ marginBottom: '14px', letterSpacing: '0.08em' }}>
          SEC-OPS CONTROL PLANE // ZERO TRUST
        </div>

        <motion.h1
          className="landing-title"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.5 }}
        >
          Unified IPsec Orchestration
        </motion.h1>

        <motion.p
          className="landing-brand"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
        >
          &gt;_ IPSEC VAULT CONTROL PLANE
        </motion.p>

        <motion.p
          className="landing-subtitle"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
        >
          Automated Zero Trust policy compilation, mTLS device authentication, and continuous cryptographic compliance across Windows, Linux, and macOS.
        </motion.p>

        <motion.div
          className="landing-actions"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55, duration: 0.5 }}
        >
          <motion.button
            className="btn btn-primary landing-action-primary"
            onClick={() => navigate('/login')}
            whileHover={{ scale: 1.03, boxShadow: '0 6px 20px rgba(16, 185, 129, 0.35)' }}
            whileTap={{ scale: 0.97 }}
          >
            Launch Console <ArrowRight size={16} />
          </motion.button>
          <a
            className="btn btn-secondary landing-action-secondary"
            href="https://api.ipsecvault.tech/docs"
            target="_blank"
            rel="noreferrer"
          >
            <Terminal size={16} /> API Reference
          </a>
          <a
            className="btn btn-secondary landing-action-secondary"
            href="https://github.com/c0d3d3m0n/IPSec.git"
            target="_blank"
            rel="noreferrer"
          >
            GitHub Repository
          </a>
        </motion.div>

        {/* ── Key Metrics ── */}
        <motion.div className="landing-metrics glass-surface" {...fadeUp}>
          <div className="landing-metric-item">
            <strong>3 Platforms Native</strong>
            <span>Linux (strongSwan) · Windows (WFP) · macOS (pfctl)</span>
          </div>
          <div className="landing-metric-item">
            <strong>Zero Trust Scoring</strong>
            <span>mTLS PKI + Dynamic Posture Telemetry</span>
          </div>
          <div className="landing-metric-item">
            <strong>SHA-512 Audit Ledger</strong>
            <span>Tamper-Evident Cryptographic Chaining</span>
          </div>
        </motion.div>
      </div>

      {/* ── SECTION 1: FEATURE FLASH CARDS ── */}
      <section className="landing-section">
        <div className="landing-section-header">
          <div className="chip os-linux" style={{ letterSpacing: '0.06em' }}>
            ENGINEERING CAPABILITIES
          </div>
          <h2>Security Architecture Flash Cards</h2>
          <p>
            Purpose-built for zero-trust environments requiring kernel-level enforcement, deterministic crypto agility, and strict attestation.
          </p>
        </div>

        <motion.div className="flashcard-grid" {...staggerContainer}>
          {FEATURE_FLASHCARDS.map((card) => {
            const Icon = card.icon;
            return (
              <motion.article key={card.id} className="flashcard interactive-card" variants={staggerChild}>
                <div className="flashcard-top">
                  <div className="flashcard-icon-badge">
                    <Icon size={22} />
                  </div>
                  <span className="flashcard-tag">{card.tag}</span>
                </div>
                <h3>{card.title}</h3>
                <p>{card.desc}</p>
                <div className="flashcard-chips">
                  {card.chips.map((chip, idx) => (
                    <span key={idx} className="tech-spec-chip">
                      {chip}
                    </span>
                  ))}
                </div>
              </motion.article>
            );
          })}
        </motion.div>
      </section>

      {/* ── SECTION 2: 4-STEP PIPELINE FLOW ── */}
      <section className="landing-section">
        <div className="landing-section-header">
          <div className="chip os-windows" style={{ letterSpacing: '0.06em' }}>
            ORCHESTRATION PIPELINE
          </div>
          <h2>How IPsec Vault Compiles &amp; Enforces</h2>
          <p>
            From declarative policy authoring to kernel-level packet filtering in four synchronized stages.
          </p>
        </div>

        <motion.div className="pipeline-grid" {...staggerContainer}>
          {PIPELINE_STEPS.map((item, idx) => {
            const StepIcon = item.icon;
            return (
              <motion.div key={idx} className="pipeline-card glass-surface" variants={staggerChild}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="pipeline-step-badge">{item.step}</span>
                  <StepIcon size={18} color="var(--accent-primary)" />
                </div>
                <h4>{item.title}</h4>
                <p>{item.desc}</p>
              </motion.div>
            );
          })}
        </motion.div>
      </section>

      {/* ── SECTION 3: COMPARISON MATRIX FLASH CARDS ── */}
      <section className="landing-section">
        <div className="landing-section-header">
          <div className="chip os-linux" style={{ letterSpacing: '0.06em' }}>
            PARADIGM SHIFT
          </div>
          <h2>Traditional Manual IPsec vs. IPsec Vault</h2>
          <p>
            Replace brittle static tunnel configurations with an automated, auditable zero-trust mesh.
          </p>
        </div>

        <div className="comparison-grid">
          {/* Legacy Card */}
          <div className="comparison-card legacy glass-surface">
            <div className="comparison-header">
              <h3 style={{ color: '#FB7185' }}>Traditional Manual IPsec</h3>
              <span className="chip compliance-danger">Brittle &amp; Fragmented</span>
            </div>
            <div className="comparison-list">
              <div className="comparison-row">
                <XCircle size={18} color="#F43F5E" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Fragmented config syntax per OS (ipsec.conf, PowerShell, pfctl)</span>
              </div>
              <div className="comparison-row">
                <XCircle size={18} color="#F43F5E" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Static pre-shared keys vulnerable to credential compromise and leakage</span>
              </div>
              <div className="comparison-row">
                <XCircle size={18} color="#F43F5E" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Blind tunnel status without live SA byte counters or verification</span>
              </div>
              <div className="comparison-row">
                <XCircle size={18} color="#F43F5E" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Undetected plaintext leaks silently exiting unencrypted network interfaces</span>
              </div>
              <div className="comparison-row">
                <XCircle size={18} color="#F43F5E" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Manual, unverified audit logs that fail compliance certifications</span>
              </div>
            </div>
          </div>

          {/* IPsec Vault Card */}
          <div className="comparison-card vault glass-surface">
            <div className="comparison-header">
              <h3 style={{ color: '#34D399' }}>IPsec Vault Zero Trust Mesh</h3>
              <span className="chip compliance-success">Automated &amp; Auditable</span>
            </div>
            <div className="comparison-list">
              <div className="comparison-row">
                <CheckCircle2 size={18} color="#10B981" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Single declarative JSON compiled natively on Linux, Windows &amp; macOS</span>
              </div>
              <div className="comparison-row">
                <CheckCircle2 size={18} color="#10B981" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Mutual TLS (mTLS) with Root CA and hardware-bound enrollment tokens</span>
              </div>
              <div className="comparison-row">
                <CheckCircle2 size={18} color="#10B981" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Real-time posture scoring (0–100) with 30-second automated telemetry loops</span>
              </div>
              <div className="comparison-row">
                <CheckCircle2 size={18} color="#10B981" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Kernel socket inspection flagging unencrypted packet escapes instantly</span>
              </div>
              <div className="comparison-row">
                <CheckCircle2 size={18} color="#10B981" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Tamper-evident SHA-512 cryptographic ledger for indisputable audit trails</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 4: CLI ENROLLMENT TERMINAL FLASH CARD ── */}
      <section className="landing-section">
        <div className="terminal-card glass-surface">
          <div className="terminal-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div className="terminal-dots">
                <span className="terminal-dot dot-red" />
                <span className="terminal-dot dot-amber" />
                <span className="terminal-dot dot-green" />
              </div>
              <span className="terminal-title">{activeSteps.title}</span>
            </div>
            <div className="terminal-tabs">
              <button
                type="button"
                className={`terminal-tab-btn ${enrollmentOs === 'linux' ? 'active' : ''}`}
                onClick={() => setEnrollmentOs('linux')}
              >
                Linux
              </button>
              <button
                type="button"
                className={`terminal-tab-btn ${enrollmentOs === 'windows' ? 'active' : ''}`}
                onClick={() => setEnrollmentOs('windows')}
              >
                Windows (Admin PowerShell)
              </button>
            </div>
          </div>
          <div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '12px', fontFamily: 'var(--font-mono)' }}>
              Deploy and enroll the native endpoint daemon onto your node:
            </p>
            <div className="terminal-multiline-wrap">
              <button className="copy-btn terminal-copy-float" onClick={handleCopy} type="button">
                {copied ? <Check size={14} /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy All'}</span>
              </button>
              <pre className="terminal-code-block">
                {activeSteps.lines.map((line, idx) => (
                  <div key={idx} className="terminal-code-line">
                    <span className="terminal-prompt-sym">{activeSteps.prompt}</span>
                    <span className="terminal-code-text">{line}</span>
                  </div>
                ))}
              </pre>
            </div>
            <div className="terminal-meta-footer">
              <div>Orchestrator URL: <span className="mono-text" style={{ color: 'var(--accent-primary)' }}>https://api.ipsecvault.tech</span></div>
              <div>Web Console: <span className="mono-text" style={{ color: 'var(--accent-primary)' }}>https://www.ipsecvault.tech</span></div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 5: COMPLIANCE & PROTOCOLS ── */}
      <section className="landing-section">
        <div className="landing-content-strip glass-surface" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <Zap size={20} color="var(--accent-primary)" />
            <h2 style={{ margin: 0 }}>Built for High-Assurance SOC Operations</h2>
          </div>
          <p>
            IPsec Vault bridges the gap between low-level cryptographic daemons and enterprise security operations. Deployed as a secure FastAPI orchestrator with PostgreSQL persistence and lightweight native daemons, it gives administrators full visibility into encrypted tunnel lifecycles.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '16px' }}>
            <span className="chip os-linux">RFC 7296 (IKEv2)</span>
            <span className="chip os-linux">RFC 4303 (ESP)</span>
            <span className="chip os-windows">NIST SP 800-207</span>
            <span className="chip os-windows">NIST SP 800-77</span>
            <span className="chip os-macos">AES-256-GCM</span>
            <span className="chip os-unknown">SHA-512</span>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="landing-footer">
        <div>IPsec Vault · Zero Trust Policy Orchestration Platform</div>
        <div style={{ marginTop: '6px', color: 'var(--text-muted)' }}>
          FastAPI · PostgreSQL · Docker · strongSwan · Windows WFP · macOS pfctl
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
