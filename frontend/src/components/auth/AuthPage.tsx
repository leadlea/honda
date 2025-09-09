import React, { useState, useEffect } from 'react';
import LoginForm from './LoginForm';
import SignUpForm from './SignUpForm';
import { signOut, getCurrentUser as amplifyGetCurrentUser } from 'aws-amplify/auth';

const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);

  // 初回表示時に残留セッションを強制クリア
  useEffect(() => {
    (async () => {
      try {
        const u = await amplifyGetCurrentUser();
        if (u) {
          // リフレッシュトークンも無効化（多端末含む）
          await signOut({ global: true });
        }
      } catch {
        // 未ログインなら何もしない
      }
    })();
  }, []);

  return (
    <>
      {isLogin ? (
        <LoginForm onSwitchToSignUp={() => setIsLogin(false)} />
      ) : (
        <SignUpForm onSwitchToLogin={() => setIsLogin(true)} />
      )}
    </>
  );
};

export default AuthPage;
