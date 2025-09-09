import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { profileService } from '../../services/profileService';
import { Questionnaire as QuestionnaireType, Question } from '../../types/profile';
import './Questionnaire.css';

const Questionnaire: React.FC = () => {
  const { user } = useAuth();

  // サーバーが返す形に合わせて、最低限の型ガードを入れた状態管理
  const [questionnaire, setQuestionnaire] = useState<QuestionnaireType | null>(null);
  const [responses, setResponses] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [questionnaireHistory, setQuestionnaireHistory] = useState<any[]>([]);

  // ---- API 呼び出し ----
  const loadQuestionnaire = useCallback(async () => {
    if (!user) return;
    try {
      setLoading(true);
      setError(null);

      const data = await profileService.getQuestionnaire(user.user_id);

      if (data && typeof data === 'object') {
        // サーバーは { questionnaire: { ... } } ではなく、サービス側で中身を返す想定
        // ここでは data が QuestionnaireType であることを前提に安全に扱う
        setQuestionnaire({
          ...data,
          questions: Array.isArray((data as any).questions) ? (data as any).questions : [],
          responses: Array.isArray((data as any).responses) ? (data as any).responses : [],
        } as QuestionnaireType);

        // 既存回答を state へ
        const existing: Record<string, any> = {};
        const respArray: any[] = Array.isArray((data as any).responses) ? (data as any).responses : [];
        respArray.forEach(r => {
          if (r && typeof r === 'object' && r.question_id) {
            existing[r.question_id] = r.answer;
          }
        });
        setResponses(existing);
      } else {
        setQuestionnaire(null);
        setResponses({});
      }
    } catch (e) {
      console.error('Load questionnaire error:', e);
      setError('問診の読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  }, [user]);

  const loadQuestionnaireHistory = useCallback(async () => {
    if (!user) return;
    try {
      const history = await profileService.getQuestionnaireHistory(user.user_id);
      setQuestionnaireHistory(Array.isArray(history) ? history : []);
    } catch (e) {
      console.error('Load questionnaire history error:', e);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      loadQuestionnaire();
      loadQuestionnaireHistory();
    }
  }, [user, loadQuestionnaire, loadQuestionnaireHistory]);

  // ---- UI ハンドラ ----
  const handleResponseChange = (questionId: string, value: any) => {
    setResponses(prev => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = async () => {
    if (!user || !questionnaire) return;
    try {
      setSubmitting(true);
      setError(null);

      const responseArray = Object.entries(responses).map(([questionId, answer]) => ({
        question_id: questionId,
        answer,
        answered_at: new Date().toISOString(),
      }));

      // ★ questionnaire_id を必ず送る
      await profileService.submitQuestionnaire(user.user_id, responseArray, questionnaire.questionnaire_id);

      await loadQuestionnaire();
      alert('問診の回答が正常に送信されました！');
    } catch (e) {
      console.error('Submit questionnaire error:', e);
      setError('問診の送信に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegenerate = async () => {
    if (!user) return;
    try {
      setLoading(true);
      setError(null);
      const data = await profileService.regenerateQuestionnaire(user.user_id);
      if (data) {
        setQuestionnaire({
          ...data,
          questions: Array.isArray((data as any).questions) ? (data as any).questions : [],
          responses: [],
        } as QuestionnaireType);
        setResponses({});
      }
    } catch (e) {
      console.error('Regenerate questionnaire error:', e);
      setError('問診の再生成に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // ---- 表示用ユーティリティ ----
  const renderQuestion = (question: Question) => {
    const value = responses[question.id] ?? '';

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
            {(question.options ?? []).map((option, idx) => (
              <label key={idx} className="option-label">
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
              {[1, 2, 3, 4, 5].map(r => (
                <label key={r} className="rating-label">
                  <input
                    type="radio"
                    name={question.id}
                    value={r}
                    checked={value === r}
                    onChange={(e) => handleResponseChange(question.id, parseInt(e.target.value))}
                  />
                  <span className="rating-number">{r}</span>
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

  const totalQuestions = (questionnaire?.questions ?? []).length;
  const answeredCount = Object.keys(responses).length;
  const progressPct = totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;

  const canSubmit = () => {
    if (!questionnaire) return false;
    const required = (questionnaire.questions ?? []).filter((q) => q.required);
    return required.every(q => responses[q.id] !== undefined && responses[q.id] !== '');
  };

  // ---- 画面描画 ----
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
          <button onClick={loadQuestionnaire} className="btn btn-primary">再試行</button>
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
          <button onClick={handleRegenerate} className="btn btn-primary">問診を生成</button>
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
            <div className="progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <span className="progress-text">
            {answeredCount} / {totalQuestions} 質問回答済み
          </span>
        </div>
      </div>

      <div className="questionnaire-content">
        {(questionnaire.questions ?? []).map((question, index) => (
          <div key={question.id ?? index} className="question-card">
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
            <div className="question-input">{renderQuestion(question)}</div>
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

        <button onClick={handleRegenerate} className="btn btn-secondary" disabled={submitting}>
          問診を再生成
        </button>

        <button onClick={handleSubmit} className="btn btn-primary" disabled={!canSubmit() || submitting}>
          {submitting ? '送信中...' : '回答を送信'}
        </button>
      </div>

      {questionnaire.status === 'completed' && (
        <div className="completion-notice">
          <h3>問診完了</h3>
          <p>回答ありがとうございました。プロフィールが更新されました。</p>
        </div>
      )}

      {showHistory && (questionnaireHistory?.length ?? 0) > 0 && (
        <div className="questionnaire-history">
          <h3>過去の問診履歴</h3>
          <div className="history-list">
            {questionnaireHistory.map((h, idx) => (
              <div key={h.questionnaire_id ?? idx} className="history-item">
                <div className="history-header">
                  <h4>問診 #{idx + 1}</h4>
                  <div className="history-meta">
                    <span className={`status-badge ${h.status}`}>{h.status === 'completed' ? '完了' : h.status === 'in_progress' ? '進行中' : '生成済み'}</span>
                    <span className="history-date">
                      {h.generated_at ? new Date(h.generated_at).toLocaleDateString('ja-JP') :
                       h.created_at ? new Date(h.created_at).toLocaleDateString('ja-JP') : ''}
                    </span>
                  </div>
                </div>
                <div className="history-stats">
                  <span>質問数: {(h.questions?.length ?? 0)}</span>
                  <span>回答数: {(h.responses?.length ?? 0)}</span>
                  {h.completed_at && (
                    <span>完了日: {new Date(h.completed_at).toLocaleDateString('ja-JP')}</span>
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
