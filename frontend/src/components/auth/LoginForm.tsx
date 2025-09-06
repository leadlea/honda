import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './AuthForms.css';

interface LoginFormProps {
  onSwitchToSignUp: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ onSwitchToSignUp }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login, loading, error } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
    } catch (error) {
      // Error is handled by AuthContext
    }
  };

  return (
    <div className="auth-form-container">
      <div className="auth-form">
        <h2>ログイン</h2>
        <p className="auth-subtitle">Honda Veteran Talent Bankにアクセス</p>
        
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">メールアドレス</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              placeholder="your.email@honda.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">パスワード</label>
            <div className="password-input-container">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="パスワードを入力"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                disabled={loading}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="auth-button primary"
            disabled={loading || !email || !password}
          >
            {loading ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            アカウントをお持ちでない場合は{' '}
            <button
              type="button"
              className="link-button"
              onClick={onSwitchToSignUp}
              disabled={loading}
            >
              新規登録
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;