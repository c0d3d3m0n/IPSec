import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';

function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      <div className="landing-hero">
        <div className="landing-icon-wrap">
          <Shield size={80} className="landing-icon" />
        </div>

        <h1 className="landing-title">Unified IPsec Orchestration</h1>
        <p className="landing-brand">IPsec Vault</p>

        <p className="landing-subtitle">
          Zero Trust policy enforcement across Windows, Linux and macOS - from one place.
        </p>

        <div className="landing-actions">
          <button className="btn btn-primary landing-action-primary" onClick={() => navigate('/_tenant_admin')}>
            Get Started
          </button>
          <a
            className="btn btn-secondary landing-action-secondary"
            href="https://api.ipsecvault.tech/docs"
            target="_blank"
            rel="noreferrer"
          >
            View API Docs
          </a>
          <a
            className="btn btn-secondary landing-action-secondary"
            href="https://github.com/c0d3d3m0n/IPSec.git"
            target="_blank"
            rel="noreferrer"
          >
            GitHub Repository
          </a>
        </div>

        <div className="landing-metrics glass-surface">
          <div className="landing-metric-item">
            <strong>3</strong>
            <span>Supported OS Targets</span>
          </div>
          <div className="landing-metric-item">
            <strong>Zero Trust</strong>
            <span>mTLS + Continuous Trust Scoring</span>
          </div>
          <div className="landing-metric-item">
            <strong>SHA-512</strong>
            <span>Tamper-Evident Audit Integrity</span>
          </div>
        </div>
      </div>

      <section className="landing-features">
        <article className="glass-surface landing-feature-card">
          <div className="landing-feature-icon" aria-hidden="true">🔐</div>
          <h3 className="landing-feature-title">Zero Trust Architecture</h3>
          <p className="landing-feature-body">
            mTLS device authentication, internal CA, continuous trust scoring on every request.
          </p>
        </article>

        <article className="glass-surface landing-feature-card">
          <div className="landing-feature-icon" aria-hidden="true">💻</div>
          <h3 className="landing-feature-title">Cross-Platform Native</h3>
          <p className="landing-feature-body">
            One JSON policy compiles to strongSwan, PowerShell, and racoon configs automatically.
          </p>
        </article>

        <article className="glass-surface landing-feature-card">
          <div className="landing-feature-icon" aria-hidden="true">📡</div>
          <h3 className="landing-feature-title">Live Compliance Monitoring</h3>
          <p className="landing-feature-body">
            SA counter polling, plaintext leak detection, and tamper-evident SHA-512 audit chain.
          </p>
        </article>
      </section>

      <section className="landing-content-strip glass-surface">
        <h2>Why Security Teams Use IPsec Vault</h2>
        <p>
          Move from fragmented, manual tunnel operations to policy-driven automation with strong identity,
          measurable compliance, and platform-native config generation from a single control plane.
        </p>
        <ul>
          <li>Centralized policy lifecycle with versioning and controlled rollout.</li>
          <li>Continuous posture telemetry: heartbeat, SA status, and leak alerts.</li>
          <li>Operationally simple deployment on Vercel + Render with API-first workflows.</li>
        </ul>
      </section>

      <footer className="landing-footer">Built with FastAPI · PostgreSQL · Docker · Render</footer>
    </div>
  );
}

export default LandingPage;
