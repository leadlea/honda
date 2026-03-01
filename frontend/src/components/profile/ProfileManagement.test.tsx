import React from 'react';
import { render, screen, act } from '@testing-library/react';
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

const mockProfile = {
  user_id: 'test-user-id',
  skills: [],
  experiences: [],
  preferences: { preferred_roles: [], work_style: 'flexible', locations: [], availability: 'full_time' },
};

const mockGetProfile = jest.fn();
const mockUpdateProfile = jest.fn();

jest.mock('../../services/profileService', () => ({
  profileService: {
    getProfile: (...args: any[]) => mockGetProfile(...args),
    updateProfile: (...args: any[]) => mockUpdateProfile(...args),
  },
}));

describe('ProfileManagement Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetProfile.mockResolvedValue(mockProfile);
    mockUpdateProfile.mockResolvedValue(mockProfile);
  });

  test('renders loading state initially', () => {
    render(<ProfileManagement />);
    expect(screen.getByText(/AIスキルポートフォリオを読み込み中/)).toBeInTheDocument();
  });

  test('renders profile management header after loading', async () => {
    let resolveProfile: (value: any) => void;
    const profilePromise = new Promise((resolve) => {
      resolveProfile = resolve;
    });
    mockGetProfile.mockReturnValue(profilePromise);

    render(<ProfileManagement />);
    expect(screen.getByText(/AIスキルポートフォリオを読み込み中/)).toBeInTheDocument();

    await act(async () => {
      resolveProfile!(mockProfile);
    });

    expect(screen.getByText('AIスキルポートフォリオ管理')).toBeInTheDocument();
    expect(screen.getByText(/あなたのAIスキルポートフォリオを編集・管理できます/)).toBeInTheDocument();
  });

  test('renders profile tabs after loading', async () => {
    let resolveProfile: (value: any) => void;
    const profilePromise = new Promise((resolve) => {
      resolveProfile = resolve;
    });
    mockGetProfile.mockReturnValue(profilePromise);

    render(<ProfileManagement />);

    await act(async () => {
      resolveProfile!(mockProfile);
    });

    expect(screen.getByText('AIスキル')).toBeInTheDocument();
    expect(screen.getByText('経験・実績')).toBeInTheDocument();
    expect(screen.getByText('希望・設定')).toBeInTheDocument();
    expect(screen.getByText('ビジネスタイトル')).toBeInTheDocument();
    expect(screen.getByText('プライバシー設定')).toBeInTheDocument();
  });
});
