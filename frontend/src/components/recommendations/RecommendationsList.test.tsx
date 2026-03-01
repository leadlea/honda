import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import RecommendationsList from './RecommendationsList';

// Mock the recommendation service
const mockGetRecommendations = jest.fn().mockResolvedValue([]);
jest.mock('../../services/recommendationService', () => ({
  RecommendationService: {
    getRecommendations: (...args: any[]) => mockGetRecommendations(...args),
    markRecommendationAsViewed: jest.fn().mockResolvedValue(undefined),
    dismissRecommendation: jest.fn().mockResolvedValue(undefined),
    applyToOpportunity: jest.fn().mockResolvedValue({ application_id: 'test-app-id' }),
  },
}));

// Mock the auth context
const mockUser = {
  user_id: 'test-user-id',
  name: 'Test User',
  email: 'test@example.com',
  role: 'veteran' as const,
  employee_id: 'EMP001',
  department: 'Engineering',
  join_date: '2020-01-01',
  is_active: true,
  created_at: '2020-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// Mock useAuth hook
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
    signUp: jest.fn(),
  }),
}));

describe('RecommendationsList', () => {
  beforeEach(() => {
    mockGetRecommendations.mockResolvedValue([]);
  });

  test('shows loading state initially', () => {
    render(<RecommendationsList />);

    // The component shows loading state first with Japanese text
    expect(screen.getByText(/AIポジション／プロジェクト レコメンドを読み込み中/)).toBeInTheDocument();
  });

  test('renders recommendations header after loading', async () => {
    render(<RecommendationsList />);

    // Wait for loading to complete - the header should appear
    const header = await screen.findByText('AIポジション／プロジェクト レコメンド');
    expect(header).toBeInTheDocument();
  });

  test('renders filter and sort controls after loading', async () => {
    render(<RecommendationsList />);

    // Wait for loading to complete and check for Japanese filter/sort labels
    const filterLabel = await screen.findByText('ソースでフィルター:');
    expect(filterLabel).toBeInTheDocument();
    expect(screen.getByText('並び順:')).toBeInTheDocument();
  });
});
