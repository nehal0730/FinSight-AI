import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function getAuthHeaders() {
  const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getRiskHistory() {
  try {
    const res = await axios.get(`${API_BASE_URL}/risk-analysis/history`, {
      headers: getAuthHeaders(),
    });
    if (res.data.success) {
      return Array.isArray(res.data.data) ? res.data.data : [];
    }
    return [];
  } catch {
    return [];
  }
}

export async function getRiskHistoryForUser() {
  return getRiskHistory();
}

export async function saveRiskAnalysis(record) {
  if (!record || typeof record !== 'object') return;
  try {
    await axios.post(
      `${API_BASE_URL}/risk-analysis`,
      {
        id: record.id,
        fileName: record.fileName,
        uploadResponse: record.uploadResponse,
        riskResponse: record.riskResponse,
      },
      { headers: getAuthHeaders() }
    );
  } catch (err) {
    console.error('Failed to save risk analysis to server:', err);
  }
}

export async function clearRiskHistory() {
  try {
    await axios.delete(`${API_BASE_URL}/risk-analysis/history`, {
      headers: getAuthHeaders(),
    });
  } catch (err) {
    console.error('Failed to clear risk history:', err);
  }
}

export function buildRiskRecord(file, riskResponse, uploadResponse = null) {
  const now = new Date();
  const fallbackName = file?.name || 'unknown.pdf';
  const reportId = riskResponse?.report?.report_id;
  const id = reportId || `risk_${now.getTime()}_${Math.random().toString(16).slice(2, 8)}`;

  return {
    id,
    createdAt: now.toISOString(),
    fileName: riskResponse?.report?.document_name || uploadResponse?.fileName || fallbackName,
    uploadResponse,
    riskResponse,
  };
}
