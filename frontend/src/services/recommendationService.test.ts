import { RecommendationService } from './recommendationService';
import { authService } from './authService';

// Mock authService
jest.mock('./authService', () => ({
  authService: {
    getAuthToken: jest.fn(),
  },
}));

// Mock fetch
global.fetch = jest.fn();

describe('RecommendationService Authentication Fix', () => {
  const mockToken = 'mock-jwt-token-12345';
  const mockUserId = 'user-123';
  const mockRecommendations = [
    {
      id: 'rec-1',
      title: 'Software Engineer',
      company: 'Tech Corp',
      match_score: 0.95,
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    (authService.getAuthToken as jest.Mock).mockResolvedValue(mockToken);
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ recommendations: mockRecommendations }),
    });
  });

  describe('Token Retrieval', () => {
    it('should retrieve token from authService instead of localStorage', async () => {
      await RecommendationService.getRecommendations(mockUserId);

      expect(authService.getAuthToken).toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: mockToken,
          }),
        })
      );
    });

    it('should include token in Authorization header without Bearer prefix', async () => {
      await RecommendationService.getRecommendations(mockUserId);

      const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
      const headers = fetchCall[1].headers;

      expect(headers.Authorization).toBe(mockToken);
      expect(headers['Content-Type']).toBe('application/json');
    });

    it('should throw error when token is not available', async () => {
      (authService.getAuthToken as jest.Mock).mockResolvedValue(null);

      await expect(
        RecommendationService.getRecommendations(mockUserId)
      ).rejects.toThrow('認証トークンが見つかりません。再度ログインしてください。');
    });
  });

  describe('API Methods with Authentication', () => {
    it('should call getRecommendations with valid token without Bearer prefix', async () => {
      const result = await RecommendationService.getRecommendations(mockUserId);

      expect(result).toEqual(mockRecommendations);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/recommendations/${mockUserId}`),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Authorization: mockToken,
          }),
        })
      );
    });

    it('should call markRecommendationAsViewed with valid token without Bearer prefix', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({}),
      });

      await RecommendationService.markRecommendationAsViewed('rec-1');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/recommendations/rec-1/view'),
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({
            Authorization: mockToken,
          }),
        })
      );
    });

    it('should call applyToOpportunity with valid token without Bearer prefix', async () => {
      const mockApplication = { id: 'app-1', status: 'pending' };
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ application: mockApplication }),
      });

      const result = await RecommendationService.applyToOpportunity(
        mockUserId,
        'opp-1',
        'Test notes'
      );

      expect(result).toEqual(mockApplication);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/applications/${mockUserId}`),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: mockToken,
          }),
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('should handle 401 Unauthorized errors', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        statusText: 'Unauthorized',
      });

      await expect(
        RecommendationService.getRecommendations(mockUserId)
      ).rejects.toThrow('Failed to fetch recommendations: Unauthorized');
    });

    it('should handle network errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      await expect(
        RecommendationService.getRecommendations(mockUserId)
      ).rejects.toThrow('Network error');
    });

    it('should handle missing token gracefully', async () => {
      (authService.getAuthToken as jest.Mock).mockResolvedValue(null);

      await expect(
        RecommendationService.getRecommendations(mockUserId)
      ).rejects.toThrow('認証トークンが見つかりません');
    });
  });

  describe('All Methods Use Async Token Retrieval', () => {
    beforeEach(() => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({}),
      });
    });

    it('should use async token retrieval in getApplications', async () => {
      await RecommendationService.getApplications(mockUserId);
      expect(authService.getAuthToken).toHaveBeenCalled();
    });

    it('should use async token retrieval in dismissRecommendation', async () => {
      await RecommendationService.dismissRecommendation('rec-1');
      expect(authService.getAuthToken).toHaveBeenCalled();
    });

    it('should use async token retrieval in withdrawApplication', async () => {
      await RecommendationService.withdrawApplication('app-1');
      expect(authService.getAuthToken).toHaveBeenCalled();
    });
  });
});
