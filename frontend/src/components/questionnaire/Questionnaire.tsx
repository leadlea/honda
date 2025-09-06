import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { profileService } from '../../services/profileService';
import { Questionnaire as QuestionnaireType, Question, QuestionnaireResponse } from '../../types/profile';
import './Questionnaire.css';

const Questionnaire: React.FC = () => {
  const { user } = useAuth();
  const [questionnaire, setQuestionnaire] = useState<QuestionnaireType | null>(null);
  const [responses, setResponses] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [showHistory, setShowHistory] = useState(false);
  const [questionnaireHistory, setQuestionnaireHistory] = useState<QuestionnaireType[]>([]);

  useEffect(() => {
    if (user) {
      loadQuestionnaire();
      loadQuestionnaireHistory();
    }
  }, [user]);

  const loadQuestionnaire = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await profileService.getQuestionnaire(user!.user_id);
      
      if (data) {
        setQuestionnaire(data);
        // Load existing responses if any
        const existingResponses: Record<string, any> = {};
        data.responses.forEach(response => {
          existingResponses[response.question_id] = response.answer;
        });
        setResponses(existingResponses);
      }
    } catch (error) {
      setError('問診の読み込みに失敗しました');
      console.error('Load questionnaire error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadQuestionnaireHistory = async () => {
    try {
      const history = await profileService.getQuestionnaireHistory(user!.user_id);
      setQuestionnaireHistory(history);
    } catch (error) {
      console.error('Load questionnaire history error:', error);
    }
  };

  const handleResponseChange = (questionId: string, value: any) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      setError(null);

      const responseArray = Object.entries(responses).map(([questionId, answer]) => ({
        question_id: questionId,
        answer,
        answered_at: new Date().toISOString()
      }));

      await profileService.submitQuestionnaire(user!.user_id, responseArray);
      
      // Reload questionnaire to get updated status
      await loadQuestionnaire();
      
      alert('問診の回答が正常に送信されました！');
    } catch (error) {
      setError('問診の送信に失敗しました');
      console.error('Submit questionnaire error:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegenerate = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await profileService.regenerateQuestionnaire(user!.user_id);
      setQuestionnaire(data);
      setResponses({});
      setCurrentQuestionIndex(0);
    } catch (error) {
      setError('問診の再生成に失敗しました');
      console.error('Regenerate questionnaire error:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderQuestion = (question: Question) => {
    const value = responses[question.id] || '';

    switch (question.type) {
      case 'text':
        return (
          <textarea
            value={value}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
            placeholder="回答を入力してください..."
            rows={4}
            className="question-textarea"
          />
        );

      case 'multiple_choice':
        return (
          <div className="question-options">
            {question.options?.map((option, index) => (
              <label key={index} className="option-label">
                <input
                  type="radio"
                  name={question.id}
                  value={option}
                  checked={value === option}
                  onChange={(e) => handleResponseChange(question.id, e.target.value)}
                />
                <span>{option}</span>
              </label>
            ))}
          </div>
        );

      case 'rating':
        return (
          <div className="rating-container">
            <div className="rating-scale">
              {[1, 2, 3, 4, 5].map(rating => (
                <label key={rating} className="rating-label">
                  <input
                    type="radio"
                    name={question.id}
                    value={rating}
                    checked={value === rating}
                    onChange={(e) => handleResponseChange(question.id, parseInt(e.target.value))}
                  />
                  <span className="rating-number">{rating}</span>
                </label>
              ))}
            </div>
            <div className="rating-labels">
              <span>低い</span>
              <span>高い</span>
            </div>
          </div>
        );

      case 'boolean':
        return (
          <div className="boolean-options">
            <label className="option-label">
              <input
                type="radio"
                name={question.id}
                value="true"
                checked={value === true}
                onChange={() => handleResponseChange(question.id, true)}
              />
              <span>はい</span>
            </label>
            <label className="option-label">
              <input
                type="radio"
                name={question.id}
                value="false"
                checked={value === false}
                onChange={() => handleResponseChange(question.id, false)}
              />
              <span>いいえ</span>
            </label>
          </div>
        );

      default:
        return null;
    }
  };

  const getProgress = () => {
    if (!questionnaire) return 0;
    const answeredQuestions = Object.keys(responses).length;
    return (answeredQuestions / questionnaire.questions.length) * 100;
  };

  const canSubmit = () => {
    if (!questionnaire) return false;
    const requiredQuestions = questionnaire.questions.filter(q => q.required);
    return requiredQuestions.every(q => responses[q.id] !== undefined && responses[q.id] !== '');
  };

  if (loading) {
    return (
      <div className="questionnaire-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>AI問診を読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="questionnaire-container">
        <div className="error-state">
          <h2>エラーが発生しました</h2>
          <p>{error}</p>
          <button onClick={loadQuestionnaire} className="btn btn-primary">
            再試行
          </button>
        </div>
      </div>
    );
  }

  if (!questionnaire) {
    return (
      <div className="questionnaire-container">
        <div className="empty-state">
          <h2>問診が見つかりません</h2>
          <p>新しい問診を生成しますか？</p>
          <button onClick={handleRegenerate} className="btn btn-primary">
            問診を生成
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="questionnaire-container">
      <div className="questionnaire-header">
        <h1>AI生成問診</h1>
        <p>あなたのスキルと興味を評価するための個人向け問診です</p>
        
        <div className="progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${getProgress()}%` }}
            ></div>
          </div>
          <span className="progress-text">
            {Object.keys(responses).length} / {questionnaire.questions.length} 質問回答済み
          </span>
        </div>
      </div>

      <div className="questionnaire-content">
        {questionnaire.questions.map((question, index) => (
          <div key={question.id} className="question-card">
            <div className="question-header">
              <span className="question-number">質問 {index + 1}</span>
              <span className={`question-category ${question.category}`}>
                {question.category === 'skills' && 'スキル'}
                {question.category === 'experience' && '経験'}
                {question.category === 'preferences' && '希望'}
                {question.category === 'goals' && '目標'}
              </span>
              {question.required && <span className="required-indicator">必須</span>}
            </div>
            
            <h3 className="question-text">{question.text}</h3>
            
            <div className="question-input">
              {renderQuestion(question)}
            </div>
          </div>
        ))}
      </div>

      <div className="questionnaire-actions">
        <button 
          onClick={() => setShowHistory(!showHistory)} 
          className="btn btn-outline"
          disabled={submitting}
        >
          {showHistory ? '問診を隠す' : '過去の問診を見る'}
        </button>
        
        <button 
          onClick={handleRegenerate} 
          className="btn btn-secondary"
          disabled={submitting}
        >
          問診を再生成
        </button>
        
        <button 
          onClick={handleSubmit} 
          className="btn btn-primary"
          disabled={!canSubmit() || submitting}
        >
          {submitting ? '送信中...' : '回答を送信'}
        </button>
      </div>

      {questionnaire.status === 'completed' && (
        <div className="completion-notice">
          <h3>問診完了</h3>
          <p>回答ありがとうございました。プロフィールが更新されました。</p>
        </div>
      )}

      {showHistory && questionnaireHistory.length > 0 && (
        <div className="questionnaire-history">
          <h3>過去の問診履歴</h3>
          <div className="history-list">
            {questionnaireHistory.map((historyItem, index) => (
              <div key={historyItem.questionnaire_id} className="history-item">
                <div className="history-header">
                  <h4>問診 #{index + 1}</h4>
                  <div className="history-meta">
                    <span className={`status-badge ${historyItem.status}`}>
                      {historyItem.status === 'completed' && '完了'}
                      {historyItem.status === 'in_progress' && '進行中'}
                      {historyItem.status === 'generated' && '生成済み'}
                    </span>
                    <span className="history-date">
                      {new Date(historyItem.generated_at).toLocaleDateString('ja-JP')}
                    </span>
                  </div>
                </div>
                <div className="history-stats">
                  <span>質問数: {historyItem.questions.length}</span>
                  <span>回答数: {historyItem.responses.length}</span>
                  {historyItem.completed_at && (
                    <span>完了日: {new Date(historyItem.completed_at).toLocaleDateString('ja-JP')}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Questionnaire;