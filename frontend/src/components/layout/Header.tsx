import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import RoleBasedComponent from '../common/RoleBasedComponent';
import { termMappingService } from '../../services/termMappingService';
import './Header.css';

interface HeaderProps {
  onNavigate: (page: string) => void;
  currentPage: string;
}

const Header: React.FC<HeaderProps> = ({ onNavigate, currentPage }) => {
  const { user, logout, isAuthenticated } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      setShowUserMenu(false);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  if (!isAuthenticated || !user) {
    return null;
  }

  const navigationItems = [
    {
      key: 'dashboard',
      label: 'ダッシュボード',
      roles: ['veteran', 'admin', 'external_recruiter'] as const,
    },
    {
      key: 'questionnaire',
      label: termMappingService.getLocalizedTerm('navigation_questionnaire'),
      roles: ['veteran'] as const,
    },
    {
      key: 'profile',
      label: termMappingService.getLocalizedTerm('navigation_profile'),
      roles: ['veteran'] as const,
    },
    {
      key: 'recommendations',
      label: termMappingService.getLocalizedTerm('navigation_recommendations'),
      roles: ['veteran'] as const,
    },
    {
      key: 'applications',
      label: termMappingService.getLocalizedTerm('navigation_applications'),
      roles: ['veteran'] as const,
    },
    {
      key: 'public-search',
      label: termMappingService.getLocalizedTerm('talent_search'),
      roles: ['external_recruiter'] as const,
    },
    {
      key: 'admin',
      label: '管理',
      roles: ['admin'] as const,
    },
  ];

  return (
    <header className="app-header">
      <div className="header-content">
        <div className="header-left">
          <div className="app-brand" onClick={() => onNavigate('dashboard')}>
            <img src="/logo.png" alt="製造業プラチナアドバイザリー" className="app-logo" />
            <h1 className="app-title">
              {termMappingService.getLocalizedTerm('app_title')}
            </h1>
          </div>
        </div>

        <nav className="header-nav">
          {navigationItems.map((item) => (
            <RoleBasedComponent key={item.key} allowedRoles={item.roles}>
              <button
                className={`nav-item ${currentPage === item.key ? 'active' : ''}`}
                onClick={() => onNavigate(item.key)}
              >
                {item.label}
              </button>
            </RoleBasedComponent>
          ))}
        </nav>

        <div className="header-right">
          <div className="user-menu">
            <button
              className="user-menu-trigger"
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              <span className="user-name">{user.name}</span>
              <span className="user-role">
                {user.role === 'admin' ? '管理者' : 
                 user.role === 'external_recruiter' ? '外部リクルーター' : termMappingService.getLocalizedTerm('navigation_talent')}
              </span>
              <span className="dropdown-arrow">▼</span>
            </button>

            {showUserMenu && (
              <div className="user-menu-dropdown">
                <button
                  className="menu-item"
                  onClick={() => {
                    onNavigate('user-profile');
                    setShowUserMenu(false);
                  }}
                >
                  ユーザー設定
                </button>
                <button
                  className="menu-item logout"
                  onClick={handleLogout}
                >
                  ログアウト
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;