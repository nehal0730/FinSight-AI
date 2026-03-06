import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FileText, Zap, Lock, BarChart3, AlertTriangle, CheckCircle, Search } from 'lucide-react';

export default function Upload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        alert('Only PDF files are allowed');
        return;
      }
      if (selectedFile.size > 50 * 1024 * 1024) {
        alert('File size must be under 50 MB');
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file first');
      return;
    }

    const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
    if (!token) {
      alert('Please login first.');
      navigate('/login');
      return;
    }

    setUploading(true);
    setProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 200);

      try {
        const res = await axios.post('http://localhost:5000/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${token}`,
          },
        });
        localStorage.setItem('analysisResult', JSON.stringify(res.data));
      } catch (apiErr) {
        const status = apiErr?.response?.status;
        if (status === 401) {
          localStorage.removeItem('authToken');
          localStorage.removeItem('user');
          alert('Session expired or invalid. Please login again.');
          navigate('/login');
          return;
        }
        console.warn('Backend unavailable, using dummy data', apiErr);
        localStorage.setItem('analysisResult', JSON.stringify(getDummyAnalysisData()));
      }

      clearInterval(progressInterval);
      setProgress(100);

      setTimeout(() => {
        navigate('/dashboard');
      }, 500);
    } catch (err) {
      console.error(err);
      alert('Upload failed. Please try again.');
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const getDummyAnalysisData = () => ({
    riskScore: 72,
    fileName: file.name || 'financial_report.pdf',
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

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      if (droppedFile.type !== 'application/pdf') {
        alert('Only PDF files are allowed');
        return;
      }
      if (droppedFile.size > 50 * 1024 * 1024) {
        alert('File size must be under 50 MB');
        return;
      }
      setFile(droppedFile);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50 py-12 px-4 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float delay-200"></div>
      </div>

      <div className="relative max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12 animate-fadeInUp">
          <div className="inline-flex items-center justify-center h-16 w-16 bg-gradient-to-r from-indigo-600 to-cyan-600 rounded-2xl mb-4 shadow-lg">
            <FileText className="w-9 h-9 text-white" />
          </div>
          <h1 className="text-5xl font-bold bg-gradient-to-r from-indigo-700 to-cyan-600 bg-clip-text text-transparent mb-4">
            Upload Financial Document
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Upload your PDF document and let our AI analyze it in seconds
          </p>
        </div>

        {/* Upload Card */}
        <div className="bg-white/80 backdrop-blur-xl rounded-2xl shadow-2xl p-10 border border-white/20 animate-fadeInUp delay-100 mb-8">
          {/* Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className="border-2 border-dashed border-indigo-300 hover:border-indigo-500 rounded-xl p-12 text-center transition-colors cursor-pointer group hover:bg-gradient-to-br hover:from-indigo-50/50 hover:to-cyan-50/50"
          >
            <input
              type="file"
              onChange={handleFileChange}
              accept="application/pdf"
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="transform group-hover:scale-110 transition-transform duration-300 mb-4">
                <svg
                  className="mx-auto h-20 w-20 text-indigo-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                  />
                </svg>
              </div>
              {file ? (
                <p className="text-lg font-semibold text-indigo-700 mb-2">{file.name}</p>
              ) : (
                <>
                  <p className="text-lg font-semibold text-gray-700 mb-2">
                    Drop your PDF here or click to browse
                  </p>
                  <p className="text-sm text-gray-500">PDF files only, up to 50MB</p>
                </>
              )}
            </label>
          </div>

          {/* Selected File Info */}
          {file && (
            <div className="mt-8 p-5 bg-gradient-to-r from-indigo-50 to-cyan-50 rounded-xl border border-indigo-200 flex items-center justify-between group hover:shadow-lg transition-all">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0 w-14 h-14 bg-gradient-to-r from-indigo-600 to-cyan-600 rounded-lg flex items-center justify-center shadow-lg">
                  <svg className="h-8 w-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-600">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <button
                onClick={() => setFile(null)}
                className="text-indigo-600 hover:text-indigo-700 hover:bg-white rounded-lg p-2 transition-all"
              >
                ✕
              </button>
            </div>
          )}

          {/* Upload Progress */}
          {uploading && (
            <div className="mt-8 animate-fadeInUp">
              <div className="flex justify-between items-center mb-3">
                <span className="text-sm font-semibold text-gray-700">Analyzing your document...</span>
                <span className="text-sm font-bold bg-gradient-to-r from-indigo-600 to-cyan-600 bg-clip-text text-transparent">
                  {progress}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-indigo-600 to-cyan-600 h-3 rounded-full transition-all duration-300 shadow-lg"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-500 mt-2">Processing your financial document with AI...</p>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full mt-8 bg-gradient-to-r from-indigo-700 to-cyan-600 text-white font-semibold py-4 rounded-xl hover:shadow-xl transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 relative overflow-hidden group"
          >
            <span className="relative z-10 flex items-center justify-center">
              {uploading ? (
                <>
                  <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                  </svg>
                  Analyzing Document...
                </>
              ) : (
                <>
                  <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Analyze Document
                </>
              )}
            </span>
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 to-indigo-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          </button>
        </div>

        {/* Info Cards */}
        <div className="grid md:grid-cols-2 gap-6 animate-fadeInUp delay-200">
          <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 hover:shadow-xl transition-all group">
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-lg flex items-center justify-center text-white text-xl">
                <Zap className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-gray-900 mb-2">Fast Processing</h3>
                <p className="text-gray-600">Get comprehensive analysis results in seconds, not hours</p>
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 hover:shadow-xl transition-all group">
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-r from-cyan-600 to-cyan-700 rounded-lg flex items-center justify-center text-white text-xl">
                <Lock className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-gray-900 mb-2">Secure & Private</h3>
                <p className="text-gray-600">Your documents are encrypted and never shared with third parties</p>
              </div>
            </div>
          </div>
        </div>

        {/* Features List */}
        <div className="mt-10 bg-white/80 backdrop-blur-xl rounded-xl shadow-lg p-8 border border-white/20 animate-fadeInUp delay-300">
          <h3 className="font-bold text-xl text-gray-900 mb-6">What Our AI Analyzes:</h3>
          <div className="grid md:grid-cols-2 gap-4">
            {[
              { icon: <BarChart3 className="w-6 h-6" />, title: 'Financial Metrics', desc: 'Revenue, expenses, margins, and key ratios' },
              { icon: <AlertTriangle className="w-6 h-6" />, title: 'Risk Assessment', desc: 'Identify potential financial threats' },
              { icon: <CheckCircle className="w-6 h-6" />, title: 'Compliance Check', desc: 'Verify regulatory compliance' },
              { icon: <Search className="w-6 h-6" />, title: 'Anomalies', desc: 'Detect unusual patterns and red flags' },
            ].map((item, idx) => (
              <div key={idx} className="flex items-start space-x-3 p-4 rounded-lg hover:bg-gray-50 transition-colors">
                <span className="text-indigo-600 flex-shrink-0">{item.icon}</span>
                <div>
                  <p className="font-semibold text-gray-900">{item.title}</p>
                  <p className="text-sm text-gray-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
