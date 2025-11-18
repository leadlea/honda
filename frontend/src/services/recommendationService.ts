import { Recommendation, Application } from '../types/profile';
import { authService } from './authService';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

export class RecommendationService {
  private static async getAuthHeaders(): Promise<HeadersInit> {
    const token = await authService.getAuthToken();
    if (!token) {
      throw new Error('認証トークンが見つかりません。再度ログインしてください。');
    }
    return {
      'Content-Type': 'application/json',
      'Authorization': token,
    };
  }

  static async getRecommendations(userId: string): Promise<Recommendation[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/recommendations/${userId}`, {
        method: 'GET',
        headers: await this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch recommendations: ${response.statusText}`);
      }

      const data = await response.json();
      return data.recommendations || [];
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      throw error;
    }
  }

  static async markRecommendationAsViewed(recommendationId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/recommendations/${recommendationId}/view`, {
        method: 'PUT',
        headers: await this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`Failed to mark recommendation as viewed: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error marking recommendation as viewed:', error);
      throw error;
    }
  }

  static async dismissRecommendation(recommendationId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/recommendations/${recommendationId}/dismiss`, {
        method: 'PUT',
        headers: await this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`Failed to dismiss recommendation: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error dismissing recommendation:', error);
      throw error;
    }
  }

  static async applyToOpportunity(userId: string, opportunityId: string, notes?: string): Promise<Application> {
    try {
      const response = await fetch(`${API_BASE_URL}/applications/${userId}`, {
        method: 'POST',
        headers: await this.getAuthHeaders(),
        body: JSON.stringify({
          opportunity_id: opportunityId,
          notes: notes || '',
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to apply to opportunity: ${response.statusText}`);
      }

      const data = await response.json();
      return data.application;
    } catch (error) {
      console.error('Error applying to opportunity:', error);
      throw error;
    }
  }

  static async getApplications(userId: string): Promise<Application[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/applications/${userId}`, {
        method: 'GET',
        headers: await this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch applications: ${response.statusText}`);
      }

      const data = await response.json();
      return data.applications || [];
    } catch (error) {
      console.error('Error fetching applications:', error);
      throw error;
    }
  }

  static async withdrawApplication(applicationId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/applications/${applicationId}/withdraw`, {
        method: 'PUT',
        headers: await this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`Failed to withdraw application: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error withdrawing application:', error);
      throw error;
    }
  }
}