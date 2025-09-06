import React from 'react';
import Header from './Header';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
  onNavigate: (page: string) => void;
  currentPage: string;
}

const Layout: React.FC<LayoutProps> = ({ children, onNavigate, currentPage }) => {
  return (
    <div className="app-layout">
      <Header onNavigate={onNavigate} currentPage={currentPage} />
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

export default Layout;