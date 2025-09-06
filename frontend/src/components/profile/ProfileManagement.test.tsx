import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProfileManagement from './ProfileManagement';
// Mock the useAuth hook
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      user_id: 'test-user-id',
      name: 'Test User',
      email: 'test@example.com',
      role: 'veteran' as const,
      department: 'Test Department',
      employee_id: 'EMP001',
      join_date: '2020-01-01',
      is_active: true,
      created_at: '2020-01-01T00:00:00Z',
      updated_at: '2020-01-01T00:00:00Z',
    },
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
    isAuthenticated: true,
    error: null,
    signUp: jest.fn(),
    updateProfile: jest.fn(),
    refreshUser: jest.fn(),
  }),
}));

// Mock the profile service
jest.mock('../../services/profileService', () => ({
  profileService: {
    getProfile: jest.fn().mockResolvedValue(null),
    updateProfile: jest.fn(),
    updatePrivacySettings: jest.fn(),
    generateBusinessTitle: jest.fn(),
  },
}));

describe('ProfileManagement Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders profile management header', () => {
    render(<ProfileManagement />);

    expect(screen.getByText('プロフィール管理')).toBeInTheDocument();
    expect(screen.getByText('あなたの詳細プロフィールを編集・管理できます')).toBeInTheDocument();
  });

  test('renders profile tabs', () => {
    render(<ProfileManagement />);

    expect(screen.getByText('スキル')).toBeInTheDocument();
    expect(screen.getByText('経験')).toBeInTheDocument();
    expect(screen.getByText('希望・設定')).toBeInTheDocument();
    expect(screen.getByText('ビジネスタイトル')).toBeInTheDocument();
    expect(screen.getByText('プライバシー設定')).toBeInTheDocument();
  });

  test('renders loading state initially', () => {
    render(<ProfileManagement />);

    expect(screen.getByText('プロフィールを読み込み中...')).toBeInTheDocument();
  });
});