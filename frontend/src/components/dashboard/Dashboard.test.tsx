/**
 * Unit tests for Dashboard component
 * Tests dashboard data retrieval, loading states, and statistics display
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from './Dashboard';
import { useAuth } from '../../contexts/AuthContext';
import { statisticsService } from '../../services/statisticsService';
import { UserStatistics } from '../../types/profile';

// Mock dependencies
jest.mock('../../contexts/AuthContext');
jest.mock('../../services/statisticsService');

describe('Dashboard Component', () => {
  const mockOnNavigate = jest.fn();
  const mockUser = {
    user_id: 'user-123',
    name: 'Test User',
    email: 'test@example.com',
    role: 'veteran' as const,
    department: 'Engineering',
    employee_id: 'EMP001',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  };

  const mockStatistics: UserStatistics = {
    completed_questionnaires: 5,
    received_recommendations: 10,
    submitted_applications: 3,
    profile_views: 42,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default mock for useAuth
    (useAuth as jest.Mock).mockReturnValue({
      user: mockUser,
      loading: false,
      error: null,
    });

    // Default mock for statisticsService
    (statisticsService.getUserStatistics as jest.Mock).mockResolvedValue(mockStatistics);
  });

  describe('Loading States', () => {
    it('should show loading message when user is not available', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        error: null,
      });

      render(<Dashboard onNavigate={mockOnNavigate} />);

      expect(screen.getByText('ダッシュボードを読み込み中...')).toBeInTheDocument();
    });

    it('should show loading indicator for statistics while fetching', async () => {
      // Mock delayed response
      (statisticsService.getUserStatistics as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockStatistics), 100))
      );

      render(<Dashboard onNavigate={mockOnNavigate} />);

      // Initially should show loading state (...)
      await waitFor(() => {
        const statElements = screen.getAllByText('...');
        expect(statElements.length).toBeGreaterThan(0);
      });
    });

    it('should hide loading indicator after statistics are loaded', async () => {
      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(screen.getByText('5')).toBeInTheDocument();
        expect(screen.getByText('10')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
        expect(screen.getByText('42')).toBeInTheDocument();
      });

      // Loading indicators should be gone
      expect(screen.queryByText('...')).not.toBeInTheDocument();
    });
  });

  describe('Statistics Display', () => {
    it('should display statistics when data is loaded', async () => {
      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(statisticsService.getUserStatistics).toHaveBeenCalledWith('user-123');
      });

      await waitFor(() => {
        expect(screen.getByText('5')).toBeInTheDocument(); // completed_questionnaires
        expect(screen.getByText('10')).toBeInTheDocument(); // received_recommendations
        expect(screen.getByText('3')).toBeInTheDocument(); // submitted_applications
        expect(screen.getByText('42')).toBeInTheDocument(); // profile_views
      });
    });

    it('should display zero values correctly', async () => {
      const zeroStats: UserStatistics = {
        completed_questionnaires: 0,
        received_recommendations: 0,
        submitted_applications: 0,
        profile_views: 0,
      };

      (statisticsService.getUserStatistics as jest.Mock).mockResolvedValue(zeroStats);

      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        const zeroElements = screen.getAllByText('0');
        expect(zeroElements.length).toBeGreaterThanOrEqual(4);
      });
    });

    it('should display dash (-) for undefined values', async () => {
      (statisticsService.getUserStatistics as jest.Mock).mockResolvedValue({
        completed_questionnaires: undefined,
        received_recommendations: undefined,
        submitted_applications: undefined,
        profile_views: undefined,
      });

      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        const dashElements = screen.getAllByText('-');
        expect(dashElements.length).toBeGreaterThanOrEqual(4);
      });
    });

    it('should display statistics labels correctly', async () => {
      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(screen.getByText('完了した問診')).toBeInTheDocument();
        expect(screen.getByText('受信した推薦')).toBeInTheDocument();
        expect(screen.getByText('応募した機会')).toBeInTheDocument();
        expect(screen.getByText('プロフィール閲覧数')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle statistics fetch error gracefully', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      
      (statisticsService.getUserStatistics as jest.Mock).mockRejectedValue(
        new Error('Failed to fetch statistics')
      );

      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          '[Dashboard] Failed to load statistics:',
          expect.any(Error)
        );
      });

      consoleErrorSpy.mockRestore();
    });

    it('should not crash when statistics service returns null', async () => {
      (statisticsService.getUserStatistics as jest.Mock).mockResolvedValue(null);

      render(<Dashboard onNavigate={mockOnNavigate} />);

      // Component should still render
      await waitFor(() => {
        expect(screen.getByText('あなたの統計')).toBeInTheDocument();
      });
    });

    it('should handle network errors gracefully', async () => {
      (statisticsService.getUserStatistics as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      render(<Dashboard onNavigate={mockOnNavigate} />);

      // Component should still render without crashing
      await waitFor(() => {
        expect(screen.getByText('あなたの統計')).toBeInTheDocument();
      });
    });
  });

  describe('User Role Handling', () => {
    it('should fetch statistics only for veteran users', async () => {
      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(statisticsService.getUserStatistics).toHaveBeenCalledWith('user-123');
      });
    });

    it('should not fetch statistics for non-veteran users', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: { ...mockUser, role: 'external_recruiter' },
        loading: false,
        error: null,
      });

      render(<Dashboard onNavigate={mockOnNavigate} />);

      // Wait a bit to ensure no call is made
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(statisticsService.getUserStatistics).not.toHaveBeenCalled();
    });

    it('should not fetch statistics for admin users', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: { ...mockUser, role: 'admin' },
        loading: false,
        error: null,
      });

      render(<Dashboard onNavigate={mockOnNavigate} />);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(statisticsService.getUserStatistics).not.toHaveBeenCalled();
    });
  });

  describe('Component Lifecycle', () => {
    it('should fetch statistics on mount for veteran users', async () => {
      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(statisticsService.getUserStatistics).toHaveBeenCalledTimes(1);
        expect(statisticsService.getUserStatistics).toHaveBeenCalledWith('user-123');
      });
    });

    it('should not fetch statistics when user is null', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        error: null,
      });

      render(<Dashboard onNavigate={mockOnNavigate} />);

      expect(statisticsService.getUserStatistics).not.toHaveBeenCalled();
    });

    it('should update statistics when user changes', async () => {
      const { rerender } = render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(statisticsService.getUserStatistics).toHaveBeenCalledWith('user-123');
      });

      // Change user
      const newUser = { ...mockUser, user_id: 'user-456' };
      (useAuth as jest.Mock).mockReturnValue({
        user: newUser,
        loading: false,
        error: null,
      });

      rerender(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(statisticsService.getUserStatistics).toHaveBeenCalledWith('user-456');
      });
    });
  });

  describe('Welcome Message', () => {
    it('should display welcome message with user name', async () => {
      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(screen.getByText(/Test User/)).toBeInTheDocument();
      });
    });

    it('should display role-specific welcome message for veterans', async () => {
      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(screen.getByText(/おかえりなさい/)).toBeInTheDocument();
      });
    });
  });

  describe('renderStatValue Function', () => {
    it('should return "..." when loading', async () => {
      (statisticsService.getUserStatistics as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockStatistics), 200))
      );

      render(<Dashboard onNavigate={mockOnNavigate} />);

      // Check for loading state
      await waitFor(() => {
        expect(screen.getAllByText('...').length).toBeGreaterThan(0);
      });
    });

    it('should return value as string when defined', async () => {
      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(screen.getByText('5')).toBeInTheDocument();
      });
    });

    it('should return "-" when value is undefined', async () => {
      (statisticsService.getUserStatistics as jest.Mock).mockResolvedValue({
        completed_questionnaires: undefined,
      });

      render(<Dashboard onNavigate={mockOnNavigate} />);

      await waitFor(() => {
        expect(screen.getAllByText('-').length).toBeGreaterThan(0);
      });
    });
  });
});
