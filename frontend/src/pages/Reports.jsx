import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  FileText, AlertTriangle, CheckCircle,
  Download, Eye, Trash2, Sparkles, TrendingUp, Shield,
  ExternalLink, FileDown, Search, X, Clock,
  ChevronDown, ChevronUp, ArrowUpDown, Filter, LayoutGrid, List
} from 'lucide-react';
import { getRiskHistoryForUser, clearRiskHistory, saveRiskAnalysis } from '../utils/riskStorage';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';

ChartJS.register(ArcElement, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Filler, Title, Tooltip, Legend);

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function toSafeFileBaseName(rawName) {
  const base = String(rawName || 'risk_analysis_report').replace(/\.[^.]+$/, '');
  return base.replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 80) || 'risk_analysis_report';
}

function downloadTextFile(content, fileName, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

function formatBytes(bytes) {
  if (!bytes) return '--';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function RiskGauge({ score, size = 80 }) {
  const radius = (size - 8) / 2;
  const circumference = Math.PI * radius;
  const progress = (Math.min(score, 100) / 100) * circumference;
  const color = score >= 70 ? '#ef4444' : score >= 40 ? '#6366f1' : '#10b981';

  return (
    <svg width={size} height={size / 2 + 12} viewBox={`0 0 ${size} ${size / 2 + 12}`}>
      <path
        d={`M 4 ${size / 2 + 4} A ${radius} ${radius} 0 0 1 ${size - 4} ${size / 2 + 4}`}
        fill="none"
        stroke="#e5e7eb"
        strokeWidth="6"
        strokeLinecap="round"
      />
      <path
        d={`M 4 ${size / 2 + 4} A ${radius} ${radius} 0 0 1 ${size - 4} ${size / 2 + 4}`}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeLinecap="round"
        strokeDasharray={`${progress} ${circumference}`}
        className="transition-all duration-700 ease-out"
      />
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        className="text-sm font-bold"
        fill={color}
        fontSize="16"
        fontWeight="700"
      >
        {score.toFixed(0)}
      </text>
    </svg>
  );
}

export default function Reports() {
  const [expandedId, setExpandedId] = useState(null);
  const [reports, setReports] = useState([]);
  const [regeneratingId, setRegeneratingId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [backendDocs, setBackendDocs] = useState([]);
  const [sortBy, setSortBy] = useState('date');
  const [sortDir, setSortDir] = useState('desc');
  const [filterLevel, setFilterLevel] = useState('all');
  const [viewMode, setViewMode] = useState('table');
  const navigate = useNavigate();

  useEffect(() => {
    loadReports();
    fetchBackendDocuments();
  }, []);

  const loadReports = async () => {
    const history = await getRiskHistoryForUser();
    setReports(history);
  };

  const fetchBackendDocuments = async () => {
    try {
      const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
      if (!token) return;
      const res = await axios.get(`${API_BASE_URL}/query/documents`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.data.success && res.data.data?.documentsWithMetadata) {
        setBackendDocs(res.data.data.documentsWithMetadata);
      }
    } catch (err) {
      console.error('Failed to fetch backend documents:', err);
    }
  };

  const getDocMeta = (report) => {
    const docId = report?.uploadResponse?.data?.aiResponse?.storage_ref?.id || report?.id;
    return backendDocs.find(d => d.documentId === docId);
  };

  const getRiskColor = (level) => {
    const n = String(level || '').toUpperCase();
    if (n === 'HIGH') return { text: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-100 text-red-700', dot: 'bg-red-500' };
    if (n === 'MEDIUM' || n === 'LOW-MEDIUM') return { text: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200', badge: 'bg-indigo-100 text-indigo-700', dot: 'bg-indigo-500' };
    return { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', badge: 'bg-emerald-100 text-emerald-700', dot: 'bg-emerald-500' };
  };

  const getRiskScore = (r) => Number(r?.riskResponse?.combined_score || 0);
  const getRiskLevel = (r) => String(r?.riskResponse?.final_risk_level || 'LOW').toUpperCase();

  const handleViewAnalysis = (report) => {
    if (report?.riskResponse) {
      localStorage.setItem('currentRiskAnalysis', JSON.stringify(report));
      navigate('/dashboard');
    }
  };

  const handleViewPdf = (report) => {
    const docId = report?.uploadResponse?.data?.aiResponse?.storage_ref?.id || report?.id;
    const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
    window.open(`${API_BASE_URL}/upload/pdf/${encodeURIComponent(docId)}?token=${encodeURIComponent(token)}`, '_blank');
  };

  const handleDownloadPdf = async (report) => {
    const docId = report?.uploadResponse?.data?.aiResponse?.storage_ref?.id || report?.id;
    const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
    try {
      const res = await axios.get(
        `${API_BASE_URL}/upload/pdf/${encodeURIComponent(docId)}?action=download`,
        { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' }
      );
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = report.fileName || 'document.pdf';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.response?.status === 404 ? 'PDF not available. It was uploaded before PDF storage was enabled.' : 'Failed to download PDF.');
    }
  };

  const handleExportJson = (report) => {
    if (!report?.riskResponse) return;
    downloadTextFile(JSON.stringify(report.riskResponse, null, 2), `${toSafeFileBaseName(report.fileName)}.json`, 'application/json;charset=utf-8');
  };

  const handleExportText = (report) => {
    if (!report?.riskResponse) return;
    downloadTextFile(report.riskResponse?.report?.formatted_report || 'Report not available.', `${toSafeFileBaseName(report.fileName)}.txt`, 'text/plain;charset=utf-8');
  };

  const handleClearHistory = async () => {
    if (window.confirm('Delete all reports? This cannot be undone.')) {
      await clearRiskHistory();
      setReports([]);
      setExpandedId(null);
    }
  };

  const hasLLMSummary = (report) => {
    if (!report?.riskResponse) return false;
    const fmt = report.riskResponse?.report?.formatted_report || '';
    return report.riskResponse?.report?.llm_summary || report.riskResponse?.has_llm_summary ||
      (typeof fmt === 'string' && fmt.includes('SUMMARY') && fmt.length > 500);
  };

  const regenerateWithLLM = async (report) => {
    if (!report) return;
    setRegeneratingId(report.id);
    try {
      const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
      const res = await axios.post(
        `${API_BASE_URL}/risk-analysis/regenerate`,
        {
          documentId: report.uploadResponse?.data?.aiResponse?.storage_ref?.id || report.id,
          analysisId: report.id
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.data.success && res.data.data?.riskResponse) {
        const updated = { ...report, riskResponse: res.data.data.riskResponse };
        setReports(prev => prev.map(r => r.id === report.id ? updated : r));
        await saveRiskAnalysis(updated);
      }
    } catch (err) {
      alert(`Error: ${err.response?.data?.error || err.message}`);
    } finally {
      setRegeneratingId(null);
    }
  };

  const filteredReports = useMemo(() => {
    let list = reports;
    if (filterLevel !== 'all') {
      list = list.filter(r => {
        const lvl = getRiskLevel(r);
        if (filterLevel === 'high') return lvl === 'HIGH';
        if (filterLevel === 'medium') return lvl === 'MEDIUM' || lvl === 'LOW-MEDIUM';
        return lvl === 'LOW';
      });
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(r =>
        r.fileName?.toLowerCase().includes(q) ||
        getRiskLevel(r).toLowerCase().includes(q) ||
        r.id?.toLowerCase().includes(q)
      );
    }
    list = [...list].sort((a, b) => {
      if (sortBy === 'date') {
        const da = new Date(a.createdAt).getTime();
        const db = new Date(b.createdAt).getTime();
        return sortDir === 'desc' ? db - da : da - db;
      }
      if (sortBy === 'score') {
        return sortDir === 'desc' ? getRiskScore(b) - getRiskScore(a) : getRiskScore(a) - getRiskScore(b);
      }
      if (sortBy === 'name') {
        const cmp = (a.fileName || '').localeCompare(b.fileName || '');
        return sortDir === 'desc' ? -cmp : cmp;
      }
      return 0;
    });
    return list;
  }, [reports, searchQuery, sortBy, sortDir, filterLevel]);

  const toggleSort = (field) => {
    if (sortBy === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(field); setSortDir('desc'); }
  };

  const averageRiskScore = reports.length > 0 ? Math.round(reports.reduce((s, r) => s + getRiskScore(r), 0) / reports.length) : 0;
  const highRiskCount = reports.filter(r => getRiskLevel(r) === 'HIGH').length;
  const mediumRiskCount = reports.filter(r => ['MEDIUM', 'LOW-MEDIUM'].includes(getRiskLevel(r))).length;
  const lowRiskCount = reports.filter(r => getRiskLevel(r) === 'LOW').length;

  const doughnutCenterPlugin = useMemo(() => ({
    id: 'doughnutCenter',
    beforeDraw(chart) {
      const { ctx, width, height } = chart;
      const total = chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
      if (!total) return;
      ctx.save();
      ctx.font = 'bold 28px Inter, system-ui, sans-serif';
      ctx.fillStyle = '#111827';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(total, width / 2, height / 2 - 8);
      ctx.font = '500 11px Inter, system-ui, sans-serif';
      ctx.fillStyle = '#9ca3af';
      ctx.fillText('TOTAL', width / 2, height / 2 + 14);
      ctx.restore();
    },
  }), []);

  const riskDistributionData = useMemo(() => ({
    labels: ['High Risk', 'Medium Risk', 'Low Risk'],
    datasets: [{
      data: [highRiskCount, mediumRiskCount, lowRiskCount],
      backgroundColor: [
        'rgba(239, 68, 68, 0.8)',
        'rgba(99, 102, 241, 0.8)',
        'rgba(16, 185, 129, 0.8)',
      ],
      hoverBackgroundColor: [
        'rgba(239, 68, 68, 1)',
        'rgba(99, 102, 241, 1)',
        'rgba(16, 185, 129, 1)',
      ],
      borderColor: '#ffffff',
      borderWidth: 3,
      hoverOffset: 8,
      spacing: 2,
      borderRadius: 4,
    }],
  }), [highRiskCount, mediumRiskCount, lowRiskCount]);

  const riskScoreBarData = useMemo(() => {
    if (reports.length === 0) return null;
    const sorted = [...reports].reverse().slice(-10);
    return {
      labels: sorted.map(r => {
        const name = r.fileName?.replace('.pdf', '') || 'Report';
        return name.length > 14 ? name.substring(0, 14) + '...' : name;
      }),
      datasets: [{
        label: 'Risk Score',
        data: sorted.map(r => getRiskScore(r)),
        backgroundColor: sorted.map(r => {
          const s = getRiskScore(r);
          return s >= 70 ? 'rgba(239, 68, 68, 0.18)' : s >= 40 ? 'rgba(99, 102, 241, 0.18)' : 'rgba(16, 185, 129, 0.18)';
        }),
        hoverBackgroundColor: sorted.map(r => {
          const s = getRiskScore(r);
          return s >= 70 ? 'rgba(239, 68, 68, 0.35)' : s >= 40 ? 'rgba(99, 102, 241, 0.35)' : 'rgba(16, 185, 129, 0.35)';
        }),
        borderColor: sorted.map(r => {
          const s = getRiskScore(r);
          return s >= 70 ? '#ef4444' : s >= 40 ? '#6366f1' : '#10b981';
        }),
        borderWidth: 2,
        borderRadius: 10,
        borderSkipped: false,
        barPercentage: 0.7,
        categoryPercentage: 0.8,
      }],
    };
  }, [reports]);

  if (reports.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-indigo-50 to-indigo-100 flex items-center justify-center">
            <FileText className="w-10 h-10 text-indigo-400" />
          </div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">No reports yet</h2>
          <p className="text-gray-500 mb-8">Upload and analyze a financial document to see your first risk report here.</p>
          <button
            onClick={() => navigate('/upload')}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors cursor-pointer"
          >
            Upload a Document
          </button>
        </div>
      </div>
    );
  }

  const SortIcon = ({ field }) => (
    <ArrowUpDown className={`w-3 h-3 inline ml-1 ${sortBy === field ? 'text-indigo-500' : 'text-gray-400'}`} />
  );

  const renderReportCard = (report) => {
    const score = getRiskScore(report);
    const level = getRiskLevel(report);
    const colors = getRiskColor(level);
    const isFraud = report?.riskResponse?.is_fraud;
    const isExpanded = expandedId === report.id;

    return (
      <div key={report.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-md transition-all">
        <div
          className="p-5 cursor-pointer"
          onClick={() => setExpandedId(isExpanded ? null : report.id)}
        >
          <div className="flex items-center gap-4">
            {/* Score circle */}
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${colors.bg} border ${colors.border} flex-shrink-0`}>
              <span className={`text-lg font-bold tabular-nums ${colors.text}`}>{score.toFixed(0)}</span>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-sm font-semibold text-gray-900 truncate">{report.fileName}</h3>
                {isFraud && (
                  <span className="flex-shrink-0 inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-bold rounded-md bg-red-600 text-white uppercase">
                    <AlertTriangle className="w-2.5 h-2.5" /> Fraud
                  </span>
                )}
                {hasLLMSummary(report) && (
                  <span className="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-semibold rounded-md bg-purple-100 text-purple-700">AI</span>
                )}
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(report.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold ${colors.badge}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
                  {level}
                </span>
              </div>
            </div>

            <div className="flex-shrink-0">
              {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
            </div>
          </div>
        </div>

        {isExpanded && renderExpandedActions(report)}
      </div>
    );
  };

  const renderExpandedActions = (report) => {
    const score = getRiskScore(report);
    const level = getRiskLevel(report);
    const colors = getRiskColor(level);

    return (
      <div className="px-5 pb-5 border-t border-gray-100">
        <div className="pt-4 flex flex-wrap gap-2">
          <button
            onClick={() => handleViewAnalysis(report)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors cursor-pointer"
          >
            <Eye className="w-3.5 h-3.5" /> Dashboard
          </button>
          <button
            onClick={() => handleViewPdf(report)}
            className="inline-flex items-center gap-1.5 px-4 py-2 border border-gray-200 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <ExternalLink className="w-3.5 h-3.5" /> View PDF
          </button>
          <button
            onClick={() => handleDownloadPdf(report)}
            className="inline-flex items-center gap-1.5 px-4 py-2 border border-gray-200 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <FileDown className="w-3.5 h-3.5" /> Save PDF
          </button>
          <button
            onClick={() => handleExportJson(report)}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" /> JSON
          </button>
          <button
            onClick={() => handleExportText(report)}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" /> TXT
          </button>
          {!hasLLMSummary(report) && (
            <button
              onClick={() => regenerateWithLLM(report)}
              disabled={regeneratingId === report.id}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-purple-500 to-indigo-500 text-white text-xs font-medium rounded-lg hover:from-purple-600 hover:to-indigo-600 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles className="w-3.5 h-3.5" /> {regeneratingId === report.id ? 'Generating...' : 'AI Summary'}
            </button>
          )}
        </div>
        <div className="mt-3 pt-3 border-t border-gray-50 flex items-center gap-4 text-[11px] text-gray-400">
          <span>ID: <span className="font-mono">{report.id?.substring(0, 16)}...</span></span>
          <span>{new Date(report.createdAt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
          {report?.riskResponse?.transactions_extracted && (
            <span>{report.riskResponse.transactions_extracted} transactions</span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50/50">
      {/* Page header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
              <p className="text-sm text-gray-500 mt-0.5">{reports.length} risk {reports.length === 1 ? 'analysis' : 'analyses'} completed</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate('/upload')}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors cursor-pointer"
              >
                + New Upload
              </button>
              <button
                onClick={handleClearHistory}
                className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                title="Clear all reports"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Inline stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <button
              onClick={() => setFilterLevel('all')}
              className={`p-4 rounded-xl text-left transition-all cursor-pointer ${filterLevel === 'all' ? 'bg-indigo-50 ring-1 ring-indigo-200' : 'bg-gray-50 hover:bg-gray-100'}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Total</span>
                <FileText className="w-4 h-4 text-indigo-500" />
              </div>
              <p className="text-2xl font-bold text-gray-900">{reports.length}</p>
            </button>
            <button
              onClick={() => setFilterLevel(filterLevel === 'high' ? 'all' : 'high')}
              className={`p-4 rounded-xl text-left transition-all cursor-pointer ${filterLevel === 'high' ? 'bg-red-50 ring-1 ring-red-200' : 'bg-gray-50 hover:bg-gray-100'}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">High Risk</span>
                <AlertTriangle className="w-4 h-4 text-red-500" />
              </div>
              <p className="text-2xl font-bold text-gray-900">{highRiskCount}</p>
            </button>
            <button
              onClick={() => setFilterLevel(filterLevel === 'medium' ? 'all' : 'medium')}
              className={`p-4 rounded-xl text-left transition-all cursor-pointer ${filterLevel === 'medium' ? 'bg-indigo-50 ring-1 ring-indigo-200' : 'bg-gray-50 hover:bg-gray-100'}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Medium</span>
                <TrendingUp className="w-4 h-4 text-indigo-500" />
              </div>
              <p className="text-2xl font-bold text-gray-900">{mediumRiskCount}</p>
            </button>
            <button
              onClick={() => setFilterLevel(filterLevel === 'low' ? 'all' : 'low')}
              className={`p-4 rounded-xl text-left transition-all cursor-pointer ${filterLevel === 'low' ? 'bg-emerald-50 ring-1 ring-emerald-200' : 'bg-gray-50 hover:bg-gray-100'}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Low Risk</span>
                <Shield className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-2xl font-bold text-gray-900">{lowRiskCount}</p>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
            {/* Doughnut card */}
            <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-6 pt-5 pb-2 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">Risk Distribution</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Across all analyzed documents</p>
                </div>
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
                  <Shield className="w-4 h-4 text-indigo-500" />
                </div>
              </div>
              <div className="px-6 pb-5">
                <div className="h-56 flex items-center justify-center">
                  <Doughnut
                    data={riskDistributionData}
                    plugins={[doughnutCenterPlugin]}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      cutout: '75%',
                      animation: { animateRotate: true, animateScale: true, duration: 800, easing: 'easeOutQuart' },
                      plugins: {
                        legend: {
                          position: 'bottom',
                          labels: {
                            padding: 16,
                            usePointStyle: true,
                            pointStyleWidth: 8,
                            font: { size: 12, weight: 600, family: 'Inter, system-ui, sans-serif' },
                            color: '#374151',
                            generateLabels: (chart) => {
                              const data = chart.data;
                              return data.labels.map((label, i) => ({
                                text: `${label}  (${data.datasets[0].data[i]})`,
                                fillStyle: data.datasets[0].backgroundColor[i],
                                strokeStyle: 'transparent',
                                pointStyle: 'rectRounded',
                                index: i,
                                hidden: false,
                              }));
                            },
                          },
                        },
                        tooltip: {
                          backgroundColor: 'rgba(17, 24, 39, 0.95)',
                          titleFont: { size: 13, weight: 600, family: 'Inter, system-ui, sans-serif' },
                          bodyFont: { size: 12, family: 'Inter, system-ui, sans-serif' },
                          cornerRadius: 10,
                          padding: { top: 10, bottom: 10, left: 14, right: 14 },
                          boxPadding: 6,
                          callbacks: {
                            label: (ctx) => {
                              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                              const pct = total ? Math.round((ctx.raw / total) * 100) : 0;
                              return ` ${ctx.raw} reports (${pct}%)`;
                            },
                          },
                        },
                      },
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Bar chart card */}
            <div className="lg:col-span-3 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-6 pt-5 pb-2 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">Score Trends</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Last {Math.min(reports.length, 10)} analyzed documents</p>
                </div>
                <div className="flex items-center gap-3 text-[10px] font-semibold">
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-red-400/40 border border-red-400" />High</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-indigo-400/40 border border-indigo-400" />Medium</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-emerald-400/40 border border-emerald-400" />Low</span>
                </div>
              </div>
              <div className="px-6 pb-5">
                {riskScoreBarData ? (
                  <div className="h-56">
                    <Bar
                      data={riskScoreBarData}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: { duration: 700, easing: 'easeOutQuart' },
                        interaction: { mode: 'index', intersect: false },
                        plugins: {
                          legend: { display: false },
                          tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            titleFont: { size: 13, weight: 600, family: 'Inter, system-ui, sans-serif' },
                            bodyFont: { size: 12, family: 'Inter, system-ui, sans-serif' },
                            cornerRadius: 10,
                            padding: { top: 10, bottom: 10, left: 14, right: 14 },
                            boxPadding: 6,
                            displayColors: true,
                            callbacks: {
                              title: (items) => items[0]?.label || '',
                              label: (ctx) => {
                                const score = ctx.raw;
                                const tag = score >= 70 ? ' (High)' : score >= 40 ? ' (Medium)' : ' (Low)';
                                return ` Risk Score: ${score}/100${tag}`;
                              },
                            },
                          },
                        },
                        scales: {
                          x: {
                            grid: { display: false },
                            border: { display: false },
                            ticks: {
                              font: { size: 11, weight: 500, family: 'Inter, system-ui, sans-serif' },
                              color: '#6b7280',
                              maxRotation: 40,
                              padding: 4,
                            },
                          },
                          y: {
                            grid: { color: 'rgba(243, 244, 246, 0.8)', lineWidth: 1 },
                            border: { display: false, dash: [4, 4] },
                            min: 0,
                            max: 100,
                            ticks: {
                              stepSize: 25,
                              font: { size: 11, weight: 500, family: 'Inter, system-ui, sans-serif' },
                              color: '#9ca3af',
                              padding: 8,
                              callback: (v) => v + '%',
                            },
                          },
                        },
                      }}
                    />
                  </div>
                ) : (
                  <div className="h-56 flex items-center justify-center text-gray-400 text-sm">No data yet</div>
                )}
              </div>
            </div>
          </div>

        {/* Toolbar */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search reports..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-10 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-300 transition-all"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer">
                <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
              </button>
            )}
          </div>

          {filterLevel !== 'all' && (
            <button
              onClick={() => setFilterLevel('all')}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 transition-colors cursor-pointer"
            >
              <X className="w-3 h-3" /> {filterLevel.charAt(0).toUpperCase() + filterLevel.slice(1)} risk
            </button>
          )}

          <div className="ml-auto flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded-md cursor-pointer transition-colors ${viewMode === 'table' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
              title="Table view"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-md cursor-pointer transition-colors ${viewMode === 'grid' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
              title="Card view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* View content */}
        {viewMode === 'table' ? (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th
                      className="text-left px-5 py-3.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700 select-none"
                      onClick={() => toggleSort('name')}
                    >
                      Document <SortIcon field="name" />
                    </th>
                    <th
                      className="text-left px-5 py-3.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700 select-none"
                      onClick={() => toggleSort('score')}
                    >
                      Risk Score <SortIcon field="score" />
                    </th>
                    <th className="text-left px-5 py-3.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th
                      className="text-left px-5 py-3.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700 select-none"
                      onClick={() => toggleSort('date')}
                    >
                      Date <SortIcon field="date" />
                    </th>
                    <th className="text-right px-5 py-3.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filteredReports.map((report) => {
                    const score = getRiskScore(report);
                    const level = getRiskLevel(report);
                    const colors = getRiskColor(level);
                    const isFraud = report?.riskResponse?.is_fraud;
                    const isExpanded = expandedId === report.id;

                    return (
                      <tr
                        key={report.id}
                        className={`group transition-colors ${isExpanded ? 'bg-gray-50/50' : 'hover:bg-gray-50/50'}`}
                      >
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${colors.dot}`} />
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate max-w-[280px]">{report.fileName}</p>
                              <p className="text-[11px] text-gray-400 font-mono mt-0.5">{report.id?.substring(0, 12)}...</p>
                            </div>
                            {isFraud && (
                              <span className="flex-shrink-0 inline-flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-bold rounded bg-red-600 text-white uppercase">Fraud</span>
                            )}
                            {hasLLMSummary(report) && (
                              <span className="flex-shrink-0 px-1.5 py-0.5 text-[9px] font-semibold rounded bg-purple-100 text-purple-700">AI</span>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-20">
                              <div className="flex items-baseline gap-1 mb-1">
                                <span className={`text-sm font-bold tabular-nums ${colors.text}`}>{score.toFixed(0)}</span>
                                <span className="text-[10px] text-gray-400">/100</span>
                              </div>
                              <div className="h-1.5 rounded-full bg-gray-100 w-full">
                                <div
                                  className={`h-1.5 rounded-full transition-all duration-500 ${score >= 70 ? 'bg-red-400' : score >= 40 ? 'bg-indigo-400' : 'bg-emerald-400'}`}
                                  style={{ width: `${Math.min(score, 100)}%` }}
                                />
                              </div>
                            </div>
                            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${colors.badge}`}>
                              {level}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700">
                            <CheckCircle className="w-3 h-3" /> Done
                          </span>
                        </td>
                        <td className="px-5 py-4 text-gray-600 text-sm">
                          <div>
                            <p>{new Date(report.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</p>
                            <p className="text-[11px] text-gray-400">{new Date(report.createdAt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</p>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => handleViewAnalysis(report)}
                              className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors cursor-pointer"
                              title="Open dashboard"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleViewPdf(report)}
                              className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                              title="View PDF"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDownloadPdf(report)}
                              className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                              title="Download PDF"
                            >
                              <FileDown className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleExportJson(report)}
                              className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                              title="Export JSON"
                            >
                              <Download className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleExportText(report)}
                              className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                              title="Export TXT"
                            >
                              <FileText className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {filteredReports.length === 0 && (
              <div className="text-center py-12 text-gray-400 text-sm">
                {searchQuery ? <>No reports match &ldquo;{searchQuery}&rdquo;</> : 'No reports found'}
              </div>
            )}
          </div>
        ) : (
          /* Card/Grid view */
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredReports.map(renderReportCard)}
            {filteredReports.length === 0 && (
              <div className="col-span-full text-center py-12 text-gray-400 text-sm">
                {searchQuery ? <>No reports match &ldquo;{searchQuery}&rdquo;</> : 'No reports found'}
              </div>
            )}
          </div>
        )}

        {/* Footer info */}
        <div className="flex items-center justify-between text-xs text-gray-400 pt-2">
          <span>Showing {filteredReports.length} of {reports.length} reports</span>
        </div>
      </div>
    </div>
  );
}
