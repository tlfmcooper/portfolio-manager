# Railway Configuration Guide

This project uses a monorepo structure with separate backend and frontend services deployed to Railway.

## Configuration Files

### Root `railway.toml`
- **Purpose**: Backend service configuration
- **Location**: `./railway.toml`
- **Points to**: `backend/Dockerfile`

### Frontend Configuration
- **Location**: Configured directly in Railway Dashboard (no `railway.toml` needed)
- **Settings**: Set in Railway Dashboard → Service Settings

## Railway Service Setup

### Backend Service (`protective-playfulness`)

**In Railway Dashboard → Settings:**

1. **Root Directory**: Leave as `.` (root) or set to `backend`
2. **Build Configuration**:
   - Builder: Dockerfile (auto-detected from `railway.toml`)
   - Dockerfile Path: `backend/Dockerfile`
   - Docker Context: `.`

**Critical**: The backend service will read the root `railway.toml` file.

### Frontend Service (`intelligent-playfulness`)

**In Railway Dashboard → Settings:**

1. **Root Directory**: Set to `frontend`
2. **Build Configuration**:
   - Builder: Dockerfile
   - Dockerfile Path: `frontend/Dockerfile`
   - Docker Context: `.`
3. **Environment Variables**:
   - `VITE_API_URL=https://protective-playfulness-production.up.railway.app`

**Important**: The frontend service should NOT have a `frontend/railway.toml` file to avoid conflicts.

## Troubleshooting

### Issue: Backend service building with frontend Dockerfile

**Symptoms:**
- Backend returns 502 Bad Gateway
- Logs show NGINX errors instead of Python/Uvicorn
- Railway edge returns "Application failed to respond"

**Solution:**
1. Verify root `railway.toml` points to `backend/Dockerfile`
2. Delete any `frontend/railway.toml` file
3. In Railway Dashboard → Backend Service → Settings:
   - Confirm Dockerfile Path is `backend/Dockerfile`
   - If needed, manually override by setting it in the dashboard

### Issue: Frontend using wrong configuration

**Solution:**
1. Go to Railway Dashboard → Frontend Service → Settings
2. Set Root Directory to `frontend`
3. Set Dockerfile Path to `frontend/Dockerfile`
4. Remove any `frontend/railway.toml` file

## Port Configuration

- **Backend**: Uses `$PORT` environment variable (set by Railway automatically)
  - Default fallback: 8000
  - Dockerfile CMD: `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`

- **Frontend**: Uses port 80 (NGINX default)
  - Exposed in Dockerfile: `EXPOSE 80`

## CORS Configuration

The backend CORS origins must include the frontend domain:

```bash
# In Railway → Backend Service → Variables
BACKEND_CORS_ORIGINS=https://pm.alikone.dev
```

Or multiple origins:
```bash
BACKEND_CORS_ORIGINS=https://pm.alikone.dev,https://intelligent-playfulness-production.up.railway.app
```

## Deployment Workflow

1. **Push to GitHub**: `git push origin main`
2. **Railway Auto-Deploy**:
   - Backend service builds using root `railway.toml`
   - Frontend service builds using dashboard settings
3. **Verify**:
   - Backend: `curl https://protective-playfulness-production.up.railway.app/health`
   - Frontend: Visit `https://pm.alikone.dev`

## Service Naming

- **Backend**: `protective-playfulness` → `protective-playfulness-production.up.railway.app`
- **Frontend**: `intelligent-playfulness` → Custom domain `pm.alikone.dev`
