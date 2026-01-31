import {
  signIn,
  signOut,
  signUp,
  getCurrentUser as amplifyGetCurrentUser,
  fetchAuthSession,
} from 'aws-amplify/auth';
import { get, put } from 'aws-amplify/api';
import { User, LoginCredentials, SignUpData } from '../types/auth';

class AuthService {
  // 共通: 認証ヘッダー
  private async authHeaders(): Promise<Record<string, string>> {
    const s = await fetchAuthSession();
    const idToken = s.tokens?.idToken?.toString();
    if (!idToken) throw new Error('No ID token in session');
    return { Authorization: `Bearer ${idToken}` };
  }

  async login(credentials: LoginCredentials): Promise<any> {
    try {
      // 残留セッション掃除（"already signed in user" 対策）
      try {
        const u = await amplifyGetCurrentUser();
        if (u) await signOut({ global: true });
      } catch {}
      await signOut().catch(() => {});

      const result = await signIn({
        username: credentials.email,
        password: credentials.password,
      });
      return result;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  async logout(): Promise<void> {
    try {
      await signOut({ global: true });
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  }

  async signUp(userData: SignUpData): Promise<any> {
    try {
      const result = await signUp({
        username: userData.email,
        password: userData.password,
        options: {
          userAttributes: {
            email: userData.email,
            name: userData.name,
            'custom:employee_id': userData.employee_id,
            'custom:department': userData.department,
          },
        },
      });
      return result;
    } catch (error) {
      console.error('Sign up error:', error);
      throw error;
    }
  }

  async getCurrentUser(): Promise<any> {
    try {
      const user = await amplifyGetCurrentUser();
      return user;
    } catch {
      return null;
    }
  }

  async getUserProfile(): Promise<User | null> {
    try {
      const cognitoUser = await this.getCurrentUser();
      if (!cognitoUser) return null;

      const response = await get({
        apiName: 'veteranTalentAPI',
        path: '/auth/profile',
        options: {
          headers: await this.authHeaders(),  // ← ここで付与
        },
      }).response;

      const data = (await response.body.json()) as any;
      return data.user;
    } catch (error) {
      console.error('Get user profile error:', error);
      return null;
    }
  }

  async updateUserProfile(userData: Partial<User>): Promise<User> {
    try {
      const response = await put({
        apiName: 'veteranTalentAPI',
        path: '/auth/profile',
        options: {
          body: userData,
          headers: await this.authHeaders(),  // ← ここで付与
        },
      }).response;

      const data = (await response.body.json()) as any;
      return data.user;
    } catch (error) {
      console.error('Update user profile error:', error);
      throw error;
    }
  }

  async getAuthToken(): Promise<string | null> {
    try {
      const s = await fetchAuthSession();
      return s.tokens?.idToken?.toString() ?? null;
    } catch (error) {
      console.error('Get auth token error:', error);
      return null;
    }
  }

  async isAuthenticated(): Promise<boolean> {
    try {
      const user = await this.getCurrentUser();
      return !!user;
    } catch {
      return false;
    }
  }
}

export const authService = new AuthService();
