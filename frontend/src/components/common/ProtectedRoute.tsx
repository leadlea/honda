import React from 'react';
import { useAuth } from '../../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: ReadonlyArray<'veteran' | 'admin' | 'external_recruiter'>;
  fallback?: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles = ['veteran', 'admin', 'external_recruiter'],
  fallback = <div className="access-denied">アクセスが拒否されました</div>,
}) => {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="loading">読み込み中...</div>;
  }

  if (!isAuthenticated || !user) {
    return <div className="auth-required">ログインが必要です</div>;
  }

  if (!allowedRoles.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

export default ProtectedRoute;