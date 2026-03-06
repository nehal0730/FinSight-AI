import { useState } from 'react';
import { FileText, AlertTriangle, Calendar, BarChart3, CheckCircle, Download, ClipboardList } from 'lucide-react';

export default function Reports() {
  const [selectedReport, setSelectedReport] = useState(null);

  const reports = [
    {
      id: 1,
      name: 'Q4 2024 Financial Analysis',
      date: '2024-12-15',
      type: 'Quarterly Report',
      riskScore: 72,
      status: 'Completed',
      fileName: 'q4_2024_report.pdf',
    },
    {
      id: 2,
      name: 'Annual Risk Assessment 2024',
      date: '2024-11-20',
      type: 'Annual Report',
      riskScore: 68,
      status: 'Completed',
      fileName: 'annual_2024.pdf',
    },
    {
      id: 3,
      name: 'Q3 2024 Financial Analysis',
      date: '2024-09-15',
      type: 'Quarterly Report',
      riskScore: 75,
      status: 'Completed',
      fileName: 'q3_2024_report.pdf',
    },
    {
      id: 4,
      name: 'Mid-Year Review 2024',
      date: '2024-06-30',
      type: 'Semi-Annual Report',
      riskScore: 70,
      status: 'Completed',
      fileName: 'midyear_2024.pdf',
    },
  ];

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

  const handleExport = (format) => {
    alert(`Exporting report as ${format}... (This is a demo)`);
  };

  const averageRiskScore = Math.round(reports.reduce((sum, r) => sum + r.riskScore, 0) / reports.length);

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
              <ClipboardList className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-700 to-cyan-600 bg-clip-text text-transparent">
                Financial Reports
              </h1>
              <p className="text-gray-600 mt-1">View and manage your analysis reports</p>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10 animate-fadeInUp delay-100">
          <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 hover:shadow-xl transition-all group">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-2 font-semibold">Total Reports</p>
                <p className="text-4xl font-bold text-gray-900">{reports.length}</p>
              </div>
              <div className="h-14 w-14 bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform shadow-lg">
                <FileText className="w-7 h-7 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 hover:shadow-xl transition-all group">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-2 font-semibold">Average Risk</p>
                <p className="text-4xl font-bold text-gray-900">{averageRiskScore}</p>
                <p className="text-xs text-gray-500 mt-1">{getRiskLevel(averageRiskScore)}</p>
              </div>
              <div className="h-14 w-14 bg-gradient-to-r from-yellow-600 to-yellow-700 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform shadow-lg">
                <AlertTriangle className="w-7 h-7 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 hover:shadow-xl transition-all group">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-2 font-semibold">Latest Report</p>
                <p className="text-2xl font-bold text-gray-900">
                  {new Date(reports[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </p>
                <p className="text-xs text-gray-500 mt-1">{new Date(reports[0].date).getFullYear()}</p>
              </div>
              <div className="h-14 w-14 bg-gradient-to-r from-green-600 to-green-700 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform shadow-lg">
                ✓
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fadeInUp delay-200">
          {/* Reports List */}
          <div className="lg:col-span-2 space-y-4">
            {reports.map((report, index) => (
              <div
                key={report.id}
                onClick={() => setSelectedReport(report)}
                className={`bg-white/80 backdrop-blur-xl rounded-xl shadow-lg border-2 transition-all cursor-pointer hover:shadow-xl transform hover:-translate-y-1 ${
                  selectedReport?.id === report.id
                    ? 'border-indigo-500 ring-2 ring-indigo-500/30'
                    : 'border-white/20 hover:border-indigo-300'
                }`}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-4 mb-3">
                        <div className="text-3xl"><ClipboardList className="w-8 h-8 text-indigo-600" /></div>
                        <div className="flex-1">
                          <h3 className="text-lg font-bold text-gray-900">{report.name}</h3>
                          <span className={`inline-block mt-1 px-3 py-1 text-xs font-bold rounded-full ${getRiskColor(report.riskScore)}`}>
                            Risk: {report.riskScore}
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                        <span className="flex items-center">
                          <Calendar className="w-4 h-4 mr-1" /> {new Date(report.date).toLocaleDateString()}
                        </span>
                        <span className="flex items-center">
                          <BarChart3 className="w-4 h-4 mr-1" /> {report.type}
                        </span>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">
                          <CheckCircle className="w-3 h-3 mr-1" /> {report.status}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-2 font-mono">{report.fileName}</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Report Details Sidebar */}
          <div className="lg:col-span-1">
            {selectedReport ? (
              <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 sticky top-4 animate-fadeInUp">
                <div className="flex items-center space-x-3 mb-6 pb-6 border-b border-gray-200">
                  <div className="text-4xl"><ClipboardList className="w-10 h-10 text-indigo-600" /></div>
                  <h3 className="text-2xl font-bold text-gray-900">Details</h3>
                </div>

                <div className="space-y-5">
                  <div>
                    <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Report Name</p>
                    <p className="font-bold text-gray-900 text-lg">{selectedReport.name}</p>
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Date Generated</p>
                    <p className="font-bold text-gray-900">
                      {new Date(selectedReport.date).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Report Type</p>
                    <div className="inline-block px-4 py-2 bg-indigo-100 text-indigo-700 rounded-lg font-semibold text-sm">
                      {selectedReport.type}
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">Risk Assessment</p>
                    <div className="flex items-center space-x-4">
                      <div className="flex-1">
                        <div className="text-4xl font-bold bg-gradient-to-r from-indigo-700 to-cyan-600 bg-clip-text text-transparent">
                          {selectedReport.riskScore}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">out of 100</div>
                      </div>
                      <div className={`px-4 py-2 rounded-lg font-bold text-sm ${getRiskColor(selectedReport.riskScore)}`}>
                        {getRiskLevel(selectedReport.riskScore)}
                      </div>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Status</p>
                    <span className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-bold bg-green-100 text-green-800">
                      <CheckCircle className="w-4 h-4 mr-1" /> {selectedReport.status}
                    </span>
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">File Name</p>
                    <p className="font-mono text-xs bg-gray-100 p-2 rounded-lg text-gray-700 break-all">{selectedReport.fileName}</p>
                  </div>

                  <div className="pt-6 space-y-3 border-t border-gray-200">
                    <button
                      onClick={() => handleExport('PDF')}
                      className="w-full bg-gradient-to-r from-indigo-700 to-cyan-600 text-white font-semibold py-3 rounded-lg hover:shadow-lg transition-all duration-300 hover:scale-105 relative overflow-hidden group flex items-center justify-center cursor-pointer"
                    >
                      <span className="relative z-10 flex items-center">
                        <Download className="w-5 h-5 mr-2" /> Download PDF
                      </span>
                      <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 to-indigo-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                    </button>
                    <button
                      onClick={() => handleExport('Excel')}
                      className="w-full border-2 border-indigo-300 text-indigo-700 font-semibold py-3 rounded-lg hover:bg-indigo-50 transition-all duration-300 hover:scale-105 flex items-center justify-center cursor-pointer"
                    >
                      <BarChart3 className="w-5 h-5 mr-2" /> Export to Excel
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 sticky top-4 text-center">
                <div className="text-6xl mb-4">
                  <ClipboardList className="w-20 h-20 mx-auto text-gray-400" />
                </div>
                <p className="text-gray-600 font-semibold">Select a report to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
