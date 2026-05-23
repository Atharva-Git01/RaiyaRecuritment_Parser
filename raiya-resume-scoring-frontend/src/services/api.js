/**
 * RAIYA API Service Layer — Connects Next.js frontend to FastAPI backend.
 * Replaces static data with real API calls.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ── Helper ─────────────────────────────────────────────────────────

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = typeof window !== 'undefined' ? localStorage.getItem('raiya_access_token') : null;

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `API error: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`[RAIYA API] ${endpoint}:`, err.message);
    throw err;
  }
}

// ── Auth ───────────────────────────────────────────────────────────

export async function apiLogin(email, password) {
  const data = await apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) {
    localStorage.setItem('raiya_access_token', data.access_token);
    localStorage.setItem('raiya_refresh_token', data.refresh_token);
    localStorage.setItem('raiya_user', JSON.stringify({
      id: data.user_id,
      email: data.email,
      role: data.role,
      full_name: data.full_name,
    }));
  }
  return data;
}

export async function apiSignup(fullName, email, password, orgCode) {
  return apiFetch('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
      org_code: orgCode || undefined,
    }),
  });
}

export async function apiRefreshToken() {
  const refreshToken = localStorage.getItem('raiya_refresh_token');
  if (!refreshToken) throw new Error('No refresh token');
  const data = await apiFetch('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (data.access_token) {
    localStorage.setItem('raiya_access_token', data.access_token);
    localStorage.setItem('raiya_refresh_token', data.refresh_token);
  }
  return data;
}

export function apiLogout() {
  localStorage.removeItem('raiya_access_token');
  localStorage.removeItem('raiya_refresh_token');
  localStorage.removeItem('raiya_user');
}

export function getStoredUser() {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem('raiya_user');
  return raw ? JSON.parse(raw) : null;
}

export function isAuthenticated() {
  return !!getStoredUser();
}

// ── JD ─────────────────────────────────────────────────────────────

export async function apiUploadJD(file, orgId, uploadedBy) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('org_id', orgId);
  formData.append('uploaded_by', uploadedBy);

  const url = `${API_BASE}/jd/upload`;
  const token = localStorage.getItem('raiya_access_token');
  const res = await fetch(url, {
    method: 'POST',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error('JD upload failed');
  return res.json();
}

export async function apiCreateJDManual(jdData, weightsData, orgId, uploadedBy) {
  return apiFetch(`/jd/create?org_id=${orgId}&uploaded_by=${uploadedBy}`, {
    method: 'POST',
    body: JSON.stringify({ jd_data: jdData, weights_data: weightsData }),
  });
}

export async function apiUpdateJDWeights(jdId, weightsData, verifiedBy) {
  return apiFetch(`/jd/${jdId}/weights?verified_by=${verifiedBy}`, {
    method: 'PUT',
    body: JSON.stringify(weightsData),
  });
}

export async function apiGetJD(jdId) {
  return apiFetch(`/jd/${jdId}`);
}

export async function apiListJDs(orgId) {
  return apiFetch(`/jd/?org_id=${orgId}`);
}

// ── Batch ──────────────────────────────────────────────────────────

export async function apiCreateBatch(jdId, orgId, createdBy, name) {
  return apiFetch(`/batch/create?jd_id=${jdId}&org_id=${orgId}&created_by=${createdBy}${name ? `&name=${name}` : ''}`, {
    method: 'POST',
  });
}

export async function apiUploadResumes(batchId, files) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));

  const url = `${API_BASE}/batch/${batchId}/upload-resumes`;
  const token = localStorage.getItem('raiya_access_token');
  const res = await fetch(url, {
    method: 'POST',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error('Resume upload failed');
  return res.json();
}

export async function apiStartBatch(batchId) {
  return apiFetch(`/batch/${batchId}/start`, { method: 'POST' });
}

export async function apiGetBatchStatus(batchId) {
  return apiFetch(`/batch/${batchId}/status`);
}

export async function apiGetBatchResults(batchId) {
  return apiFetch(`/batch/${batchId}/results`);
}

// ── Admin ──────────────────────────────────────────────────────────

export async function apiGetPipelineMetrics() {
  return apiFetch('/admin/metrics');
}

export async function apiGetTokenUsage() {
  return apiFetch('/admin/token-usage');
}

export async function apiGetSystemHealth() {
  return apiFetch('/admin/health');
}

// ── Backend Health Check ───────────────────────────────────────────

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE.replace('/api/v1', '')}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
