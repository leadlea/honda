import React, { useState } from 'react';
import { PublicVeteranProfile } from '../../types/public';
import ContactForm from './ContactForm';
import { termMappingService } from '../../services/termMappingService';
import './VeteranProfileModal.css';

interface VeteranProfileModalProps {
  profile: PublicVeteranProfile;
  onClose: () => void;
}

const VeteranProfileModal: React.FC<VeteranProfileModalProps> = ({ profile, onClose }) => {
  const [showContactForm, setShowContactForm] = useState(false);

  const getExperienceYears = () => {
    return profile.experiences.reduce((total, exp) => total + exp.duration, 0);
  };

  const getSkillLevel = (level: string) => {
    const levels: { [key: string]: string } = {
      'beginner': '初級',
      'intermediate': '中級',
      'advanced': '上級',
      'expert': 'エキスパート'
    };
    return levels[level] || level;
  };

  const getAvailabilityLabel = (availability: string) => {
    const labels: { [key: string]: string } = {
      'full_time': 'フルタイム',
      'part_time': 'パートタイム',
      'consulting': 'コンサルティング',
      'project_based': 'プロジェクトベース'
    };
    return labels[availability] || availability;
  };

  const getWorkStyleLabel = (workStyle: string) => {
    const labels: { [key: string]: string } = {
      'remote': 'リモート',
      'hybrid': 'ハイブリッド',
      'onsite': 'オンサイト',
      'flexible': '柔軟'
    };
    return labels[workStyle] || workStyle;
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleContactSuccess = () => {
    setShowContactForm(false);
    // Show success message or notification
  };

  const experienceYears = getExperienceYears();

  return (
    <div className="veteran-profile-modal-backdrop" onClick={handleBackdropClick}>
      <div className="veteran-profile-modal">
        <div className="modal-header">
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-content">
          <div className="profile-header">
            <div className="profile-avatar-large">
              <span className="avatar-initial-large">
                {profile.business_title.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="profile-info">
              <h1 className="business-title-large">{profile.business_title}</h1>
              <div className="profile-meta">
                <span className="experience-years">{experienceYears}年の経験</span>
                <span className="last-updated">
                  更新: {new Date(profile.last_updated).toLocaleDateString('ja-JP')}
                </span>
              </div>
            </div>
            <div className="profile-actions">
              <button 
                className="contact-btn"
                onClick={() => setShowContactForm(true)}
              >
                連絡する
              </button>
            </div>
          </div>

          <div className="profile-summary-section">
            <h2>{termMappingService.getLocalizedTerm('skill_portfolio')}概要</h2>
            <p className="profile-summary-text">{profile.summary}</p>
          </div>

          <div className="profile-details">
            <div className="details-column">
              <div className="skills-section-detailed">
                <h2>スキル・専門分野</h2>
                <div className="skills-grid">
                  {profile.skills.map((skill, index) => (
                    <div key={index} className="skill-item-detailed">
                      <div className="skill-header">
                        <span className="skill-name">{skill.name}</span>
                        <span className="skill-level">{getSkillLevel(skill.level)}</span>
                      </div>
                      <div className="skill-experience">
                        {skill.years}年の経験
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="preferences-section-detailed">
                <h2>希望条件</h2>
                <div className="preferences-grid">
                  <div className="preference-group">
                    <h3>勤務形態</h3>
                    <p>{getAvailabilityLabel(profile.preferences.availability)}</p>
                  </div>
                  <div className="preference-group">
                    <h3>働き方</h3>
                    <p>{getWorkStyleLabel(profile.preferences.work_style)}</p>
                  </div>
                  {profile.preferences.locations.length > 0 && (
                    <div className="preference-group">
                      <h3>勤務地</h3>
                      <p>{profile.preferences.locations.join(', ')}</p>
                    </div>
                  )}
                  {profile.preferences.preferred_roles.length > 0 && (
                    <div className="preference-group">
                      <h3>希望職種</h3>
                      <div className="preferred-roles">
                        {profile.preferences.preferred_roles.map((role, index) => (
                          <span key={index} className="role-tag">{role}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="details-column">
              <div className="experience-section-detailed">
                <h2>職歴・経験</h2>
                <div className="experience-timeline">
                  {profile.experiences.map((exp, index) => (
                    <div key={index} className="experience-item-detailed">
                      <div className="experience-header">
                        <h3 className="experience-title">{exp.title}</h3>
                        <span className="experience-duration">{exp.duration}年</span>
                      </div>
                      <div className="experience-department">{exp.department}</div>
                      {exp.achievements.length > 0 && (
                        <div className="experience-achievements">
                          <h4>主な成果</h4>
                          <ul>
                            {exp.achievements.map((achievement, achIndex) => (
                              <li key={achIndex}>{achievement}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {showContactForm && (
          <ContactForm
            profile={profile}
            onClose={() => setShowContactForm(false)}
            onSuccess={handleContactSuccess}
          />
        )}
      </div>
    </div>
  );
};

export default VeteranProfileModal;