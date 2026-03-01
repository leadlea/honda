import { PublicVeteranProfile, SearchFilters, SearchResult, ContactRequest, SkillCategory } from '../types/public';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

export class PublicSearchService {
  private static getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('authToken');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    };
  }

  static async searchVeterans(
    filters: SearchFilters = {},
    page: number = 1,
    perPage: number = 20
  ): Promise<SearchResult> {
    try {
      const queryParams = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      });

      // Add filters to query params
      if (filters.skills && filters.skills.length > 0) {
        queryParams.append('skills', filters.skills.join(','));
      }
      if (filters.experience_years) {
        queryParams.append('min_experience', filters.experience_years.min.toString());
        queryParams.append('max_experience', filters.experience_years.max.toString());
      }
      if (filters.locations && filters.locations.length > 0) {
        queryParams.append('locations', filters.locations.join(','));
      }
      if (filters.availability && filters.availability.length > 0) {
        queryParams.append('availability', filters.availability.join(','));
      }
      if (filters.work_style && filters.work_style.length > 0) {
        queryParams.append('work_style', filters.work_style.join(','));
      }
      if (filters.preferred_roles && filters.preferred_roles.length > 0) {
        queryParams.append('preferred_roles', filters.preferred_roles.join(','));
      }

      const response = await fetch(`${API_BASE_URL}/public/veterans/search?${queryParams}`, {
        method: 'GET',
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`社内AI人材候補の検索に失敗しました: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error searching AI talent candidates:', error);
      throw error;
    }
  }

  static async getVeteranProfile(profileId: string): Promise<PublicVeteranProfile> {
    try {
      const response = await fetch(`${API_BASE_URL}/public/veterans/${profileId}`, {
        method: 'GET',
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`社内AI人材候補のプロフィール取得に失敗しました: ${response.statusText}`);
      }

      const data = await response.json();
      return data.profile;
    } catch (error) {
      console.error('Error fetching AI talent candidate profile:', error);
      throw error;
    }
  }

  static async sendContactRequest(
    profileId: string,
    contactData: {
      recruiter_name: string;
      recruiter_email: string;
      company: string;
      position_title: string;
      message: string;
    }
  ): Promise<ContactRequest> {
    try {
      const response = await fetch(`${API_BASE_URL}/public/contact/${profileId}`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(contactData),
      });

      if (!response.ok) {
        throw new Error(`連絡リクエストの送信に失敗しました: ${response.statusText}`);
      }

      const data = await response.json();
      return data.contact_request;
    } catch (error) {
      console.error('Error sending contact request:', error);
      throw error;
    }
  }

  static async getSkillCategories(): Promise<SkillCategory[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/public/categories`, {
        method: 'GET',
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`スキルカテゴリの取得に失敗しました: ${response.statusText}`);
      }

      const data = await response.json();
      return data.categories || [];
    } catch (error) {
      console.error('Error fetching skill categories:', error);
      throw error;
    }
  }

  static async getContactHistory(): Promise<ContactRequest[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/public/contacts/history`, {
        method: 'GET',
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`連絡履歴の取得に失敗しました: ${response.statusText}`);
      }

      const data = await response.json();
      return data.contacts || [];
    } catch (error) {
      console.error('Error fetching contact history:', error);
      throw error;
    }
  }
}