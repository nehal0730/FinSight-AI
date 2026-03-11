import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Gauge,
  ShieldAlert,
  Sparkles,
  Table,
  TrendingUp,
  Bot,
} from 'lucide-react';
import { useEffect, useState, useMemo } from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

function getRiskTheme(level) {
  const normalized = String(level || '').toUpperCase();
  if (normalized === 'HIGH') {
    return {
      ring: '#dc2626',
      badge: 'bg-red-100 text-red-700 border-red-200',
      panel: 'from-red-50 to-rose-50 border-red-200',
      text: 'text-red-700',
    };
  }
  if (normalized === 'MEDIUM' || normalized === 'LOW-MEDIUM') {
    return {
      ring: '#d97706',
      badge: 'bg-amber-100 text-amber-700 border-amber-200',
      panel: 'from-amber-50 to-orange-50 border-amber-200',
      text: 'text-amber-700',
    };
  }
  return {
    ring: '#16a34a',
    badge: 'bg-green-100 text-green-700 border-green-200',
    panel: 'from-green-50 to-emerald-50 border-green-200',
    text: 'text-green-700',
  };
}

function formatMoney(value) {
  const n = Number(value || 0);
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPct(value) {
  const n = Number(value || 0);
  return `${(n * 100).toFixed(2)}%`;
}

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

export default function RiskAnalysisDashboard({ analysis }) {
  const [toastMessage, setToastMessage] = useState('');

  const finalLevel = String(analysis?.final_risk_level || 'LOW').toUpperCase();
  const combinedScore = Number(analysis?.combined_score || 0);
  const mlScore = Number(analysis?.risk_score || 0);
  const reasons = Array.isArray(analysis?.reasons) ? analysis.reasons : [];
  const transactions = Array.isArray(analysis?.transactions) ? analysis.transactions : [];
  const report = analysis?.report || {};
  const metrics = report?.key_metrics || {};
  const insights = report?.document_insights || {};
  const isFraud = Boolean(analysis?.is_fraud);
  const llmSummary = report?.llm_summary || null;

  const theme = getRiskTheme(finalLevel);
  const normalizedPercent = Math.max(0, Math.min(100, combinedScore));
  const circumference = 2 * Math.PI * 88;
  const dash = (normalizedPercent / 100) * circumference;
  const fileBaseName = toSafeFileBaseName(report?.report_id || report?.document_name || 'risk_analysis_report');

  // --- Chart data ---
  const scoreBreakdownData = useMemo(() => ({
    labels: ['ML Score', 'Rule Score', 'Remaining'],
    datasets: [{
      data: [
        Math.round(mlScore * 100),
        Math.round(Number(analysis?.fraud_score || 0)),
        Math.max(0, 100 - Math.round(mlScore * 100) - Math.round(Number(analysis?.fraud_score || 0))),
      ],
      backgroundColor: ['#6366f1', '#06b6d4', '#e5e7eb'],
      borderColor: ['#4f46e5', '#0891b2', '#d1d5db'],
      borderWidth: 2,
      hoverOffset: 8,
    }],
  }), [mlScore, analysis?.fraud_score]);

  const scoreBreakdownOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
      legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyleWidth: 10, font: { size: 12 } } },
      tooltip: {
        callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw}` },
      },
    },
  };

  const transactionChartData = useMemo(() => {
    if (transactions.length === 0) return null;
    const debitTxns = transactions.filter(t => t.type === 'debit');
    const creditTxns = transactions.filter(t => t.type === 'credit');
    const labels = transactions.slice(0, 10).map((t, i) => t.merchant?.substring(0, 12) || `Txn ${i + 1}`);
    return {
      labels,
      datasets: [
        {
          label: 'Amount ($)',
          data: transactions.slice(0, 10).map(t => Number(t.amount || 0)),
          backgroundColor: transactions.slice(0, 10).map(t =>
            t.type === 'debit' ? 'rgba(239, 68, 68, 0.7)' : 'rgba(16, 185, 129, 0.7)'
          ),
          borderColor: transactions.slice(0, 10).map(t =>
            t.type === 'debit' ? '#dc2626' : '#059669'
          ),
          borderWidth: 1.5,
          borderRadius: 6,
        },
      ],
      meta: { totalDebit: debitTxns.reduce((s, t) => s + Number(t.amount || 0), 0), totalCredit: creditTxns.reduce((s, t) => s + Number(t.amount || 0), 0), debitCount: debitTxns.length, creditCount: creditTxns.length },
    };
  }, [transactions]);

  const transactionChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: { label: (ctx) => `$${Number(ctx.raw).toLocaleString(undefined, { minimumFractionDigits: 2 })}` },
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 45 } },
      y: { grid: { color: '#f3f4f6' }, ticks: { callback: (v) => `$${v.toLocaleString()}` } },
    },
  };

  const handleDownloadJson = () => {
    downloadTextFile(
      JSON.stringify(analysis, null, 2),
      `${fileBaseName}.json`,
      'application/json;charset=utf-8'
    );
    setToastMessage('JSON report downloaded');
  };

  const handleDownloadText = () => {
    const textReport = report?.formatted_report || 'Formatted report not available.';
    downloadTextFile(textReport, `${fileBaseName}.txt`, 'text/plain;charset=utf-8');
    setToastMessage('Text report downloaded');
  };

  useEffect(() => {
    if (!toastMessage) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setToastMessage('');
    }, 1800);

    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  return (
    <div className="space-y-8">
      {toastMessage ? (
        <div className="fixed right-6 top-20 z-50 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-800 shadow-lg">
          {toastMessage}
        </div>
      ) : null}

      <section className={`bg-gradient-to-br ${theme.panel} border rounded-2xl p-6 md:p-8 shadow-lg`}>
        <div className="grid lg:grid-cols-[320px_1fr] gap-8 items-center">
          <div className="flex justify-center">
            <div className="relative w-56 h-56">
              <svg className="-rotate-90 w-56 h-56">
                <circle cx="112" cy="112" r="88" stroke="#e5e7eb" strokeWidth="16" fill="none" />
                <circle
                  cx="112"
                  cy="112"
                  r="88"
                  stroke={theme.ring}
                  strokeWidth="16"
                  fill="none"
                  strokeDasharray={`${dash} ${circumference}`}
                  strokeLinecap="round"
                  className="transition-all duration-1000"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-4xl font-bold text-gray-900">{combinedScore.toFixed(2)}</span>
                <span className="text-sm text-gray-600">Combined / 100</span>
                <span className={`mt-3 px-3 py-1 text-xs font-bold rounded-full border ${theme.badge}`}>
                  {finalLevel}
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <Gauge className="w-6 h-6" /> Risk Analysis Result
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Final verdict from hybrid rule + ML scoring pipeline.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleDownloadJson}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" /> JSON
                </button>
                <button
                  type="button"
                  onClick={handleDownloadText}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-indigo-300 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" /> TXT
                </button>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                    isFraud ? 'bg-red-100 text-red-700 border-red-200' : 'bg-green-100 text-green-700 border-green-200'
                  }`}
                >
                  {isFraud ? 'Fraud Flagged' : 'No Fraud Flag'}
                </span>
              </div>
            </div>

            <div className="grid sm:grid-cols-3 gap-4">
              <div className="bg-white/80 rounded-xl p-4 border border-gray-200">
                <p className="text-xs text-gray-500">Combined Score</p>
                <p className="text-lg font-semibold text-gray-900">{combinedScore.toFixed(2)} / 100</p>
              </div>
              <div className="bg-white/80 rounded-xl p-4 border border-gray-200">
                <p className="text-xs text-gray-500">Rule Fraud Score</p>
                <p className="text-lg font-semibold text-gray-900">{Number(analysis?.fraud_score || 0).toFixed(2)} / 100</p>
              </div>
              <div className="bg-white/80 rounded-xl p-4 border border-gray-200">
                <p className="text-xs text-gray-500">Transactions Extracted</p>
                <p className="text-lg font-semibold text-gray-900">{Number(analysis?.transactions_extracted || transactions.length)}</p>
              </div>
            </div>
          </div>
        </div>

        {/* ML Model Breakdown */}
        <div className="mt-4 flex items-center gap-4 px-2">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Bot className="w-3.5 h-3.5" />
            <span className="font-medium">ML Model Breakdown:</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-white/80 border border-gray-200 text-gray-700">
              ML Score: <span className="font-semibold text-gray-900">{formatPct(mlScore)}</span>
            </span>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border ${
              String(analysis?.ml_risk_level || '').toUpperCase() === 'HIGH'
                ? 'bg-red-50 border-red-200 text-red-700'
                : String(analysis?.ml_risk_level || '').toUpperCase() === 'MEDIUM'
                  ? 'bg-amber-50 border-amber-200 text-amber-700'
                  : 'bg-green-50 border-green-200 text-green-700'
            }`}>
              ML Risk Level: <span className="font-semibold">{String(analysis?.ml_risk_level || 'N/A').toUpperCase()}</span>
            </span>
          </div>
        </div>
      </section>

      <section className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5" /> Reasons For Risk
          </h3>
          {reasons.length === 0 ? (
            <p className="text-sm text-gray-500">No explicit risk reasons were produced.</p>
          ) : (
            <ul className="space-y-3 max-h-72 overflow-auto pr-2">
              {reasons.map((reason, idx) => (
                <li key={`${reason}-${idx}`} className="flex gap-3 text-sm text-gray-700 p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <span className="mt-0.5"><AlertTriangle className="w-4 h-4 text-amber-600" /></span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5" /> Document Analysis Summary
          </h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Document</span><span className="font-medium text-gray-900 truncate max-w-[60%] text-right">{report.document_name || 'N/A'}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Report ID</span><span className="font-medium text-gray-900 truncate max-w-[60%] text-right">{report.report_id || 'N/A'}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Generated At</span><span className="font-medium text-gray-900">{report.timestamp || 'N/A'}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Pages</span><span className="font-medium text-gray-900">{insights.pages ?? 'N/A'}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">OCR Pages</span><span className="font-medium text-gray-900">{insights.ocr_pages ?? 'N/A'}</span></div>
          </div>
        </div>
      </section>

      {/* Recommendation — full width */}
      <section className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
        <div className="p-4 rounded-xl bg-indigo-50 border border-indigo-200">
          <p className="text-xs font-semibold text-indigo-700 mb-1">Recommendation</p>
          <p className="text-sm text-indigo-900">{report.recommendation || 'No recommendation generated.'}</p>
        </div>
      </section>

      {/* AI-Generated Summary — full width */}
      {llmSummary && (
        <section className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
          <div className="p-4 rounded-xl bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200">
            <p className="text-xs font-semibold text-purple-700 mb-2 flex items-center gap-1.5">
              <Bot className="w-3.5 h-3.5" /> AI-Generated Summary
            </p>
            <p className="text-sm text-purple-900 whitespace-pre-line leading-relaxed">{llmSummary}</p>
          </div>
        </section>
      )}

      <section className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5" /> Key Metrics
        </h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
            <p className="text-xs text-gray-500">Total Debited</p>
            <p className="text-lg font-semibold text-gray-900">${formatMoney(metrics.total_debited)}</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
            <p className="text-xs text-gray-500">Total Credited</p>
            <p className="text-lg font-semibold text-gray-900">${formatMoney(metrics.total_credited)}</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
            <p className="text-xs text-gray-500">High-Risk Merchants</p>
            <p className="text-lg font-semibold text-gray-900">{Number(metrics.high_risk_merchants || 0)}</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
            <p className="text-xs text-gray-500">Max Transaction</p>
            <p className="text-lg font-semibold text-gray-900">${formatMoney(metrics.max_transaction_amount)}</p>
          </div>
        </div>
      </section>

      {/* ---- Charts Section ---- */}
      <section className="grid lg:grid-cols-2 gap-6">
        {/* Score Breakdown Doughnut */}
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm hover:shadow-lg transition-shadow">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-indigo-600" /> Score Breakdown
          </h3>
          <div className="h-64">
            <Doughnut data={scoreBreakdownData} options={scoreBreakdownOptions} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="text-center p-3 rounded-xl bg-indigo-50 border border-indigo-100">
              <p className="text-xs text-indigo-600 font-semibold">ML Risk</p>
              <p className="text-xl font-bold text-indigo-700">{formatPct(mlScore)}</p>
            </div>
            <div className="text-center p-3 rounded-xl bg-cyan-50 border border-cyan-100">
              <p className="text-xs text-cyan-600 font-semibold">Rule Score</p>
              <p className="text-xl font-bold text-cyan-700">{Number(analysis?.fraud_score || 0).toFixed(1)}</p>
            </div>
          </div>
        </div>

        {/* Transaction Bar Chart */}
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm hover:shadow-lg transition-shadow">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-600" /> Transaction Distribution
          </h3>
          {transactionChartData ? (
            <>
              <div className="h-64">
                <Bar data={transactionChartData} options={transactionChartOptions} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="text-center p-3 rounded-xl bg-red-50 border border-red-100">
                  <p className="text-xs text-red-600 font-semibold">Debits ({transactionChartData.meta.debitCount})</p>
                  <p className="text-lg font-bold text-red-700">${formatMoney(transactionChartData.meta.totalDebit)}</p>
                </div>
                <div className="text-center p-3 rounded-xl bg-green-50 border border-green-100">
                  <p className="text-xs text-green-600 font-semibold">Credits ({transactionChartData.meta.creditCount})</p>
                  <p className="text-lg font-bold text-green-700">${formatMoney(transactionChartData.meta.totalCredit)}</p>
                </div>
              </div>
            </>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-400">
              <p className="text-sm">No transaction data to chart</p>
            </div>
          )}
        </div>
      </section>

      <section className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Table className="w-5 h-5" /> Extracted Transactions (Top 10)
        </h3>
        {transactions.length === 0 ? (
          <p className="text-sm text-gray-500">No transactions to display.</p>
        ) : (
          <div className="overflow-auto rounded-xl border border-gray-200">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  <th className="py-3 px-4 text-left">#</th>
                  <th className="py-3 px-4 text-left">Date</th>
                  <th className="py-3 px-4 text-left">Merchant</th>
                  <th className="py-3 px-4 text-center">Type</th>
                  <th className="py-3 px-4 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {transactions.map((tx, idx) => (
                  <tr key={`${tx.date}-${tx.merchant}-${idx}`} className="hover:bg-gray-50/60 transition-colors">
                    <td className="py-3 px-4 text-gray-400 font-medium">{idx + 1}</td>
                    <td className="py-3 px-4 text-gray-600 font-mono text-xs">{tx.date}</td>
                    <td className="py-3 px-4 text-gray-900 font-medium">{tx.merchant}</td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${
                          tx.type === 'debit'
                            ? 'bg-red-50 text-red-600 ring-1 ring-red-200'
                            : 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-200'
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${tx.type === 'debit' ? 'bg-red-500' : 'bg-emerald-500'}`} />
                        {tx.type}
                      </span>
                    </td>
                    <td className={`py-3 px-4 text-right font-semibold tabular-nums ${tx.type === 'debit' ? 'text-red-600' : 'text-emerald-600'}`}>
                      {tx.type === 'debit' ? '−' : '+'}${formatMoney(tx.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

    </div>
  );
}
