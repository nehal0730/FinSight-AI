import { Link } from 'react-router-dom';
import { Rocket, Bot, Shield, MessageCircle, BarChart3, FileText, Search, Sparkles } from 'lucide-react';
import { getRiskHistory } from '../utils/riskStorage';
import { useState, useEffect } from 'react';

export default function Home() {
  const [docCount, setDocCount] = useState(0);
  const [avgAccuracy, setAvgAccuracy] = useState(99);

  useEffect(() => {
    getRiskHistory().then(history => {
      setDocCount(history.length);
      if (history.length > 0) {
        setAvgAccuracy(
          Math.round(history.reduce((s, r) => s + (100 - Number(r?.riskResponse?.risk_score || 0)), 0) / history.length)
        );
      }
    });
  }, []);

  const features = [
    {
      title: 'AI-Powered Analysis',
      description: 'Advanced machine learning algorithms analyze your financial documents in seconds',
      icon: <Bot className="w-6 h-6 text-white" />,
      gradient: 'from-indigo-600 to-indigo-700',
    },
    {
      title: 'Risk Assessment',
      description: 'Comprehensive risk scoring and identification of potential financial threats',
      icon: <Shield className="w-6 h-6 text-white" />,
      gradient: 'from-cyan-600 to-teal-700',
    },
    {
      title: 'Real-time Chat',
      description: 'Ask questions and get instant insights from your AI financial assistant',
      icon: <MessageCircle className="w-6 h-6 text-white" />,
      gradient: 'from-indigo-700 to-cyan-600',
    },
    {
      title: 'Visual Reports',
      description: 'Beautiful charts and dashboards to visualize your financial data',
      icon: <BarChart3 className="w-6 h-6 text-white" />,
      gradient: 'from-slate-700 to-indigo-600',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50 overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-teal-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float delay-200"></div>
        <div className="absolute top-1/2 left-1/2 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float delay-400"></div>
      </div>

      {/* Hero Section */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16">
        <div className="text-center animate-fadeInUp">
          <div className="inline-block mb-4">
            <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800 animate-pulse-glow">
              <Rocket className="w-4 h-4 mr-2" /> Transform Your Financial Analysis
            </span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-extrabold text-gray-900 mb-6 leading-tight">
            Welcome to{' '}
            <span className="bg-gradient-to-r from-indigo-700 via-indigo-600 to-cyan-600 bg-clip-text text-transparent animate-gradient">
              FinSight AI
            </span>
          </h1>
          
          <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed animate-fadeInUp delay-200">
            Harness the power of artificial intelligence to analyze financial documents, 
            assess risks, and unlock actionable insights—all in seconds.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12 animate-fadeInUp delay-300">
            <Link 
              to="/signup" 
              className="group relative inline-flex items-center justify-center px-8 py-4 text-lg font-semibold text-white bg-gradient-to-r from-indigo-700 to-cyan-600 rounded-xl overflow-hidden transition-all duration-300 hover:scale-105 hover:shadow-2xl cursor-pointer"
            >
              <span className="relative z-10 flex items-center">
                Get Started Free
                <svg className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 to-indigo-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            </Link>
            
            <Link 
              to="/login" 
              className="inline-flex items-center justify-center px-8 py-4 text-lg font-semibold text-indigo-700 bg-white rounded-xl border-2 border-indigo-700 hover:bg-indigo-50 transition-all duration-300 hover:scale-105 hover:shadow-lg cursor-pointer"
            >
              Sign In
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto animate-fadeInUp delay-400">
            <div className="transition-transform hover:scale-110 duration-300">
              <div className="text-3xl font-bold text-indigo-600">{docCount > 0 ? `${docCount}` : '0'}</div>
              <div className="text-sm text-gray-600">Documents Analyzed</div>
            </div>
            <div className="transition-transform hover:scale-110 duration-300">
              <div className="text-3xl font-bold text-indigo-600">{avgAccuracy}%</div>
              <div className="text-sm text-gray-600">Accuracy Rate</div>
            </div>
            <div className="transition-transform hover:scale-110 duration-300">
              <div className="text-3xl font-bold text-indigo-600">24/7</div>
              <div className="text-sm text-gray-600">AI Assistance</div>
            </div>
          </div>
        </div>

        {/* Demo Image with animation */}
        <div className="mt-16 animate-fadeInUp delay-500">
          <div className="relative rounded-2xl shadow-2xl overflow-hidden border-4 border-white backdrop-blur-sm group">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-700 via-indigo-600 to-cyan-600 animate-gradient"></div>
            <div className="relative h-96 flex items-center justify-center bg-gradient-to-br from-indigo-700/95 to-cyan-600/95">
              <div className="text-center text-white">
                <svg className="h-24 w-24 mx-auto mb-4 opacity-75 animate-float" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
                <p className="text-2xl font-semibold opacity-90">Interactive Dashboard Preview</p>
                <p className="text-sm opacity-75 mt-2">Real-time analytics and insights</p>
              </div>
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="relative bg-white/50 backdrop-blur-sm py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fadeInUp">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">Powerful Features</h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Everything you need to analyze and understand your financial documents
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div 
                key={index} 
                className="group relative bg-white rounded-2xl shadow-lg p-8 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2 animate-fadeInUp border border-gray-100"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className={`h-14 w-14 bg-gradient-to-r ${feature.gradient} rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg`}>
                  {feature.icon}
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3 group-hover:text-indigo-600 transition-colors">
                  {feature.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">{feature.description}</p>
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-600 to-cyan-600 rounded-b-2xl transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="relative py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fadeInUp">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">How It Works</h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Get started in three simple steps
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {[
              { step: '1', title: 'Upload Document', desc: 'Simply upload your financial PDF document to our secure platform', icon: <FileText className="w-10 h-10 text-indigo-600" /> },
              { step: '2', title: 'AI Analysis', desc: 'Our AI analyzes your document and generates comprehensive insights', icon: <Search className="w-10 h-10 text-indigo-600" /> },
              { step: '3', title: 'Get Insights', desc: 'View your dashboard, chat with AI, and download detailed reports', icon: <Sparkles className="w-10 h-10 text-indigo-600" /> },
            ].map((item, index) => (
              <div key={index} className="text-center animate-fadeInUp" style={{ animationDelay: `${index * 0.2}s` }}>
                <div className="relative mb-6">
                  <div className="h-20 w-20 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-full flex items-center justify-center text-4xl font-bold mx-auto shadow-xl animate-pulse-glow">
                    {item.step}
                  </div>
                  <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2">
                    {item.icon}
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3 mt-8">{item.title}</h3>
                <p className="text-gray-600 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="relative bg-gradient-to-r from-slate-900 via-indigo-900 to-slate-900 py-20 animate-gradient">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative max-w-4xl mx-auto text-center px-4">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6 animate-fadeInUp">
            Ready to Transform Your Financial Analysis?
          </h2>
          <p className="text-xl text-white/90 mb-10 animate-fadeInUp delay-200">
            Join thousands of users who trust FinSight AI for their financial document analysis
          </p>
          <Link 
            to="/signup" 
            className="inline-flex items-center px-10 py-5 text-lg font-bold text-indigo-600 bg-white rounded-xl hover:bg-gray-100 transition-all duration-300 hover:scale-105 shadow-2xl animate-fadeInUp delay-300 cursor-pointer"
          >
            <span>Start Free Trial</span>
            <svg className="w-6 h-6 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
        </div>
      </div>
    </div>
  );
}
