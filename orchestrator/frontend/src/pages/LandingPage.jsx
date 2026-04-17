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

        <p className="landing-subtitle">
          Zero Trust policy enforcement across Windows, Linux and macOS - from one place.
        </p>

        <div className="landing-actions">
          <button className="btn btn-primary landing-action-primary" onClick={() => navigate('/login')}>
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

      <footer className="landing-footer">Built with FastAPI · PostgreSQL · Docker · Render</footer>
    </div>
  );
}

export default LandingPage;
