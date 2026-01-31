/**
 * Unit tests for StatisticsService
 * Tests dashboard data retrieval, error handling, and loading states
 */

import { statisticsService } from './statisticsService';
import { get } from 'aws-amplify/api';
import { fetchAuthSession } from 'aws-amplify/auth';

// Mock AWS Amplify modules
jest.mock('aws-amplify/api');
jest.mock('aws-amplify/auth');

describe('StatisticsService', () => {
  const mockUserId = 'user-123';
  const mockIdToken = 'mock-id-token-12345';
  const mockStatistics = {
    completed_questionnaires: 5,
    received_recommendations: 10,
    submitted_applications: 3,
    profile_views: 42,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock fetchAuthSession to return a valid token
    (fetchAuthSession as jest.Mock).mockResolvedValue({
      tokens: {
        idToken: {
          toString: () => mockIdToken,
        },
      },
    });
  });

  describe('getUserStatistics', () => {
    it('should fetch user statistics successfully', async () => {
      // Mock successful API response
      const mockResponse = {
        statusCode: 200,
        body: {
          json: jest.fn().mockResolvedValue({
            user_id: mockUserId,
            statistics: mockStatistics,
            last_updated: '2024-01-01T00:00:00Z',
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(fetchAuthSession).toHaveBeenCalled();
      expect(get).toHaveBeenCalledWith({
        apiName: 'veteranTalentAPI',
        path: `/stats/${mockUserId}`,
        options: {
          headers: {
            Authorization: `Bearer ${mockIdToken}`,
            'Content-Type': 'application/json',
          },
        },
      });
      expect(result).toEqual(mockStatistics);
    });

    it('should include Bearer token in Authorization header', async () => {
      const mockResponse = {
        statusCode: 200,
        body: {
          json: jest.fn().mockResolvedValue({
            statistics: mockStatistics,
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      await statisticsService.getUserStatistics(mockUserId);

      const callArgs = (get as jest.Mock).mock.calls[0][0];
      expect(callArgs.options.headers.Authorization).toBe(`Bearer ${mockIdToken}`);
      expect(callArgs.options.headers['Content-Type']).toBe('application/json');
    });

    it('should return default values when not authenticated', async () => {
      // Mock no token available
      (fetchAuthSession as jest.Mock).mockResolvedValue({
        tokens: null,
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(result).toEqual({
        completed_questionnaires: 0,
        received_recommendations: 0,
        submitted_applications: 0,
        profile_views: 0,
      });
    });

    it('should return default values when idToken is undefined', async () => {
      // Mock token without idToken
      (fetchAuthSession as jest.Mock).mockResolvedValue({
        tokens: {
          idToken: undefined,
        },
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(result).toEqual({
        completed_questionnaires: 0,
        received_recommendations: 0,
        submitted_applications: 0,
        profile_views: 0,
      });
    });

    it('should handle API errors gracefully', async () => {
      // Mock API error
      (get as jest.Mock).mockReturnValue({
        response: Promise.reject(new Error('API Error')),
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(result).toEqual({
        completed_questionnaires: 0,
        received_recommendations: 0,
        submitted_applications: 0,
        profile_views: 0,
      });
    });

    it('should handle network errors gracefully', async () => {
      // Mock network error
      (fetchAuthSession as jest.Mock).mockRejectedValue(new Error('Network error'));

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(result).toEqual({
        completed_questionnaires: 0,
        received_recommendations: 0,
        submitted_applications: 0,
        profile_views: 0,
      });
    });

    it('should handle malformed response data', async () => {
      // Mock response without statistics field
      const mockResponse = {
        statusCode: 200,
        body: {
          json: jest.fn().mockResolvedValue({
            user_id: mockUserId,
            // Missing statistics field
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      // When statistics field is missing, it returns undefined
      expect(result).toBeUndefined();
    });

    it('should handle empty statistics data', async () => {
      // Mock response with zero values
      const emptyStats = {
        completed_questionnaires: 0,
        received_recommendations: 0,
        submitted_applications: 0,
        profile_views: 0,
      };

      const mockResponse = {
        statusCode: 200,
        body: {
          json: jest.fn().mockResolvedValue({
            user_id: mockUserId,
            statistics: emptyStats,
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(result).toEqual(emptyStats);
    });

    it('should handle partial statistics data', async () => {
      // Mock response with some missing fields
      const partialStats = {
        completed_questionnaires: 5,
        received_recommendations: 10,
        // Missing submitted_applications and profile_views
      };

      const mockResponse = {
        statusCode: 200,
        body: {
          json: jest.fn().mockResolvedValue({
            user_id: mockUserId,
            statistics: partialStats,
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(result).toEqual(partialStats);
    });

    it('should log errors for debugging', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      
      // Mock API error
      const error = new Error('Test error');
      (get as jest.Mock).mockReturnValue({
        response: Promise.reject(error),
      });

      await statisticsService.getUserStatistics(mockUserId);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        '[StatisticsService] Get user statistics error:',
        error
      );

      consoleErrorSpy.mockRestore();
    });

    it('should make API call with correct path', async () => {
      const mockResponse = {
        statusCode: 200,
        body: {
          json: jest.fn().mockResolvedValue({
            statistics: mockStatistics,
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      await statisticsService.getUserStatistics(mockUserId);

      const callArgs = (get as jest.Mock).mock.calls[0][0];
      expect(callArgs.path).toBe(`/stats/${mockUserId}`);
      expect(callArgs.apiName).toBe('veteranTalentAPI');
    });
  });

  describe('Error Handling', () => {
    it('should handle 401 Unauthorized errors', async () => {
      const mockResponse = {
        statusCode: 401,
        body: {
          json: jest.fn().mockResolvedValue({
            error: 'Unauthorized',
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      // When error response doesn't have statistics field, returns undefined
      expect(result).toBeUndefined();
    });

    it('should handle 403 Forbidden errors', async () => {
      const mockResponse = {
        statusCode: 403,
        body: {
          json: jest.fn().mockResolvedValue({
            error: 'Access denied',
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(result).toBeUndefined();
    });

    it('should handle 500 Internal Server Error', async () => {
      const mockResponse = {
        statusCode: 500,
        body: {
          json: jest.fn().mockResolvedValue({
            error: 'Internal server error',
          }),
        },
      };

      (get as jest.Mock).mockReturnValue({
        response: Promise.resolve(mockResponse),
      });

      const result = await statisticsService.getUserStatistics(mockUserId);

      expect(result).toBeUndefined();
    });
  });
});
