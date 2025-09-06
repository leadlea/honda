import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { User } from '../../types/auth';
import './UserProfile.css';

const UserProfile: React.FC = () => {
  const { user, updateProfile, loading } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<Partial<User>>({});

  if (!user) {
    return <div className="profile-loading">ユーザー情報を読み込み中...</div>;
  }

  const handleEdit = () => {
    setEditData({
      name: user.name,
      department: user.department,
      employee_id: user.employee_id,
    });
    setIsEditing(true);
  };

  const handleCancel = () => {
    setEditData({});
    setIsEditing(false);
  };

  const handleSave = async () => {
    try {
      await updateProfile(editData);
      setIsEditing(false);
      setEditData({});
    } catch (error) {
      console.error('Profile update failed:', error);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setEditData({
      ...editData,
      [e.target.name]: e.target.value,
    });
  };

  const getRoleBadgeClass = (role: string) => {
    switch (role) {
      case 'admin':
        return 'role-badge admin';
      case 'external_recruiter':
        return 'role-badge external';
      default:
        return 'role-badge veteran';
    }
  };

  const getRoleDisplayName = (role: string) => {
    switch (role) {
      case 'admin':
        return '管理者';
      case 'external_recruiter':
        return '外部リクルーター';
      default:
        return 'ベテラン社員';
    }
  };

  return (
    <div className="user-profile-container">
      <div className="profile-header">
        <h2>ユーザープロフィール</h2>
        <div className={getRoleBadgeClass(user.role)}>
          {getRoleDisplayName(user.role)}
        </div>
      </div>

      <div className="profile-content">
        {isEditing ? (
          <div className="profile-edit-form">
            <div className="form-group">
              <label htmlFor="name">氏名</label>
              <input
                type="text"
                id="name"
                name="name"
                value={editData.name || ''}
                onChange={handleChange}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="employee_id">社員ID</label>
              <input
                type="text"
                id="employee_id"
                name="employee_id"
                value={editData.employee_id || ''}
                onChange={handleChange}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="department">部署</label>
              <select
                id="department"
                name="department"
                value={editData.department || ''}
                onChange={handleChange}
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

            <div className="profile-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleCancel}
                disabled={loading}
              >
                キャンセル
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSave}
                disabled={loading}
              >
                {loading ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        ) : (
          <div className="profile-display">
            <div className="profile-field">
              <label>氏名</label>
              <span>{user.name}</span>
            </div>

            <div className="profile-field">
              <label>メールアドレス</label>
              <span>{user.email}</span>
            </div>

            <div className="profile-field">
              <label>社員ID</label>
              <span>{user.employee_id}</span>
            </div>

            <div className="profile-field">
              <label>部署</label>
              <span>{user.department}</span>
            </div>

            <div className="profile-field">
              <label>入社日</label>
              <span>{new Date(user.join_date).toLocaleDateString('ja-JP')}</span>
            </div>

            <div className="profile-field">
              <label>アカウント作成日</label>
              <span>{new Date(user.created_at).toLocaleDateString('ja-JP')}</span>
            </div>

            <div className="profile-field">
              <label>最終更新日</label>
              <span>{new Date(user.updated_at).toLocaleDateString('ja-JP')}</span>
            </div>

            <div className="profile-field">
              <label>ステータス</label>
              <span className={`status ${user.is_active ? 'active' : 'inactive'}`}>
                {user.is_active ? 'アクティブ' : '非アクティブ'}
              </span>
            </div>

            <div className="profile-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleEdit}
                disabled={loading}
              >
                編集
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserProfile;