import React, { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import AuthPage from './components/auth/AuthPage';
import Layout from './components/layout/Layout';
import Dashboard from './components/dashboard/Dashboard';
import UserProfile from './components/profile/UserProfile';
import ProfileManagement from './components/profile/ProfileManagement';
import RecommendationsList from './components/recommendations/RecommendationsList';
import ApplicationTracker from './components/recommendations/ApplicationTracker';
import PublicVeteranSearch from './components/public/PublicVeteranSearch';
import ProtectedRoute from './components/common/ProtectedRoute';
import Verified from './components/Verified';
import Questionnaire from './components/questionnaire/Questionnaire'; // ← 追加
import './config/amplify';
import './App.css';

const AppContent: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();
  const [currentPage, setCurrentPage] = useState('dashboard');

  // URLのパスで /verified をハンドリング（Routerなし運用）
  const pathname =
    typeof window !== 'undefined'
      ? window.location.pathname.replace(/\/+$/, '')
      : '';

  if (pathname === '/verified') {
    return <Verified />; // 認証状態に関係なく表示
  }

  const handleNavigate = (page: string) => {
    setCurrentPage(page);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'user-profile':
        return (
          <ProtectedRoute allowedRoles={['veteran']}>
            <UserProfile />
          </ProtectedRoute>
        );

      case 'profile': // ← プロフィール管理（スキル、経験、ビジネスタイトルなど）
        return (
          <ProtectedRoute allowedRoles={['veteran']}>
            <ProfileManagement />
          </ProtectedRoute>
        );

      case 'questionnaire': // ← プレースホルダーを本実装に差し替え
        return (
          <ProtectedRoute allowedRoles={['veteran']}>
            <Questionnaire />
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
    return <AuthPage />; // 通常ログイン/新規登録画面
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
