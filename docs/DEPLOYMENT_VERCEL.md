# 🚀 Frontend Deployment Guide: Vercel

This guide walks you through deploying the **IPsec Console** (React Dashboard) to **Vercel** and connecting it to your **Render** backend.

---

## 🏗 Prerequisites

- A [Vercel](https://vercel.com) account.
- Your Orchestrator backend URL (e.g., `https://ipsec-lcir.onrender.com`).
- The project pushed to a GitHub repository.

---

## 🚀 Step-by-Step Deployment

### 1. Import Project
1. Go to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New** $\rightarrow$ **Project**.
3. Import your `IPSec_Framework` repository.

### 2. Configure Framework
- **Framework Preset**: Vite
- **Root Directory**: `orchestrator/frontend` (Click **Edit** next to Root Directory and select the folder).
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

### 3. Environment Variables
Add the following variable to connect the frontend to the backend:
- `VITE_API_URL`: Your Render backend URL (e.g., `https://ipsec-lcir.onrender.com`)

> [!NOTE]
> Ensure you update your `vite.config.js` or API services to use this environment variable in production.

### 4. Deploy
Click **Deploy**. Vercel will build your React application and provide a production URL (e.g., `https://ipsec-console.vercel.app`).

---

## 🔧 Post-Deployment: CORS

Once your frontend is deployed, you **must** allow its URL in your Render backend settings:
1. Go to your **Render Dashboard**.
2. Select your **ipsec-orchestrator** service.
3. Add your Vercel URL to the `ALLOWED_ORIGINS` environment variable (if implemented) or update `main.py` to include it in the CORS middleware.

---

## 🔍 Troubleshooting

- **404 on Refresh**: If you get a 404 when refreshing a page inside the dashboard, add a `vercel.json` file in `orchestrator/frontend` with:
  ```json
  {
    "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
  }
  ```
- **Connection Refused**: Double-check that your `VITE_API_URL` does *not* have a trailing slash and is using `https`.
