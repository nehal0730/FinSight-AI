import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AlertTriangle, ArrowLeft, FileSearch, RefreshCw, Trash2, Sparkles } from 'lucide-react';
import RiskAnalysisDashboard from '../components/RiskAnalysisDashboard';
import { clearRiskHistory, getRiskHistoryForUser, saveRiskAnalysis } from '../utils/riskStorage';

export default function Dashboard() {
  const [riskAnalysis, setRiskAnalysis] = useState(null);
  const [riskHistory, setRiskHistory] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [error, setError] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const init = async () => {
      try {
        // Fetch documents from backend
        const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
        let backendDocuments = [];
        
        if (token) {
          try {
            const res = await axios.get('http://localhost:5000/query/documents', {
              headers: { Authorization: `Bearer ${token}` }
            });
            
            if (res.data.success && res.data.data?.documentsWithMetadata) {
              backendDocuments = res.data.data.documentsWithMetadata;
            }
          } catch (err) {
            console.error('Failed to fetch documents from backend:', err);
          }
        }

        // Get risk history from MongoDB
        const history = await getRiskHistoryForUser();
        
        // Merge backend documents with risk analysis data
        const mergedHistory = history.map(item => ({
          ...item,
          isFromBackend: backendDocuments.some(doc => doc.documentId === item.id)
        }));
        
        setRiskHistory(mergedHistory);

        // Check if viewing a specific report from Reports page
        const currentReport = localStorage.getItem('currentRiskAnalysis');
        if (currentReport) {
          const parsed = JSON.parse(currentReport);
          setSelectedId(parsed.id || '');
          setRiskAnalysis(parsed.riskResponse || parsed);
          setSelectedDocument(parsed.uploadResponse?.data?.aiResponse?.storage_ref?.id || parsed.id);
          localStorage.removeItem('currentRiskAnalysis'); // Clear after loading
          return;
        }

        // Find the latest analysis for the current user
        const latest = mergedHistory.length > 0 ? mergedHistory[0] : null;
        if (!latest) {
          setError('No risk analysis found. Upload a PDF to generate a dynamic dashboard.');
          return;
        }

        setSelectedId(latest.id || '');
        setRiskAnalysis(latest.riskResponse || latest);
        // Store the document ID for regeneration
        setSelectedDocument(latest.uploadResponse?.data?.aiResponse?.storage_ref?.id || latest.id);
      } catch (err) {
        console.error('Failed to parse risk analysis result:', err);
        setError('Risk analysis data is corrupted. Please re-upload the document.');
      }
    };

    init();
  }, []);

  const onHistoryChange = (event) => {
    const nextId = event.target.value;
    setSelectedId(nextId);
    const matched = riskHistory.find((item) => item.id === nextId);
    if (matched) {
      setRiskAnalysis(matched.riskResponse || null);
      // Store the document ID for regeneration
      setSelectedDocument(matched.uploadResponse?.data?.aiResponse?.storage_ref?.id || nextId);
    }
  };

  const onClearHistory = async () => {
    await clearRiskHistory();
    setRiskHistory([]);
    setRiskAnalysis(null);
    setSelectedId('');
    setError('History cleared. Upload a PDF to generate a new analysis.');
  };

  const hasData = useMemo(() => {
    return !!riskAnalysis && typeof riskAnalysis === 'object';
  }, [riskAnalysis]);

  const hasLLMSummary = useMemo(() => {
    if (!riskAnalysis) return false;
    const report = riskAnalysis?.report?.formatted_report || '';
    const hasSummary = riskAnalysis?.report?.llm_summary || riskAnalysis?.has_llm_summary;
    return hasSummary || (typeof report === 'string' && report.includes('SUMMARY') && report.length > 500);
  }, [riskAnalysis]);

  const regenerateWithLLM = async () => {
    if (!selectedDocument || !selectedId) {
      alert('No document selected. Please select a document first.');
      return;
    }

    setRegenerating(true);
    try {
      const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
      
      // Call backend to regenerate with LLM
      const res = await axios.post(
        'http://localhost:5000/risk-analysis/regenerate',
        { 
          documentId: selectedDocument,
          analysisId: selectedId
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      if (res.data.success && res.data.data?.riskResponse) {
        const updatedAnalysis = res.data.data.riskResponse;
        setRiskAnalysis(updatedAnalysis);
        
        // Update the record in MongoDB
        const matchedHistory = riskHistory.find(item => item.id === selectedId);
        if (matchedHistory) {
          const updated = { ...matchedHistory, riskResponse: updatedAnalysis };
          await saveRiskAnalysis(updated);
          setRiskHistory(prev => prev.map(h => h.id === selectedId ? updated : h));
        }
        
        alert('AI summary generated successfully! The dashboard has been updated.');
      }
    } catch (err) {
      console.error('Regeneration error:', err);
      const errorMsg = err.response?.data?.error || err.message || 'Failed to regenerate analysis';
      alert(`Error: ${errorMsg}`);
    } finally {
      setRegenerating(false);
    }
  };

  if (error && !hasData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50 py-14 px-4">
        <div className="max-w-2xl mx-auto bg-white rounded-2xl border border-gray-200 shadow-lg p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-amber-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Dashboard Not Ready</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => navigate('/upload')}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors cursor-pointer"
            >
              Go To Upload
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50 py-10 px-4 relative overflow-hidden">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float delay-200" />
      </div>

      <div className="relative max-w-7xl mx-auto space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-700 to-cyan-600 bg-clip-text text-transparent">
              Risk Dashboard
            </h1>
          </div>

          <div className="flex items-center gap-2">
            {riskHistory.length > 1 ? (
              <select
                value={selectedId}
                onChange={onHistoryChange}
                className="px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-700 bg-white cursor-pointer"
              >
                {riskHistory.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.fileName} - {new Date(item.createdAt).toLocaleString()}
                  </option>
                ))}
              </select>
            ) : null}
            <button
              onClick={() => navigate('/upload')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-white transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" /> Upload New File
            </button>
            {riskHistory.length > 0 ? (
              <button
                onClick={onClearHistory}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-700 hover:bg-red-50 transition-colors cursor-pointer"
              >
                <Trash2 className="w-4 h-4" /> Clear History
              </button>
            ) : null}
            {hasData && !hasLLMSummary ? (
              <button
                onClick={regenerateWithLLM}
                disabled={regenerating}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-600 text-white hover:bg-amber-700 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                title="Generate AI-powered summary"
              >
                <Sparkles className="w-4 h-4" /> {regenerating ? 'Generating...' : 'Generate AI Summary'}
              </button>
            ) : null}
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </header>

        {error ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 text-amber-800 px-4 py-3 text-sm">
            {error}
          </div>
        ) : null}

        {hasData ? <RiskAnalysisDashboard analysis={riskAnalysis} /> : null}
      </div>
    </div>
  );
}
