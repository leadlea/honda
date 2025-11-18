import { get } from 'aws-amplify/api';
import { fetchAuthSession } from 'aws-amplify/auth';
import { UserStatistics } from '../types/profile';

class StatisticsService {
  async getUserStatistics(userId: string): Promise<UserStatistics> {
    try {
      console.log('[StatisticsService] Fetching statistics for user:', userId);
      const { tokens } = await fetchAuthSession();
      const idToken = tokens?.idToken?.toString();
      
      if (!idToken) {
        console.error('[StatisticsService] No ID token available');
        throw new Error('Not authenticated');
      }

      console.log('[StatisticsService] Making API request to /stats/' + userId);
      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/stats/${userId}`,
        options: {
          headers: {
            Authorization: `Bearer ${idToken}`,
            'Content-Type': 'application/json',
          },
        },
      }).response;

      console.log('[StatisticsService] Response status:', response.statusCode);
      const data = (await response.body.json()) as any;
      console.log('[StatisticsService] Response data:', data);
      return data.statistics;
    } catch (error) {
      console.error('[StatisticsService] Get user statistics error:', error);
      // エラー時はデフォルト値を返す
      return {
        completed_questionnaires: 0,
        received_recommendations: 0,
        submitted_applications: 0,
        profile_views: 0,
      };
    }
  }
}

export const statisticsService = new StatisticsService();
