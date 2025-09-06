import React, { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import AuthPage from './components/auth/AuthPage';
import Layout from './components/layout/Layout';
import Dashboard from './components/dashboard/Dashboard';
import UserProfile from './components/profile/UserProfile';
import RecommendationsList from './components/recommendations/RecommendationsList';
import ApplicationTracker from './components/recommendations/ApplicationTracker';
import { PublicVeteranSearch } from './components/public';
import ProtectedRoute from './components/common/ProtectedRoute';
import './config/amplify';
import './App.css';

const AppContent: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();
  const [currentPage, setCurrentPage] = useState('dashboard');

  const handleNavigate = (page: string) => {
    setCurrentPage(page);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'user-profile':
        return <UserProfile />;
      case 'questionnaire':
        return (
          <ProtectedRoute allowedRoles={['veteran']}>
            <div className="page-placeholder">
              <h2>AI問診システム</h2>
              <p>この機能は次のタスクで実装されます。</p>
            </div>
          </ProtectedRoute>
        );
      case 'profile':
        return (
          <ProtectedRoute allowedRoles={['veteran']}>
            <div className="page-placeholder">
              <h2>プロフィール管理</h2>
              <p>この機能は次のタスクで実装されます。</p>
            </div>
          </ProtectedRoute>
        );
      case 'recommendations':
        return (
          <ProtectedRoute allowedRoles={['veteran']}>
            <RecommendationsList />
          </ProtectedRoute>
        );
      case 'applications':
        return (
          <ProtectedRoute allowedRoles={['veteran']}>
            <ApplicationTracker />
          </ProtectedRoute>
        );
      case 'public-search':
        return (
          <ProtectedRoute allowedRoles={['external_recruiter']}>
            <PublicVeteranSearch />
          </ProtectedRoute>
        );
      case 'admin':
        return (
          <ProtectedRoute allowedRoles={['admin']}>
            <div className="page-placeholder">
              <h2>管理画面</h2>
              <p>この機能は次のタスクで実装されます。</p>
            </div>
          </ProtectedRoute>
        );
      default:
        return <Dashboard onNavigate={handleNavigate} />;
    }
  };

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>読み込み中...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthPage />;
  }

  return (
    <Layout onNavigate={handleNavigate} currentPage={currentPage}>
      {renderPage()}
    </Layout>
  );
};

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <AppContent />
      </div>
    </AuthProvider>
  );
}

export default App;