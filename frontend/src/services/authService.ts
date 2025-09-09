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
  // 共通：認証ヘッダーを作る
  private async authHeaders(): Promise<Record<string, string>> {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();
    if (!idToken) throw new Error('No ID token in session');
    // User Pools Authorizer は Authorization ヘッダーに JWT を期待
    // （Bearer なしで動く構成が一般的）
    return { Authorization: idToken };
    // もし環境側で Bearer を要求しているなら:
    // return { Authorization: `Bearer ${idToken}` };
  }

  async login(credentials: LoginCredentials): Promise<any> {
    try {
      // 既存セッション掃除（今回の元エラー対策）
      try {
        const u = await amplifyGetCurrentUser();
        if (u) await signOut({ global: true });
      } catch {/* 未ログインなら無視 */}
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
    } catch (error) {
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
          headers: await this.authHeaders(),   // ← 追加
        },
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
        path: '/auth/profile',
        options: {
          body: userData,
          headers: await this.authHeaders(),   // ← 追加
        },
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
