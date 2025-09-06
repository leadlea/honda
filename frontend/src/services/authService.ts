import { signIn, signOut, signUp, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
import { get, put } from 'aws-amplify/api';
import { User, LoginCredentials, SignUpData } from '../types/auth';

class AuthService {
  async login(credentials: LoginCredentials): Promise<any> {
    try {
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
      await signOut();
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
      const user = await getCurrentUser();
      return user;
    } catch (error) {
      console.error('Get current user error:', error);
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

      const userData = await response.body.json() as any;
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
        options: {
          body: userData,
        },
      }).response;

      const updatedUser = await response.body.json() as any;
      return updatedUser.user;
    } catch (error) {
      console.error('Update user profile error:', error);
      throw error;
    }
  }

  async getAuthToken(): Promise<string | null> {
    try {
      const session = await fetchAuthSession();
      return session.tokens?.idToken?.toString() || null;
    } catch (error) {
      console.error('Get auth token error:', error);
      return null;
    }
  }

  async isAuthenticated(): Promise<boolean> {
    try {
      const user = await this.getCurrentUser();
      return !!user;
    } catch (error) {
      return false;
    }
  }
}

export const authService = new AuthService();