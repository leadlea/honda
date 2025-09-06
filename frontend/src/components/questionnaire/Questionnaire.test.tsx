import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Questionnaire from './Questionnaire';

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
    getQuestionnaire: jest.fn().mockResolvedValue(null),
    getQuestionnaireHistory: jest.fn().mockResolvedValue([]),
    submitQuestionnaire: jest.fn(),
    regenerateQuestionnaire: jest.fn(),
  },
}));

describe('Questionnaire Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders questionnaire component', () => {
    render(<Questionnaire />);
    
    // Should render the component without crashing
    expect(document.body).toBeInTheDocument();
  });

  test('renders empty state when no questionnaire', async () => {
    render(<Questionnaire />);
    
    // Wait for loading to complete and check for empty state
    await screen.findByText('問診が見つかりません');
    expect(screen.getByText('新しい問診を生成しますか？')).toBeInTheDocument();
  });
});