import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { profileService } from '../../services/profileService';
import { VeteranProfile, Skill, Experience, Preferences } from '../../types/profile';
import BusinessTitleGenerator from './BusinessTitleGenerator';
import PrivacySettings from './PrivacySettings';
import './ProfileManagement.css';

const ProfileManagement: React.FC = () => {
  const { user } = useAuth();
  const [profile, setProfile] = useState<VeteranProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'skills' | 'experience' | 'preferences' | 'business-title' | 'privacy'>('skills');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const loadProfile = async () => {
    if (!user) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await profileService.getProfile(user.user_id);
      setProfile(data);
    } catch (error) {
      setError('プロフィールの読み込みに失敗しました');
      console.error('Load profile error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const saveProfile = async (updatedProfile: Partial<VeteranProfile>) => {
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);
      const updated = await profileService.updateProfile(user!.user_id, updatedProfile);
      setProfile(updated);
      setHasUnsavedChanges(false);
      setSuccessMessage('プロフィールが正常に保存されました');
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      setError('プロフィールの保存に失敗しました');
      console.error('Save profile error:', error);
    } finally {
      setSaving(false);
    }
  };

  const addSkill = () => {
    const newSkill: Skill = {
      name: '',
      level: 'beginner',
      years: 0,
      certifications: []
    };
    
    const updatedProfile = {
      ...profile!,
      skills: [...(profile?.skills || []), newSkill]
    };
    setProfile(updatedProfile);
    setHasUnsavedChanges(true);
  };

  const updateSkill = (index: number, skill: Skill) => {
    const updatedSkills = [...(profile?.skills || [])];
    updatedSkills[index] = skill;
    
    const updatedProfile = {
      ...profile!,
      skills: updatedSkills
    };
    setProfile(updatedProfile);
    setHasUnsavedChanges(true);
  };

  const removeSkill = (index: number) => {
    if (window.confirm('このスキルを削除してもよろしいですか？')) {
      const updatedSkills = (profile?.skills || []).filter((_, i) => i !== index);
      
      const updatedProfile = {
        ...profile!,
        skills: updatedSkills
      };
      setProfile(updatedProfile);
      setHasUnsavedChanges(true);
    }
  };

  const addExperience = () => {
    const newExperience: Experience = {
      title: '',
      department: '',
      duration: 0,
      achievements: [],
      description: ''
    };
    
    const updatedProfile = {
      ...profile!,
      experiences: [...(profile?.experiences || []), newExperience]
    };
    setProfile(updatedProfile);
    setHasUnsavedChanges(true);
  };

  const updateExperience = (index: number, experience: Experience) => {
    const updatedExperiences = [...(profile?.experiences || [])];
    updatedExperiences[index] = experience;
    
    const updatedProfile = {
      ...profile!,
      experiences: updatedExperiences
    };
    setProfile(updatedProfile);
    setHasUnsavedChanges(true);
  };

  const removeExperience = (index: number) => {
    if (window.confirm('この経験を削除してもよろしいですか？')) {
      const updatedExperiences = (profile?.experiences || []).filter((_, i) => i !== index);
      
      const updatedProfile = {
        ...profile!,
        experiences: updatedExperiences
      };
      setProfile(updatedProfile);
      setHasUnsavedChanges(true);
    }
  };

  const updatePreferences = (preferences: Preferences) => {
    const updatedProfile = {
      ...profile!,
      preferences
    };
    setProfile(updatedProfile);
    setHasUnsavedChanges(true);
  };

  const renderSkillsTab = () => (
    <div className="tab-content">
      <div className="tab-header">
        <h3>スキル管理</h3>
        <button onClick={addSkill} className="btn btn-primary">
          スキルを追加
        </button>
      </div>

      <div className="skills-list">
        {(profile?.skills || []).map((skill, index) => (
          <div key={index} className="skill-card">
            <div className="skill-form">
              <div className="form-row">
                <div className="form-group">
                  <label>スキル名</label>
                  <input
                    type="text"
                    value={skill.name}
                    onChange={(e) => updateSkill(index, { ...skill, name: e.target.value })}
                    placeholder="例: React, Python, プロジェクト管理"
                  />
                </div>
                
                <div className="form-group">
                  <label>レベル</label>
                  <select
                    value={skill.level}
                    onChange={(e) => updateSkill(index, { ...skill, level: e.target.value as any })}
                  >
                    <option value="beginner">初級</option>
                    <option value="intermediate">中級</option>
                    <option value="advanced">上級</option>
                    <option value="expert">エキスパート</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>経験年数</label>
                  <input
                    type="number"
                    min="0"
                    value={skill.years}
                    onChange={(e) => updateSkill(index, { ...skill, years: parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>
              
              <div className="form-group">
                <label>資格・認定</label>
                <input
                  type="text"
                  value={skill.certifications.join(', ')}
                  onChange={(e) => updateSkill(index, { 
                    ...skill, 
                    certifications: e.target.value.split(',').map(cert => cert.trim()).filter(cert => cert)
                  })}
                  placeholder="資格をカンマ区切りで入力"
                />
              </div>
            </div>
            
            <button 
              onClick={() => removeSkill(index)} 
              className="btn btn-danger btn-small"
            >
              削除
            </button>
          </div>
        ))}
        
        {(profile?.skills || []).length === 0 && (
          <div className="empty-state">
            <p>まだスキルが登録されていません。「スキルを追加」ボタンから追加してください。</p>
          </div>
        )}
      </div>
    </div>
  );

  const renderExperienceTab = () => (
    <div className="tab-content">
      <div className="tab-header">
        <h3>経験管理</h3>
        <button onClick={addExperience} className="btn btn-primary">
          経験を追加
        </button>
      </div>

      <div className="experiences-list">
        {(profile?.experiences || []).map((experience, index) => (
          <div key={index} className="experience-card">
            <div className="experience-form">
              <div className="form-row">
                <div className="form-group">
                  <label>役職・タイトル</label>
                  <input
                    type="text"
                    value={experience.title}
                    onChange={(e) => updateExperience(index, { ...experience, title: e.target.value })}
                    placeholder="例: シニアエンジニア、プロジェクトマネージャー"
                  />
                </div>
                
                <div className="form-group">
                  <label>部署</label>
                  <input
                    type="text"
                    value={experience.department}
                    onChange={(e) => updateExperience(index, { ...experience, department: e.target.value })}
                    placeholder="例: 研究開発部、IT部"
                  />
                </div>
                
                <div className="form-group">
                  <label>期間（年）</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={experience.duration}
                    onChange={(e) => updateExperience(index, { ...experience, duration: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
              
              <div className="form-group">
                <label>説明</label>
                <textarea
                  value={experience.description || ''}
                  onChange={(e) => updateExperience(index, { ...experience, description: e.target.value })}
                  placeholder="この経験での役割や責任について説明してください"
                  rows={3}
                />
              </div>
              
              <div className="form-group">
                <label>主な成果・実績</label>
                <textarea
                  value={experience.achievements.join('\n')}
                  onChange={(e) => updateExperience(index, { 
                    ...experience, 
                    achievements: e.target.value.split('\n').filter(achievement => achievement.trim())
                  })}
                  placeholder="各行に一つずつ成果を入力してください"
                  rows={4}
                />
              </div>
            </div>
            
            <button 
              onClick={() => removeExperience(index)} 
              className="btn btn-danger btn-small"
            >
              削除
            </button>
          </div>
        ))}
        
        {(profile?.experiences || []).length === 0 && (
          <div className="empty-state">
            <p>まだ経験が登録されていません。「経験を追加」ボタンから追加してください。</p>
          </div>
        )}
      </div>
    </div>
  );

  const renderPreferencesTab = () => (
    <div className="tab-content">
      <h3>希望・設定</h3>
      
      <div className="preferences-form">
        <div className="form-group">
          <label>希望する役割</label>
          <textarea
            value={(profile?.preferences?.preferred_roles || []).join('\n')}
            onChange={(e) => updatePreferences({
              ...profile?.preferences!,
              preferred_roles: e.target.value.split('\n').filter(role => role.trim())
            })}
            placeholder="各行に一つずつ希望する役割を入力してください"
            rows={4}
          />
        </div>
        
        <div className="form-group">
          <label>働き方の希望</label>
          <select
            value={profile?.preferences?.work_style || 'flexible'}
            onChange={(e) => updatePreferences({
              ...profile?.preferences!,
              work_style: e.target.value as any
            })}
          >
            <option value="remote">リモートワーク</option>
            <option value="hybrid">ハイブリッド</option>
            <option value="onsite">オンサイト</option>
            <option value="flexible">柔軟</option>
          </select>
        </div>
        
        <div className="form-group">
          <label>希望勤務地</label>
          <textarea
            value={(profile?.preferences?.locations || []).join('\n')}
            onChange={(e) => updatePreferences({
              ...profile?.preferences!,
              locations: e.target.value.split('\n').filter(location => location.trim())
            })}
            placeholder="各行に一つずつ希望勤務地を入力してください"
            rows={3}
          />
        </div>
        
        <div className="form-group">
          <label>勤務形態の希望</label>
          <select
            value={profile?.preferences?.availability || 'full_time'}
            onChange={(e) => updatePreferences({
              ...profile?.preferences!,
              availability: e.target.value as any
            })}
          >
            <option value="full_time">フルタイム</option>
            <option value="part_time">パートタイム</option>
            <option value="consulting">コンサルティング</option>
            <option value="project_based">プロジェクトベース</option>
          </select>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="profile-management-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>プロフィールを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="profile-management-container">
        <div className="error-state">
          <h2>エラーが発生しました</h2>
          <p>{error}</p>
          <button onClick={loadProfile} className="btn btn-primary">
            再試行
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-management-container">
      <div className="profile-header">
        <h1>プロフィール管理</h1>
        <p>あなたの詳細プロフィールを編集・管理できます</p>
        {hasUnsavedChanges && (
          <div className="unsaved-changes-notice">
            <span>⚠️ 未保存の変更があります</span>
          </div>
        )}
      </div>

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

      <div className="profile-tabs">
        <button 
          className={`tab-button ${activeTab === 'skills' ? 'active' : ''}`}
          onClick={() => setActiveTab('skills')}
        >
          スキル
        </button>
        <button 
          className={`tab-button ${activeTab === 'experience' ? 'active' : ''}`}
          onClick={() => setActiveTab('experience')}
        >
          経験
        </button>
        <button 
          className={`tab-button ${activeTab === 'preferences' ? 'active' : ''}`}
          onClick={() => setActiveTab('preferences')}
        >
          希望・設定
        </button>
        <button 
          className={`tab-button ${activeTab === 'business-title' ? 'active' : ''}`}
          onClick={() => setActiveTab('business-title')}
        >
          ビジネスタイトル
        </button>
        <button 
          className={`tab-button ${activeTab === 'privacy' ? 'active' : ''}`}
          onClick={() => setActiveTab('privacy')}
        >
          プライバシー設定
        </button>
      </div>

      <div className="profile-content">
        {activeTab === 'skills' && renderSkillsTab()}
        {activeTab === 'experience' && renderExperienceTab()}
        {activeTab === 'preferences' && renderPreferencesTab()}
        {activeTab === 'business-title' && (
          <BusinessTitleGenerator 
            profile={profile} 
            onUpdate={(updatedProfile) => setProfile(updatedProfile)}
          />
        )}
        {activeTab === 'privacy' && (
          <PrivacySettings 
            profile={profile} 
            onUpdate={(updatedProfile) => setProfile(updatedProfile)}
          />
        )}
      </div>

      <div className="profile-actions">
        <button 
          onClick={() => saveProfile(profile!)} 
          className="btn btn-primary"
          disabled={saving}
        >
          {saving ? '保存中...' : 'プロフィールを保存'}
        </button>
      </div>
    </div>
  );
};

export default ProfileManagement;