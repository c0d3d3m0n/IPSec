import React, { useEffect, useRef } from 'react';

/**
 * CyberBackground — Dynamic animated tech grid, glowing constellation nodes,
 * pulse packets, and sweeping radar scanline.
 * Clearly visible yet balanced motion so the background feels alive and high-tech.
 */
function CyberBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    // Particle nodes setup
    const particleCount = Math.min(52, Math.floor((width * height) / 24000));
    const particles = [];
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.55,
        vy: (Math.random() - 0.5) * 0.55,
        radius: Math.random() * 1.6 + 1.4,
        alpha: Math.random() * 0.4 + 0.35,
        pulseSpeed: Math.random() * 0.03 + 0.01,
        pulseOffset: Math.random() * Math.PI * 2,
      });
    }

    // Floating data packets traveling along lines
    const packets = [];
    const maxPackets = 8;

    // Scanline state
    let scanlineY = 0;
    const scanlineSpeed = 0.9;

    // Mouse coordinates
    let mouse = { x: -1000, y: -1000 };
    const handleMouseMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    window.addEventListener('mousemove', handleMouseMove);

    let frameCount = 0;

    // Render loop
    const render = () => {
      frameCount++;
      ctx.clearRect(0, 0, width, height);

      // 1. Subtle Tech Grid & Crosshairs
      const gridSize = 64;
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.04)';
      ctx.lineWidth = 1;

      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Grid intersection marks (+)
      ctx.fillStyle = 'rgba(52, 211, 153, 0.14)';
      for (let x = gridSize; x < width; x += gridSize * 2) {
        for (let y = gridSize; y < height; y += gridSize * 2) {
          ctx.fillRect(x - 2, y - 0.5, 4, 1);
          ctx.fillRect(x - 0.5, y - 2, 1, 4);
        }
      }

      // 2. Sweeping Radar Scanline
      scanlineY += scanlineSpeed;
      if (scanlineY > height + 60) scanlineY = -60;

      // Soft ambient beam
      const beamGrad = ctx.createLinearGradient(0, scanlineY - 45, 0, scanlineY + 45);
      beamGrad.addColorStop(0, 'rgba(16, 185, 129, 0)');
      beamGrad.addColorStop(0.5, 'rgba(16, 185, 129, 0.045)');
      beamGrad.addColorStop(1, 'rgba(16, 185, 129, 0)');
      ctx.fillStyle = beamGrad;
      ctx.fillRect(0, scanlineY - 45, width, 90);

      // Sharp central laser scanline
      ctx.strokeStyle = 'rgba(52, 211, 153, 0.18)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, scanlineY);
      ctx.lineTo(width, scanlineY);
      ctx.stroke();

      // 3. Connect nearby nodes
      const activeConnections = [];

      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 145) {
            const lineAlpha = (1 - dist / 145) * 0.22;
            ctx.strokeStyle = `rgba(16, 185, 129, ${lineAlpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();

            activeConnections.push({ from: particles[i], to: particles[j] });
          }
        }

        // Mouse attraction
        const mdx = particles[i].x - mouse.x;
        const mdy = particles[i].y - mouse.y;
        const mdist = Math.sqrt(mdx * mdx + mdy * mdy);
        if (mdist < 150) {
          const mAlpha = (1 - mdist / 150) * 0.35;
          ctx.strokeStyle = `rgba(52, 211, 153, ${mAlpha})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.stroke();
        }
      }

      // 4. Data Packets traveling along connections
      if (frameCount % 40 === 0 && activeConnections.length > 0 && packets.length < maxPackets) {
        const conn = activeConnections[Math.floor(Math.random() * activeConnections.length)];
        packets.push({
          from: conn.from,
          to: conn.to,
          progress: 0,
          speed: Math.random() * 0.02 + 0.015,
        });
      }

      for (let pIdx = packets.length - 1; pIdx >= 0; pIdx--) {
        const pkt = packets[pIdx];
        pkt.progress += pkt.speed;

        if (pkt.progress >= 1) {
          packets.splice(pIdx, 1);
          continue;
        }

        const px = pkt.from.x + (pkt.to.x - pkt.from.x) * pkt.progress;
        const py = pkt.from.y + (pkt.to.y - pkt.from.y) * pkt.progress;

        ctx.shadowBlur = 6;
        ctx.shadowColor = 'rgba(52, 211, 153, 0.9)';
        ctx.fillStyle = '#6EE7B7';
        ctx.beginPath();
        ctx.arc(px, py, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // 5. Update & Draw Particles with Glow
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        // Wrap edges
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        // Pulse alpha
        const dynamicAlpha = Math.max(0.2, p.alpha + Math.sin(frameCount * p.pulseSpeed + p.pulseOffset) * 0.15);

        ctx.shadowBlur = 8;
        ctx.shadowColor = 'rgba(16, 185, 129, 0.7)';
        ctx.fillStyle = `rgba(52, 211, 153, ${dynamicAlpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
        opacity: 0.92,
      }}
    />
  );
}

export default CyberBackground;
