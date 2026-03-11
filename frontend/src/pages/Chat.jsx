import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, RefreshCw, Bot, Pin } from 'lucide-react';

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your FinSight AI assistant. I can help you understand your financial documents and answer questions. Please make sure you have uploaded a document first.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch available documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
      if (!token) return;

      const res = await axios.get('http://localhost:5000/query/documents', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.data.success && res.data.data?.documents) {
        const docList = res.data.data.documents;
        setDocuments(docList);
        if (docList.length > 0 && !selectedDoc) {
          setSelectedDoc(docList[0]); // Auto-select first document
        }
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    if (!selectedDoc) {
      alert('Please select a document first or upload one.');
      return;
    }

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
      
      const res = await axios.post(
        'http://localhost:5000/query',
        {
          query: input,
          document_id: selectedDoc,
          top_k: 5
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      const aiResponse = {
        role: 'assistant',
        content: res.data.data.answer || 'No answer found.',
        source: res.data.data.source,
        confidence: res.data.data.confidence,
        citations: res.data.data.citations,
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      const errorResponse = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.error || error.message || 'Failed to get answer. Please try again.'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorResponse]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickQuestions = [
    'Summarize the key points of this document',
    'What are the main financial figures mentioned?',
    'Are there any risk factors discussed?',
    'What recommendations or conclusions are stated?',
  ];

  const handleQuickQuestion = (question) => {
    setInput(question);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50 flex flex-col relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float delay-200"></div>
      </div>

      {/* Header */}
      <div className="bg-white/80 backdrop-blur-xl border-b border-white/20 px-6 py-5 shadow-lg relative z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="inline-flex items-center justify-center h-12 w-12 bg-gradient-to-r from-indigo-600 to-cyan-600 rounded-xl shadow-lg">
              <Send className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-700 to-cyan-600 bg-clip-text text-transparent">
                AI Financial Assistant
              </h1>
              <p className="text-sm text-gray-600">Ask questions about your documents</p>
            </div>
          </div>

          {/* Document Selector */}
          <div className="flex items-center space-x-3">
            <label className="text-sm font-medium text-gray-700">Document:</label>
            <select
              value={selectedDoc || ''}
              onChange={(e) => setSelectedDoc(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white cursor-pointer"
              title={selectedDoc || 'Select a document'}
            >
              {documents.length === 0 ? (
                <option value="">No documents indexed</option>
              ) : (
                documents.map((doc) => (
                  <option key={doc} value={doc} title={doc}>
                    {doc.split('_')[0].substring(0, 30)}...
                  </option>
                ))
              )}
            </select>
            <button
              onClick={fetchDocuments}
              className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors cursor-pointer"
              title="Refresh documents"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col max-w-5xl mx-auto w-full relative z-0">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 py-8 space-y-5">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeInUp`}
            >
                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-4 shadow-lg transition-all hover:shadow-xl ${
                    message.role === 'user'
                      ? 'bg-gradient-to-r from-indigo-700 to-cyan-600 text-white rounded-3xl rounded-tr-lg'
                      : 'bg-white/80 backdrop-blur-xl border border-white/20 text-gray-900 rounded-3xl rounded-tl-lg'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    {message.role === 'assistant' && (
                      <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-indigo-600 to-cyan-600 rounded-full flex items-center justify-center text-white text-sm flex-shrink-0 mt-0.5">
                        <Bot className="w-5 h-5" />
                      </div>
                    )}
                    <div className="flex-1">
                      <p className="whitespace-pre-line leading-relaxed text-sm md:text-base">{message.content}</p>

                      <p
                        className={`text-xs mt-2 ${
                          message.role === 'user' ? 'text-indigo-200' : 'text-gray-500'
                        }`}
                      >
                        {message.timestamp.toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )
          )}

          {isTyping && (
            <div className="flex justify-start animate-fadeInUp">
              <div className="bg-white/80 backdrop-blur-xl border border-white/20 rounded-3xl rounded-tl-lg px-5 py-4 shadow-lg">
                <div className="flex space-x-3">
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce delay-100"></div>
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce delay-200"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Questions */}
        {messages.length <= 1 && (
          <div className="px-6 py-5 bg-white/50 backdrop-blur-sm border-t border-white/20">
            <p className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
              <Pin className="w-4 h-4 mr-2" /> Try asking:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {quickQuestions.map((question, index) => (
                <button
                  key={index}
                  onClick={() => handleQuickQuestion(question)}
                  className="text-left px-4 py-3 bg-white border-2 border-gray-200 rounded-xl hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-md transition-all text-sm font-medium text-gray-700 hover:text-indigo-700 cursor-pointer"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-white/20 bg-white/80 backdrop-blur-xl px-6 py-4 shadow-lg">
          <div className="flex space-x-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about your analysis..."
                className="w-full px-5 py-3 rounded-xl border-2 border-gray-200 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all bg-white/70 placeholder-gray-400 disabled:opacity-50"
                disabled={isTyping}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || isTyping}
              className="bg-gradient-to-r from-indigo-700 to-cyan-600 text-white font-semibold px-6 py-3 rounded-xl hover:shadow-lg transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 relative overflow-hidden group cursor-pointer"
            >
              <span className="relative z-10 flex items-center justify-center">
                {isTyping ? (
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                  </svg>
                ) : (
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                  </svg>
                )}
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 to-indigo-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
