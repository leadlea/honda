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
  async login(credentials: LoginCredentials): Promise<any> {
    try {
      // 既存セッションがあると "There is already a signed in user." が出るため事前に掃除
      try {
        const u = await amplifyGetCurrentUser();
        if (u) {
          await signOut({ global: true });
        }
      } catch {
        // 未ログインなら無視
      }
      // 念のためローカルセッションもクリア
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
      // 全端末のセッションも含めて無効化
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
      // 未ログイン
      return null;
    }
  }

  async getUserProfile(): Promise<User | null> {
    try {
      const cognitoUser = await this.getCurrentUser();
      if (!cognitoUser) return null;

      const response = await get({
        apiName: 'veteranTalentAPI',
        path: `/auth/profile`,
      }).response;

      const userData = (await response.body.json()) as any;
      return userData.user;
    } catch (error) {
      console.error('Get user profile error:', error);
      return null;
    }
  }

  async updateUserProfile(userData: Partial<User>): Promise<User> {
    try {
      const response = await put({
        apiName: 'veteranTalentAPI',
        path: `/auth/profile`,
        options: { body: userData },
      }).response;

      const updatedUser = (await response.body.json()) as any;
      return updatedUser.user;
    } catch (error) {
      console.error('Update user profile error:', error);
      throw error;
    }
  }

  async getAuthToken(): Promise<string | null> {
    try {
      const session = await fetchAuthSession();
      return session.tokens?.idToken?.toString() ?? null;
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
