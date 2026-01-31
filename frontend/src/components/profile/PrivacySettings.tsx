import React, { useState } from 'react';
import { profileService } from '../../services/profileService';
import { VeteranProfile, PrivacySettings as PrivacySettingsType } from '../../types/profile';
import { useAuth } from '../../contexts/AuthContext';
import './PrivacySettings.css';

interface PrivacySettingsProps {
  profile: VeteranProfile | null;
  onUpdate: (profile: VeteranProfile) => void;
}

const PrivacySettings: React.FC<PrivacySettingsProps> = ({ profile, onUpdate }) => {
  const { user } = useAuth();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const currentSettings = profile?.privacy_settings || {
    is_publicly_visible: false,
    external_contact: false,
    show_contact_info: false,
    show_detailed_experience: false
  };

  const updateSetting = (key: keyof PrivacySettingsType, value: boolean) => {
    if (!profile) return;

    const updatedSettings = {
      ...currentSettings,
      [key]: value
    };

    const updatedProfile = {
      ...profile,
      privacy_settings: updatedSettings,
      is_publicly_visible: updatedSettings.is_publicly_visible ? 'true' : 'false'
    };

    onUpdate(updatedProfile);
  };

  const savePrivacySettings = async () => {
    if (!user || !profile) return;

    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      const updatedProfile = await profileService.updatePrivacySettings(
        user.user_id, 
        currentSettings
      );
      
      onUpdate(updatedProfile);
      setSuccessMessage('プライバシー設定が正常に更新されました');
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      setError('プライバシー設定の更新に失敗しました');
      console.error('Update privacy settings error:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="privacy-settings">
      <div className="tab-content">
        <h3>プライバシー設定</h3>
        <p className="description">
          あなたのプロフィールの可視性とデータ共有をコントロールできます。
        </p>

        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}

        {successMessage && (
          <div className="success-message">
            <p>{successMessage}</p>
          </div>
        )}

        <div className="privacy-options">
          <div className="privacy-section">
            <h4>外部公開設定</h4>
            <div className="setting-card">
              <div className="setting-info">
                <h5>プロフィールを外部に公開</h5>
                <p>
                  製造業プラチナアドバイザリーで外部リクルーターがあなたのプロフィールを検索・閲覧できるようになります。
                  この設定をオフにすると、社内のみでプロフィールが利用されます。
                </p>
              </div>
              <div className="setting-control">
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={currentSettings.is_publicly_visible}
                    onChange={(e) => updateSetting('is_publicly_visible', e.target.checked)}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
            </div>

            {currentSettings.is_publicly_visible && (
              <div className="sub-settings">
                <div className="setting-card">
                  <div className="setting-info">
                    <h5>外部からの連絡を許可</h5>
                    <p>
                      外部リクルーターがプラットフォームを通じてあなたに連絡できるようになります。
                    </p>
                  </div>
                  <div className="setting-control">
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={currentSettings.external_contact}
                        onChange={(e) => updateSetting('external_contact', e.target.checked)}
                      />
                      <span className="toggle-slider"></span>
                    </label>
                  </div>
                </div>

                <div className="setting-card">
                  <div className="setting-info">
                    <h5>連絡先情報を表示</h5>
                    <p>
                      外部公開プロフィールにメールアドレスなどの連絡先情報を含めます。
                    </p>
                  </div>
                  <div className="setting-control">
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={currentSettings.show_contact_info}
                        onChange={(e) => updateSetting('show_contact_info', e.target.checked)}
                      />
                      <span className="toggle-slider"></span>
                    </label>
                  </div>
                </div>

                <div className="setting-card">
                  <div className="setting-info">
                    <h5>詳細な経験情報を表示</h5>
                    <p>
                      外部公開プロフィールに具体的な実績や成果の詳細を含めます。
                    </p>
                  </div>
                  <div className="setting-control">
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={currentSettings.show_detailed_experience}
                        onChange={(e) => updateSetting('show_detailed_experience', e.target.checked)}
                      />
                      <span className="toggle-slider"></span>
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="privacy-section">
            <h4>現在の設定状況</h4>
            <div className="status-overview">
              <div className="status-item">
                <div className="status-icon">
                  {currentSettings.is_publicly_visible ? '🌐' : '🏢'}
                </div>
                <div className="status-info">
                  <h5>プロフィール可視性</h5>
                  <p>
                    {currentSettings.is_publicly_visible 
                      ? '外部公開（製造業プラチナアドバイザリーで検索可能）' 
                      : '社内のみ（外部からは見えません）'
                    }
                  </p>
                </div>
              </div>

              <div className="status-item">
                <div className="status-icon">
                  {currentSettings.external_contact ? '📧' : '🚫'}
                </div>
                <div className="status-info">
                  <h5>外部連絡</h5>
                  <p>
                    {currentSettings.external_contact 
                      ? '外部リクルーターからの連絡を受け付けます' 
                      : '外部からの直接連絡は受け付けません'
                    }
                  </p>
                </div>
              </div>

              <div className="status-item">
                <div className="status-icon">
                  {currentSettings.show_contact_info ? '📞' : '🔒'}
                </div>
                <div className="status-info">
                  <h5>連絡先情報</h5>
                  <p>
                    {currentSettings.show_contact_info 
                      ? '連絡先情報が外部に表示されます' 
                      : '連絡先情報は非公開です'
                    }
                  </p>
                </div>
              </div>

              <div className="status-item">
                <div className="status-icon">
                  {currentSettings.show_detailed_experience ? '📋' : '📄'}
                </div>
                <div className="status-info">
                  <h5>経験情報の詳細度</h5>
                  <p>
                    {currentSettings.show_detailed_experience 
                      ? '詳細な実績・成果が外部に表示されます' 
                      : '基本的な経験情報のみ外部に表示されます'
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="privacy-section">
            <h4>重要な注意事項</h4>
            <div className="notice-card">
              <div className="notice-icon">⚠️</div>
              <div className="notice-content">
                <h5>プライバシー設定について</h5>
                <ul>
                  <li>設定変更は即座に反映され、外部プラットフォームからの可視性が変更されます</li>
                  <li>外部公開を無効にした場合、既存の外部連絡や応募には影響しません</li>
                  <li>社内での推薦・マッチング機能は、外部公開設定に関係なく利用できます</li>
                  <li>データの完全削除をご希望の場合は、システム管理者にお問い合わせください</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div className="privacy-actions">
          <button 
            onClick={savePrivacySettings} 
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '設定を保存中...' : 'プライバシー設定を保存'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PrivacySettings;