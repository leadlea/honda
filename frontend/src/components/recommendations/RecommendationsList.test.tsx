import React from 'react';
import { render, screen } from '@testing-library/react';
import { AuthProvider } from '../../contexts/AuthContext';
import RecommendationsList from './RecommendationsList';

// Mock the recommendation service
jest.mock('../../services/recommendationService', () => ({
  RecommendationService: {
    getRecommendations: jest.fn().mockResolvedValue([]),
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

const MockAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  );
};

// Mock useAuth hook
jest.mock('../../contexts/AuthContext', () => ({
  ...jest.requireActual('../../contexts/AuthContext'),
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
    jest.clearAllMocks();
  });

  test('renders recommendations header', async () => {
    render(
      <MockAuthProvider>
        <RecommendationsList />
      </MockAuthProvider>
    );

    expect(screen.getByText('Recommended Opportunities')).toBeInTheDocument();
    expect(screen.getByText('AI-powered recommendations based on your profile and preferences')).toBeInTheDocument();
  });

  test('shows loading state initially', async () => {
    render(
      <MockAuthProvider>
        <RecommendationsList />
      </MockAuthProvider>
    );

    expect(screen.getByText('Loading your personalized recommendations...')).toBeInTheDocument();
  });

  test('renders filter and sort controls', async () => {
    render(
      <MockAuthProvider>
        <RecommendationsList />
      </MockAuthProvider>
    );

    expect(screen.getByText('Filter by source:')).toBeInTheDocument();
    expect(screen.getByText('Sort by:')).toBeInTheDocument();
  });
});