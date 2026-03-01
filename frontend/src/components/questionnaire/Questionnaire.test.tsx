import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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

// Use plain functions that won't be affected by resetMocks
jest.mock('../../services/profileService', () => ({
  profileService: {
    getQuestionnaire: () => Promise.resolve(null),
    getQuestionnaireHistory: () => Promise.resolve([]),
    submitQuestionnaire: () => Promise.resolve({}),
    regenerateQuestionnaire: () => Promise.resolve({}),
  },
}));

describe('Questionnaire Component', () => {
  test('renders questionnaire component', () => {
    render(<Questionnaire />);
    expect(document.body).toBeInTheDocument();
  });

  test('renders empty state when no questionnaire', async () => {
    render(<Questionnaire />);
    
    await waitFor(() => {
      expect(screen.getByText('AIスキル棚卸し（セルフ診断）が見つかりません')).toBeInTheDocument();
    });
    expect(screen.getByText('新しいAIスキル棚卸し（セルフ診断）を生成しますか？')).toBeInTheDocument();
  });
});
