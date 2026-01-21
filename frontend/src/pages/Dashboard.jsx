import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

export default function Dashboard() {
  const [analysisData, setAnalysisData] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    try {
      // Get analysis result from localStorage (or use dummy data)
      const stored = localStorage.getItem('analysisResult');
      if (stored) {
        const parsed = JSON.parse(stored);
        setAnalysisData(parsed);
      } else {
        // Dummy data for demonstration
        setAnalysisData(getDummyData());
      }
    } catch (err) {
      console.error('Error loading analysis data:', err);
      setError('Failed to load analysis data');
      setAnalysisData(getDummyData());
    }
  }, []);

  const getDummyData = () => ({
    riskScore: 72,
    fileName: 'financial_report_2024.pdf',
    uploadDate: new Date().toLocaleDateString(),
    metrics: {
      revenue: '$2.5M',
      expenses: '$1.8M',
      profit: '$700K',
      profitMargin: '28%',
    },
    riskFactors: [
      { name: 'Liquidity Risk', level: 'Medium', score: 65 },
      { name: 'Credit Risk', level: 'Low', score: 35 },
      { name: 'Market Risk', level: 'High', score: 85 },
      { name: 'Operational Risk', level: 'Low', score: 40 },
    ],
    insights: [
      'Revenue has increased by 15% compared to last quarter',
      'Cash flow is stable with positive trend',
      'Consider diversifying investment portfolio to reduce market risk',
      'Operational efficiency can be improved by 12%',
    ],
  });

  if (!analysisData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="card max-w-md text-center">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Data</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <p className="text-sm text-gray-500 mb-4">Using sample data instead</p>
          <button onClick={() => navigate('/upload')} className="btn-primary">
            Back to Upload
          </button>
        </div>
      </div>
    );
  }

  const getRiskColor = (score) => {
    if (score >= 75) return 'text-red-600 bg-red-100';
    if (score >= 50) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  const getRiskLevel = (score) => {
    if (score >= 75) return 'High Risk';
    if (score >= 50) return 'Medium Risk';
    return 'Low Risk';
  };

  // Ensure data has required properties
  const safeAnalysisData = {
    riskScore: analysisData?.riskScore || 72,
    fileName: analysisData?.fileName || 'Document',
    uploadDate: analysisData?.uploadDate || new Date().toLocaleDateString(),
    metrics: analysisData?.metrics || { revenue: '$0', expenses: '$0', profit: '$0', profitMargin: '0%' },
    riskFactors: analysisData?.riskFactors || [
      { name: 'Liquidity Risk', level: 'Medium', score: 65 },
      { name: 'Credit Risk', level: 'Low', score: 35 },
      { name: 'Market Risk', level: 'High', score: 85 },
      { name: 'Operational Risk', level: 'Low', score: 40 },
    ],
    insights: analysisData?.insights || ['Loading insights...'],
  };

  // Chart data
  const lineChartData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Revenue',
        data: [1.8, 2.0, 2.2, 2.3, 2.4, 2.5],
        borderColor: 'rgb(79, 70, 229)',
        backgroundColor: 'rgba(79, 70, 229, 0.1)',
        tension: 0.3,
      },
      {
        label: 'Expenses',
        data: [1.5, 1.6, 1.65, 1.7, 1.75, 1.8],
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.3,
      },
    ],
  };

  const barChartData = {
    labels: (safeAnalysisData?.riskFactors || []).map((f) => f.name),
    datasets: [
      {
        label: 'Risk Score',
        data: (safeAnalysisData?.riskFactors || []).map((f) => f.score),
        backgroundColor: (safeAnalysisData?.riskFactors || []).map((f) => {
          if (f.score >= 75) return 'rgba(239, 68, 68, 0.7)';
          if (f.score >= 50) return 'rgba(245, 158, 11, 0.7)';
          return 'rgba(16, 185, 129, 0.7)';
        }),
      },
    ],
  };

  const doughnutData = {
    labels: ['Low Risk', 'Medium Risk', 'High Risk'],
    datasets: [
      {
        data: [30, 50, 20],
        backgroundColor: [
          'rgba(16, 185, 129, 0.7)',
          'rgba(245, 158, 11, 0.7)',
          'rgba(239, 68, 68, 0.7)',
        ],
        borderWidth: 2,
      },
    ],
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50 py-10 px-4 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float delay-200"></div>
      </div>

      <div className="relative max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-10 animate-fadeInUp">
          <div className="flex items-center space-x-4 mb-4">
            <div className="inline-flex items-center justify-center h-14 w-14 bg-gradient-to-r from-indigo-600 to-cyan-600 rounded-xl shadow-lg">
              <span className="text-2xl">📊</span>
            </div>
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-700 to-cyan-600 bg-clip-text text-transparent">
                Analysis Dashboard
              </h1>
              <p className="text-gray-600 mt-1">
                📄 {safeAnalysisData.fileName} • 📅 {safeAnalysisData.uploadDate}
              </p>
            </div>
          </div>
        </div>

        {/* Risk Score Meter Card */}
        <div className="bg-white/80 backdrop-blur-xl rounded-2xl shadow-xl p-10 mb-10 border border-white/20 animate-fadeInUp delay-100">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 flex items-center">
            <span className="text-3xl mr-3">⚠️</span> Overall Risk Assessment
          </h2>
          <div className="flex flex-col lg:flex-row items-center justify-between gap-10">
            {/* Score Circle */}
            <div className="flex items-center justify-center">
              <div className="relative w-72 h-72">
                <svg className="transform -rotate-90 w-72 h-72 drop-shadow-lg">
                  <circle cx="144" cy="144" r="120" stroke="#e5e7eb" strokeWidth="20" fill="none" />
                  <circle
                    cx="144"
                    cy="144"
                    r="120"
                    stroke={
                      safeAnalysisData.riskScore >= 75
                        ? '#ef4444'
                        : safeAnalysisData.riskScore >= 50
                        ? '#f59e0b'
                        : '#10b981'
                    }
                    strokeWidth="20"
                    fill="none"
                    strokeDasharray={`${(safeAnalysisData.riskScore / 100) * 753.98} 753.98`}
                    strokeLinecap="round"
                    className="transition-all duration-1000"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-6xl font-bold text-transparent bg-gradient-to-r from-indigo-700 to-cyan-600 bg-clip-text">
                    {safeAnalysisData.riskScore}
                  </span>
                  <span className="text-lg text-gray-600">/ 100</span>
                  <span
                    className={`mt-4 px-4 py-2 rounded-full text-sm font-bold ${getRiskColor(
                      safeAnalysisData.riskScore
                    )}`}
                  >
                    {getRiskLevel(safeAnalysisData.riskScore)}
                  </span>
                </div>
              </div>
            </div>

            {/* Risk Summary */}
            <div className="flex-1 space-y-6">
              <div className="p-6 bg-gradient-to-br from-indigo-50 to-cyan-50 rounded-xl border border-indigo-200 hover:shadow-lg transition-all">
                <p className="text-sm text-gray-600 mb-1">Risk Level</p>
                <p className="text-2xl font-bold text-indigo-700">{getRiskLevel(safeAnalysisData.riskScore)}</p>
              </div>
              <div className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200 hover:shadow-lg transition-all">
                <p className="text-sm text-gray-600 mb-1">Assessment Date</p>
                <p className="text-2xl font-bold text-blue-700">{safeAnalysisData.uploadDate}</p>
              </div>
              <div className="p-6 bg-gradient-to-br from-cyan-50 to-teal-50 rounded-xl border border-cyan-200 hover:shadow-lg transition-all">
                <p className="text-sm text-gray-600 mb-1">Status</p>
                <p className="text-2xl font-bold text-cyan-700">✓ Analyzed</p>
              </div>
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10 animate-fadeInUp delay-200">
          {[
            { label: 'Revenue', value: safeAnalysisData.metrics.revenue, icon: '💰', color: 'from-indigo-600 to-indigo-700' },
            { label: 'Expenses', value: safeAnalysisData.metrics.expenses, icon: '📉', color: 'from-orange-600 to-orange-700' },
            { label: 'Profit', value: safeAnalysisData.metrics.profit, icon: '📈', color: 'from-green-600 to-green-700' },
            { label: 'Profit Margin', value: safeAnalysisData.metrics.profitMargin, icon: '📊', color: 'from-cyan-600 to-cyan-700' },
          ].map((metric, idx) => (
            <div
              key={idx}
              className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-6 border border-white/20 hover:shadow-xl transition-all group"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-gray-600">{metric.label}</span>
                <div className={`w-10 h-10 bg-gradient-to-r ${metric.color} rounded-lg flex items-center justify-center text-lg group-hover:scale-110 transition-transform`}>
                  {metric.icon}
                </div>
              </div>
              <p className="text-3xl font-bold text-gray-900">{metric.value}</p>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10 animate-fadeInUp delay-300">
          <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20">
            <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <span className="text-2xl mr-2">📈</span> Revenue vs Expenses Trend
            </h3>
            <Line data={lineChartData} options={{ responsive: true, maintainAspectRatio: true }} />
          </div>
          <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20">
            <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <span className="text-2xl mr-2">⚠️</span> Risk Factor Analysis
            </h3>
            <Bar data={barChartData} options={{ responsive: true, maintainAspectRatio: true }} />
          </div>
        </div>

        {/* Risk Factors and Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10 animate-fadeInUp delay-400">
          <div className="lg:col-span-2 bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20">
            <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <span className="text-2xl mr-2">🔍</span> Detailed Risk Factors
            </h3>
            <div className="space-y-5">
              {safeAnalysisData.riskFactors.map((factor, index) => (
                <div key={index} className="p-5 bg-gradient-to-r from-gray-50 to-blue-50 rounded-xl border border-gray-200 hover:border-indigo-300 hover:shadow-md transition-all">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-bold text-gray-900">{factor.name}</span>
                    <span className={`text-sm font-bold px-3 py-1 rounded-full ${getRiskColor(factor.score)}`}>
                      {factor.level}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-3 rounded-full transition-all duration-500 ${
                        factor.score >= 75
                          ? 'bg-red-500'
                          : factor.score >= 50
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                      }`}
                      style={{ width: `${factor.score}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between mt-2">
                    <span className="text-xs text-gray-500">Score: {factor.score}/100</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20">
            <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <span className="text-2xl mr-2">📊</span> Risk Distribution
            </h3>
            <Doughnut
              data={doughnutData}
              options={{ responsive: true, maintainAspectRatio: true }}
            />
          </div>
        </div>

        {/* AI Insights */}
        <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 animate-fadeInUp delay-500">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <span className="text-2xl mr-2">💡</span> AI-Powered Insights
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {safeAnalysisData.insights.map((insight, index) => (
              <div key={index} className="p-5 bg-gradient-to-br from-indigo-50 to-cyan-50 rounded-lg border border-indigo-200 hover:border-indigo-400 hover:shadow-md transition-all flex items-start space-x-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-r from-indigo-600 to-cyan-600 flex items-center justify-center text-white text-sm font-bold">
                  ✓
                </div>
                <span className="text-gray-700 text-sm leading-relaxed">{insight}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
