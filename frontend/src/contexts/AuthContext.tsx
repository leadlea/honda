import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { authService } from '../services/authService';
import { User, AuthState } from '../types/auth';

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  signUp: (userData: any) => Promise<void>;
  updateProfile: (userData: Partial<User>) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

type AuthAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_AUTHENTICATED'; payload: boolean };

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_USER':
      return { 
        ...state, 
        user: action.payload, 
        isAuthenticated: !!action.payload,
        loading: false 
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'SET_AUTHENTICATED':
      return { ...state, isAuthenticated: action.payload };
    default:
      return state;
  }
};

const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
  loading: true,
  error: null,
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  const login = async (email: string, password: string): Promise<void> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });

      await authService.login({ email, password });
      const user = await authService.getUserProfile();
      
      dispatch({ type: 'SET_USER', payload: user });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'ログインに失敗しました' });
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      await authService.logout();
      dispatch({ type: 'SET_USER', payload: null });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'ログアウトに失敗しました' });
      throw error;
    }
  };

  const signUp = async (userData: any): Promise<void> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });

      await authService.signUp(userData);
      // Note: After sign up, user needs to verify email before they can login
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'アカウント作成に失敗しました' });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const updateProfile = async (userData: Partial<User>): Promise<void> => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_ERROR', payload: null });

      const updatedUser = await authService.updateUserProfile(userData);
      dispatch({ type: 'SET_USER', payload: updatedUser });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'プロフィール更新に失敗しました' });
      throw error;
    }
  };

  const refreshUser = async (): Promise<void> => {
    try {
      const user = await authService.getUserProfile();
      dispatch({ type: 'SET_USER', payload: user });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'ユーザー情報の取得に失敗しました' });
    }
  };

  // Check authentication status on mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const isAuth = await authService.isAuthenticated();
        if (isAuth) {
          const user = await authService.getUserProfile();
          dispatch({ type: 'SET_USER', payload: user });
        } else {
          dispatch({ type: 'SET_LOADING', payload: false });
        }
      } catch (error) {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    checkAuthStatus();
  }, []);

  const value: AuthContextType = {
    ...state,
    login,
    logout,
    signUp,
    updateProfile,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};