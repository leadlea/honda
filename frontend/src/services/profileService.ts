import { get, put, post } from 'aws-amplify/api';
import { VeteranProfile, Questionnaire, BusinessTitleSuggestion, PrivacySettings } from '../types/profile';

class ProfileService {
  async getProfile(userId: string): Promise<VeteranProfile | null> {
    try {
      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/profiles/${userId}`,
      }).response;

      const data = await response.body.json() as any;
      return data.profile;
    } catch (error) {
      console.error('Get profile error:', error);
      return null;
    }
  }

  async updateProfile(userId: string, profileData: Partial<VeteranProfile>): Promise<VeteranProfile> {
    try {
      const response = await put({
        apiName: 'veteranTalentAPI',
        path: `/profiles/${userId}`,
        options: {
          body: JSON.stringify(profileData),
          headers: {
            'Content-Type': 'application/json',
          },
        },
      }).response;

      const data = await response.body.json() as any;
      return data.profile;
    } catch (error) {
      console.error('Update profile error:', error);
      throw error;
    }
  }

  async updatePrivacySettings(userId: string, privacySettings: PrivacySettings): Promise<VeteranProfile> {
    try {
      const response = await put({
        apiName: 'veteranTalentAPI',
        path: `/profiles/${userId}/privacy`,
        options: {
          body: JSON.stringify(privacySettings),
          headers: {
            'Content-Type': 'application/json',
          },
        },
      }).response;

      const data = await response.body.json() as any;
      return data.profile;
    } catch (error) {
      console.error('Update privacy settings error:', error);
      throw error;
    }
  }

  async generateBusinessTitle(userId: string): Promise<BusinessTitleSuggestion[]> {
    try {
      const response = await post({
        apiName: 'veteranTalentAPI',
        path: `/profiles/${userId}/business-title`,
      }).response;

      const data = await response.body.json() as any;
      return data.suggestions;
    } catch (error) {
      console.error('Generate business title error:', error);
      throw error;
    }
  }

  async getQuestionnaire(userId: string): Promise<Questionnaire | null> {
    try {
      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/questionnaire/${userId}`,
      }).response;

      const data = await response.body.json() as any;
      return data.questionnaire;
    } catch (error) {
      console.error('Get questionnaire error:', error);
      return null;
    }
  }

  async submitQuestionnaire(userId: string, responses: any): Promise<Questionnaire> {
    try {
      const response = await post({
        apiName: 'veteranTalentAPI',
        path: `/questionnaire/${userId}/submit`,
        options: {
          body: JSON.stringify({ responses }),
          headers: {
            'Content-Type': 'application/json',
          },
        },
      }).response;

      const data = await response.body.json() as any;
      return data.questionnaire;
    } catch (error) {
      console.error('Submit questionnaire error:', error);
      throw error;
    }
  }

  async regenerateQuestionnaire(userId: string): Promise<Questionnaire> {
    try {
      const response = await put({
        apiName: 'veteranTalentAPI',
        path: `/questionnaire/${userId}/regenerate`,
      }).response;

      const data = await response.body.json() as any;
      return data.questionnaire;
    } catch (error) {
      console.error('Regenerate questionnaire error:', error);
      throw error;
    }
  }

  async getQuestionnaireHistory(userId: string): Promise<Questionnaire[]> {
    try {
      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/questionnaire/${userId}/history`,
      }).response;

      const data = await response.body.json() as any;
      return data.questionnaires;
    } catch (error) {
      console.error('Get questionnaire history error:', error);
      return [];
    }
  }
}

export const profileService = new ProfileService();