import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './AuthForms.css';

interface SignUpFormProps {
  onSwitchToLogin: () => void;
}

const SignUpForm: React.FC<SignUpFormProps> = ({ onSwitchToLogin }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: '',
    employee_id: '',
    department: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [signUpSuccess, setSignUpSuccess] = useState(false);
  const { signUp, loading, error } = useAuth();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      alert('パスワードが一致しません');
      return;
    }

    try {
      await signUp({
        email: formData.email,
        password: formData.password,
        name: formData.name,
        employee_id: formData.employee_id,
        department: formData.department,
      });
      setSignUpSuccess(true);
    } catch (error) {
      // Error is handled by AuthContext
    }
  };

  if (signUpSuccess) {
    return (
      <div className="auth-form-container">
        <div className="auth-form">
          <h2>登録完了</h2>
          <div className="success-message">
            <p>アカウントが正常に作成されました。</p>
            <p>メールアドレスに送信された確認コードを使用してアカウントを有効化してください。</p>
          </div>
          <button
            type="button"
            className="auth-button primary"
            onClick={onSwitchToLogin}
          >
            ログインページに戻る
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-form-container">
      <div className="auth-form">
        <h2>新規登録</h2>
        <p className="auth-subtitle">AI人材発掘・配置マッチングMVP（AI CoE支援）アカウントを作成</p>
        
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">氏名</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              disabled={loading}
              placeholder="山田 太郎"
            />
          </div>

          <div className="form-group">
            <label htmlFor="employee_id">社員ID</label>
            <input
              type="text"
              id="employee_id"
              name="employee_id"
              value={formData.employee_id}
              onChange={handleChange}
              required
              disabled={loading}
              placeholder="H123456"
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">メールアドレス</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              disabled={loading}
              placeholder="your.email@company.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="department">部署</label>
            <select
              id="department"
              name="department"
              value={formData.department}
              onChange={handleChange}
              required
              disabled={loading}
            >
              <option value="">部署を選択</option>
              <option value="研究開発">研究開発</option>
              <option value="製造">製造</option>
              <option value="営業">営業</option>
              <option value="マーケティング">マーケティング</option>
              <option value="人事">人事</option>
              <option value="財務">財務</option>
              <option value="IT">IT</option>
              <option value="品質管理">品質管理</option>
              <option value="その他">その他</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="password">パスワード</label>
            <div className="password-input-container">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                disabled={loading}
                placeholder="8文字以上のパスワード"
                minLength={8}
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

          <div className="form-group">
            <label htmlFor="confirmPassword">パスワード確認</label>
            <div className="password-input-container">
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                disabled={loading}
                placeholder="パスワードを再入力"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                disabled={loading}
              >
                {showConfirmPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="auth-button primary"
            disabled={loading || !formData.email || !formData.password || !formData.name || !formData.employee_id || !formData.department}
          >
            {loading ? '登録中...' : 'アカウント作成'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            既にアカウントをお持ちの場合は{' '}
            <button
              type="button"
              className="link-button"
              onClick={onSwitchToLogin}
              disabled={loading}
            >
              ログイン
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignUpForm;