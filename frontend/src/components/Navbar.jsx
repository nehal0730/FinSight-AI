import { Link, useLocation } from 'react-router-dom';
import { Sparkles, LogOut, User } from 'lucide-react';

export default function Navbar() {
  const location = useLocation();
  const userRaw = localStorage.getItem('user') || sessionStorage.getItem('user');
  let userName = '';
  try {
    const parsedUser = userRaw ? JSON.parse(userRaw) : null;
    userName = parsedUser?.name || userRaw || '';
  } catch {
    userName = userRaw || '';
  }
  const isLoggedIn = Boolean(localStorage.getItem('authToken') || sessionStorage.getItem('authToken'));
  
  const isActive = (path) => location.pathname === path;
  
  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('authToken');
    sessionStorage.removeItem('user');
    sessionStorage.removeItem('authToken');
    window.location.href = '/login';
  };

  // Don't show navbar on login/signup pages
  if (location.pathname === '/login' || location.pathname === '/signup') {
    return null;
  }

  return (
    <nav className="bg-white/80 backdrop-blur-xl shadow-lg border-b border-white/20 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link to="/" className="flex items-center gap-2 group cursor-pointer">
              <div className="h-9 w-9 bg-gradient-to-r from-indigo-600 to-cyan-600 rounded-lg flex items-center justify-center shadow-md group-hover:scale-110 transition-transform">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-indigo-700 to-cyan-600 bg-clip-text text-transparent">
                FinSight AI
              </span>
            </Link>
            
            {isLoggedIn && (
              <div className="hidden md:flex space-x-1">
                {[
                  { to: '/upload', label: 'Upload' },
                  { to: '/dashboard', label: 'Dashboard' },
                  { to: '/chat', label: 'Chat' },
                  { to: '/reports', label: 'Reports' },
                ].map(({ to, label }) => (
                  <Link
                    key={to}
                    to={to}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer ${
                      isActive(to)
                        ? 'bg-gradient-to-r from-indigo-600 to-cyan-600 text-white shadow-md'
                        : 'text-gray-600 hover:text-indigo-700 hover:bg-indigo-50'
                    }`}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-4">
            {isLoggedIn ? (
              <>
                <span className="text-sm text-gray-600 flex items-center gap-1.5">
                  <User className="w-4 h-4" /> {userName}
                </span>
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-red-600 hover:bg-red-50 transition-all cursor-pointer"
                >
                  <LogOut className="w-4 h-4" /> Logout
                </button>
              </>
            ) : (
              <Link to="/login" className="btn-primary text-sm cursor-pointer">
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
