import React from 'react';
import { PublicVeteranProfile } from '../../types/public';
import { termMappingService } from '../../services/termMappingService';
import './VeteranSearchCard.css';

interface VeteranSearchCardProps {
  profile: PublicVeteranProfile;
  onSelect: (profile: PublicVeteranProfile) => void;
}

const VeteranSearchCard: React.FC<VeteranSearchCardProps> = ({ profile, onSelect }) => {
  const getExperienceYears = () => {
    return profile.experiences.reduce((total, exp) => total + exp.duration, 0);
  };

  const getTopSkills = () => {
    return profile.skills
      .sort((a, b) => b.years - a.years)
      .slice(0, 4)
      .map(skill => skill.name);
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

  const topSkills = getTopSkills();
  const experienceYears = getExperienceYears();

  return (
    <div className="veteran-search-card" onClick={() => onSelect(profile)}>
      <div className="card-header">
        <div className="profile-avatar">
          <span className="avatar-initial">
            {profile.business_title.charAt(0).toUpperCase()}
          </span>
        </div>
        <div className="profile-basic">
          <h3 className="business-title">{profile.business_title}</h3>
          <div className="experience-badge">
            {experienceYears}年の経験
          </div>
        </div>
      </div>

      <div className="card-content">
        <div className="summary-section">
          <p className="profile-summary">{profile.summary}</p>
        </div>

        <div className="skills-section">
          <h4>主要スキル</h4>
          <div className="skills-tags">
            {topSkills.map((skill, index) => (
              <span key={index} className="skill-tag">
                {skill}
              </span>
            ))}
            {profile.skills.length > 4 && (
              <span className="more-skills">
                +{profile.skills.length - 4}個
              </span>
            )}
          </div>
        </div>

        <div className="preferences-section">
          <div className="preference-item">
            <span className="preference-label">勤務形態:</span>
            <span className="preference-value">
              {getAvailabilityLabel(profile.preferences.availability)}
            </span>
          </div>
          <div className="preference-item">
            <span className="preference-label">働き方:</span>
            <span className="preference-value">
              {getWorkStyleLabel(profile.preferences.work_style)}
            </span>
          </div>
          {profile.preferences.locations.length > 0 && (
            <div className="preference-item">
              <span className="preference-label">勤務地:</span>
              <span className="preference-value">
                {profile.preferences.locations.slice(0, 2).join(', ')}
                {profile.preferences.locations.length > 2 && ' など'}
              </span>
            </div>
          )}
        </div>

        <div className="recent-experience">
          <h4>最近の経験</h4>
          {profile.experiences.slice(0, 2).map((exp, index) => (
            <div key={index} className="experience-item">
              <div className="experience-title">{exp.title}</div>
              <div className="experience-details">
                {exp.department} • {exp.duration}年
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card-footer">
        <button className="view-profile-btn">
          詳細{termMappingService.getLocalizedTerm('skill_portfolio')}を見る
        </button>
        <div className="last-updated">
          更新: {new Date(profile.last_updated).toLocaleDateString('ja-JP')}
        </div>
      </div>
    </div>
  );
};

export default VeteranSearchCard;