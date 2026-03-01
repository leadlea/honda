import React, { useState } from 'react';
import { PublicVeteranProfile } from '../../types/public';
import { PublicSearchService } from '../../services/publicSearchService';
import './ContactForm.css';

interface ContactFormProps {
  profile: PublicVeteranProfile;
  onClose: () => void;
  onSuccess: () => void;
}

interface FormData {
  recruiter_name: string;
  recruiter_email: string;
  company: string;
  position_title: string;
  message: string;
}

const ContactForm: React.FC<ContactFormProps> = ({ profile, onClose, onSuccess }) => {
  const [formData, setFormData] = useState<FormData>({
    recruiter_name: '',
    recruiter_email: '',
    company: '',
    position_title: '',
    message: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError(null);
  };

  const validateForm = (): boolean => {
    if (!formData.recruiter_name.trim()) {
      setError('お名前を入力してください。');
      return false;
    }
    if (!formData.recruiter_email.trim()) {
      setError('メールアドレスを入力してください。');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.recruiter_email)) {
      setError('有効なメールアドレスを入力してください。');
      return false;
    }
    if (!formData.company.trim()) {
      setError('会社名を入力してください。');
      return false;
    }
    if (!formData.position_title.trim()) {
      setError('職種・ポジション名を入力してください。');
      return false;
    }
    if (!formData.message.trim()) {
      setError('メッセージを入力してください。');
      return false;
    }
    if (formData.message.trim().length < 20) {
      setError('メッセージは20文字以上で入力してください。');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await PublicSearchService.sendContactRequest(profile.profile_id, formData);
      setSuccess(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 2000);
    } catch (error) {
      setError('連絡の送信に失敗しました。もう一度お試しください。');
      console.error('Contact form error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (success) {
    return (
      <div className="contact-form-backdrop" onClick={handleBackdropClick}>
        <div className="contact-form-modal">
          <div className="success-message">
            <div className="success-icon">✓</div>
            <h2>連絡を送信しました</h2>
            <p>
              {profile.business_title}さんに連絡を送信しました。<br />
              返信をお待ちください。
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="contact-form-backdrop" onClick={handleBackdropClick}>
      <div className="contact-form-modal">
        <div className="contact-form-header">
          <h2>連絡する</h2>
          <p>{profile.business_title}さんに連絡を送信します</p>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit} className="contact-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="recruiter_name">お名前 *</label>
              <input
                type="text"
                id="recruiter_name"
                name="recruiter_name"
                value={formData.recruiter_name}
                onChange={handleInputChange}
                placeholder="山田 太郎"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="recruiter_email">メールアドレス *</label>
              <input
                type="email"
                id="recruiter_email"
                name="recruiter_email"
                value={formData.recruiter_email}
                onChange={handleInputChange}
                placeholder="yamada@example.com"
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="company">会社名 *</label>
              <input
                type="text"
                id="company"
                name="company"
                value={formData.company}
                onChange={handleInputChange}
                placeholder="株式会社サンプル"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="position_title">職種・ポジション名 *</label>
              <input
                type="text"
                id="position_title"
                name="position_title"
                value={formData.position_title}
                onChange={handleInputChange}
                placeholder="シニアエンジニア"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="message">メッセージ *</label>
            <textarea
              id="message"
              name="message"
              value={formData.message}
              onChange={handleInputChange}
              placeholder="こんにちは。弊社では現在、あなたのご経験を活かせるポジションを募集しております。詳細についてお話しできればと思います。ご都合の良い時間があれば、お聞かせください。"
              rows={6}
              required
            />
            <div className="character-count">
              {formData.message.length}/500文字
            </div>
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <div className="form-actions">
            <button type="button" className="cancel-btn" onClick={onClose}>
              キャンセル
            </button>
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? '送信中...' : '連絡を送信'}
            </button>
          </div>
        </form>

        <div className="contact-disclaimer">
          <p>
            <strong>注意:</strong> この連絡は社内AI人材候補の方に直接送信されます。
            適切で専門的な内容でお送りください。
          </p>
        </div>
      </div>
    </div>
  );
};

export default ContactForm;