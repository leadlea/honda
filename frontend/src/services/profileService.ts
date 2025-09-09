// frontend/src/services/profileService.ts
import { get, put, post } from 'aws-amplify/api';
import { fetchAuthSession } from 'aws-amplify/auth';
import {
  VeteranProfile,
  Questionnaire,
  BusinessTitleSuggestion,
  PrivacySettings,
} from '../types/profile';

// 共通: 認証ヘッダー（IDトークン）。バックエンド側は "Bearer " を除去する実装なので、どちらでもOK。
// 明示的に "Bearer " を付与しておく。
async function authHeaders(extra?: Record<string, string>) {
  const { tokens } = await fetchAuthSession();
  const idToken = tokens?.idToken?.toString();
  if (!idToken) throw new Error('Not authenticated');
  return {
    Authorization: `Bearer ${idToken}`,
    'Content-Type': 'application/json',
    ...(extra || {}),
  };
}

class ProfileService {
  // ---------- Profiles ----------
  async getProfile(userId: string): Promise<VeteranProfile | null> {
    try {
      const headers = await authHeaders();
      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/profiles/${userId}`,
        options: { headers },
      }).response;
      const data = (await response.body.json()) as any;
      return data.profile ?? null;
    } catch (error) {
      console.error('Get profile error:', error);
      return null;
    }
  }

  async updateProfile(
    userId: string,
    profileData: Partial<VeteranProfile>
  ): Promise<VeteranProfile> {
    try {
      const headers = await authHeaders();
      const response = await put({
        apiName: 'veteranTalentAPI',
        path: `/profiles/${userId}`,
        options: {
          headers,
          // Amplify APIは object を渡すと自動でJSON化されます
          body: profileData,
        },
      }).response;
      const data = (await response.body.json()) as any;
      return data.profile;
    } catch (error) {
      console.error('Update profile error:', error);
      throw error;
    }
  }

  async updatePrivacySettings(
    userId: string,
    privacySettings: PrivacySettings
  ): Promise<VeteranProfile> {
    try {
      const headers = await authHeaders();
      const response = await put({
        apiName: 'veteranTalentAPI',
        path: `/profiles/${userId}/privacy`,
        options: {
          headers,
          body: privacySettings,
        },
      }).response;
      const data = (await response.body.json()) as any;
      return data.profile;
    } catch (error) {
      console.error('Update privacy settings error:', error);
      throw error;
    }
  }

  async generateBusinessTitle(userId: string): Promise<BusinessTitleSuggestion[]> {
    try {
      const headers = await authHeaders();
      const response = await post({
        apiName: 'veteranTalentAPI',
        path: `/profiles/${userId}/business-title`,
        options: { headers },
      }).response;
      const data = (await response.body.json()) as any;
      return data.suggestions ?? [];
    } catch (error) {
      console.error('Generate business title error:', error);
      throw error;
    }
  }

  // ---------- Questionnaire ----------
  // バックエンドは「questions を直置き」で返すので、そのまま返す
  async getQuestionnaire(userId: string): Promise<Questionnaire | null> {
    try {
      const headers = await authHeaders();
      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/questionnaire/${userId}`,
        options: { headers },
      }).response;
      const data = (await response.body.json()) as any;
      // data.questionnaire ではなく data を採用
      return (data as Questionnaire) ?? null;
    } catch (error) {
      console.error('Get questionnaire error:', error);
      return null;
    }
  }

  // 返却は { message, questionnaire_id, submitted_at } を想定
  async submitQuestionnaire(
    userId: string,
    responses: Array<{ question_id: string; answer: any; answered_at?: string }>,
    questionnaireId?: string
  ): Promise<{ message: string; questionnaire_id: string; submitted_at: string }> {
    try {
      const headers = await authHeaders();
      const response = await post({
        apiName: 'veteranTalentAPI',
        path: `/questionnaire/${userId}/submit`,
        options: {
          headers,
          body: { questionnaire_id: questionnaireId, responses },
        },
      }).response;
      const data = (await response.body.json()) as any;
      return data;
    } catch (error) {
      console.error('Submit questionnaire error:', error);
      throw error;
    }
  }

  // 再生成も「直置きの質問票」を返す
  async regenerateQuestionnaire(userId: string, questionnaireId?: string): Promise<Questionnaire> {
    try {
      const headers = await authHeaders();
      const response = await put({
        apiName: 'veteranTalentAPI',
        path: `/questionnaire/${userId}/regenerate`,
        options: { headers, body: { questionnaire_id: questionnaireId } },
      }).response;
      const data = (await response.body.json()) as any;
      return data as Questionnaire;
    } catch (error) {
      console.error('Regenerate questionnaire error:', error);
      throw error;
    }
  }

  async getQuestionnaireHistory(userId: string): Promise<Questionnaire[]> {
    try {
      const headers = await authHeaders();
      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/questionnaire/${userId}/history`,
        options: { headers },
      }).response;
      const data = (await response.body.json()) as any;
      return (data?.questionnaires ?? []) as Questionnaire[];
    } catch (error) {
      console.error('Get questionnaire history error:', error);
      return [];
    }
  }
}

export const profileService = new ProfileService();
