import React, { useState } from 'react';
import { profileService } from '../../services/profileService';
import { VeteranProfile, BusinessTitleSuggestion } from '../../types/profile';
import { useAuth } from '../../contexts/AuthContext';
import './BusinessTitleGenerator.css';

interface BusinessTitleGeneratorProps {
  profile: VeteranProfile | null;
  onUpdate: (profile: VeteranProfile) => void;
}

const BusinessTitleGenerator: React.FC<BusinessTitleGeneratorProps> = ({ profile, onUpdate }) => {
  const { user } = useAuth();
  const [suggestions, setSuggestions] = useState<BusinessTitleSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customTitle, setCustomTitle] = useState(profile?.business_title || '');
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState<number | null>(null);

  const generateTitles = async (regenerate: boolean = false) => {
    if (!user) return;

    try {
      setLoading(true);
      setError(null);
      
      const titleSuggestions = regenerate 
        ? await profileService.regenerateBusinessTitle(user.user_id)
        : await profileService.generateBusinessTitle(user.user_id);
        
      setSuggestions(titleSuggestions);
      setSelectedSuggestionIndex(null); // 新しい候補が生成されたら選択をリセット
    } catch (error) {
      setError(regenerate ? 'ビジネスタイトルの再生成に失敗しました' : 'ビジネスタイトルの生成に失敗しました');
      console.error('Generate business title error:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectTitle = async (title: string, index: number) => {
    if (!user) return;

    try {
      setLoading(true);
      setError(null);
      
      // バックエンドにタイトル選択を送信
      await profileService.selectBusinessTitle(user.user_id, title);
      
      setCustomTitle(title);
      setSelectedSuggestionIndex(index);
      
      if (profile) {
        const updatedProfile = {
          ...profile,
          business_title: title
        };
        onUpdate(updatedProfile);
      }
    } catch (error) {
      setError('ビジネスタイトルの選択に失敗しました');
      console.error('Select business title error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const title = e.target.value;
    setCustomTitle(title);
    if (profile) {
      const updatedProfile = {
        ...profile,
        business_title: title
      };
      onUpdate(updatedProfile);
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'high';
    if (score >= 0.6) return 'medium';
    return 'low';
  };

  const getConfidenceText = (score: number) => {
    if (score >= 0.8) return '高い適合度';
    if (score >= 0.6) return '中程度の適合度';
    return '低い適合度';
  };

  return (
    <div className="business-title-generator">
      <div className="tab-content">
        <h3>ビジネスタイトル生成</h3>
        <p className="description">
          あなたのAIスキルと経験に基づいて、AIがユニークなビジネスタイトルを生成します。
        </p>

        <div className="current-title-section">
          <h4>現在のビジネスタイトル</h4>
          <div className="title-input-group">
            <input
              type="text"
              value={customTitle}
              onChange={handleCustomTitleChange}
              placeholder="ビジネスタイトルを入力してください"
              className="title-input"
            />
            <button 
              onClick={() => generateTitles(false)} 
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'AI生成中...' : 'AIで生成'}
            </button>
          </div>
        </div>

        {error && (
          <div className="error-message">
            <p>{error}</p>
          </div>
        )}

        {loading && (
          <div className="loading-section">
            <div className="loading-spinner"></div>
            <p>AIがあなたのAIスキルポートフォリオを分析してビジネスタイトルを生成しています...</p>
          </div>
        )}

        {suggestions.length > 0 && (
          <div className="suggestions-section">
            <div className="suggestions-header">
              <h4>AI生成されたタイトル候補</h4>
              <button 
                onClick={() => generateTitles(true)} 
                className="btn btn-secondary"
                disabled={loading}
              >
                {loading ? '再生成中...' : '再生成'}
              </button>
            </div>
            <div className="suggestions-list">
              {suggestions.map((suggestion, index) => (
                <div key={index} className="suggestion-card">
                  <div className="suggestion-header">
                    <h5 className="suggestion-title">{suggestion.title}</h5>
                    <div className={`confidence-badge ${getConfidenceColor(suggestion.confidence_score)}`}>
                      {getConfidenceText(suggestion.confidence_score)}
                    </div>
                  </div>
                  
                  <p className="suggestion-reasoning">{suggestion.reasoning}</p>
                  
                  <div className="suggestion-actions">
                    <button 
                      onClick={() => selectTitle(suggestion.title, index)}
                      className={`btn ${selectedSuggestionIndex === index ? 'btn-primary' : 'btn-secondary'}`}
                    >
                      {selectedSuggestionIndex === index ? '選択済み' : 'このタイトルを選択'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && suggestions.length === 0 && (
          <div className="empty-suggestions">
            <div className="empty-icon">🎯</div>
            <h4>タイトル候補を生成しましょう</h4>
            <p>
              「AIで生成」ボタンをクリックして、あなたのAIスキルと経験に基づいた
              ユニークなビジネスタイトルを生成してください。
            </p>
            <div className="tips">
              <h5>より良いタイトル生成のために：</h5>
              <ul>
                <li>AIスキルセクションに詳細なスキル情報を入力</li>
                <li>経験セクションに具体的な実績を記載</li>
                <li>希望・設定で将来の方向性を明確化</li>
              </ul>
            </div>
            
            {(!profile?.skills || profile.skills.length === 0) && (
              <div className="profile-warning">
                <span>⚠️ AIスキル情報が不足しています。より良いタイトル生成のため、まずAIスキルを追加してください。</span>
              </div>
            )}
          </div>
        )}

        <div className="title-preview">
          <h4>プレビュー</h4>
          <div className="preview-card">
            <div className="preview-title">
              {customTitle || 'ビジネスタイトルが設定されていません'}
            </div>
            <div className="preview-name">{user?.name}</div>
            <div className="preview-department">{user?.department}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BusinessTitleGenerator;