import React, { useState, useEffect } from 'react';
import { SearchFilters, SkillCategory } from '../../types/public';
import './SearchFiltersPanel.css';

interface SearchFiltersPanelProps {
  filters: SearchFilters;
  skillCategories: SkillCategory[];
  onFiltersChange: (filters: SearchFilters) => void;
}

const SearchFiltersPanel: React.FC<SearchFiltersPanelProps> = ({
  filters,
  skillCategories,
  onFiltersChange,
}) => {
  const [localFilters, setLocalFilters] = useState<SearchFilters>(filters);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleSkillToggle = (skill: string) => {
    const currentSkills = localFilters.skills || [];
    const newSkills = currentSkills.includes(skill)
      ? currentSkills.filter(s => s !== skill)
      : [...currentSkills, skill];
    
    handleFilterChange('skills', newSkills.length > 0 ? newSkills : undefined);
  };

  const handleLocationToggle = (location: string) => {
    const currentLocations = localFilters.locations || [];
    const newLocations = currentLocations.includes(location)
      ? currentLocations.filter(l => l !== location)
      : [...currentLocations, location];
    
    handleFilterChange('locations', newLocations.length > 0 ? newLocations : undefined);
  };

  const handleAvailabilityToggle = (availability: string) => {
    const currentAvailability = localFilters.availability || [];
    const newAvailability = currentAvailability.includes(availability as any)
      ? currentAvailability.filter(a => a !== availability)
      : [...currentAvailability, availability as any];
    
    handleFilterChange('availability', newAvailability.length > 0 ? newAvailability : undefined);
  };

  const handleWorkStyleToggle = (workStyle: string) => {
    const currentWorkStyle = localFilters.work_style || [];
    const newWorkStyle = currentWorkStyle.includes(workStyle as any)
      ? currentWorkStyle.filter(w => w !== workStyle)
      : [...currentWorkStyle, workStyle as any];
    
    handleFilterChange('work_style', newWorkStyle.length > 0 ? newWorkStyle : undefined);
  };

  const handleExperienceChange = (type: 'min' | 'max', value: string) => {
    const numValue = parseInt(value) || 0;
    const currentRange = localFilters.experience_years || { min: 0, max: 50 };
    const newRange = { ...currentRange, [type]: numValue };
    
    if (newRange.min === 0 && newRange.max === 50) {
      handleFilterChange('experience_years', undefined);
    } else {
      handleFilterChange('experience_years', newRange);
    }
  };

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const clearAllFilters = () => {
    setLocalFilters({});
    onFiltersChange({});
  };

  const hasActiveFilters = Object.keys(localFilters).length > 0;

  const commonLocations = [
    '東京', '大阪', '名古屋', '横浜', '福岡', '札幌', '仙台', '広島', '京都', '神戸',
    'リモート', '全国対応'
  ];

  return (
    <div className="search-filters-panel">
      <div className="filters-header">
        <h3>検索フィルター</h3>
        {hasActiveFilters && (
          <button className="clear-filters-btn" onClick={clearAllFilters}>
            すべてクリア
          </button>
        )}
      </div>

      {/* Experience Years Filter */}
      <div className="filter-section">
        <h4>経験年数</h4>
        <div className="experience-range">
          <div className="range-input">
            <label>最小</label>
            <input
              type="number"
              min="0"
              max="50"
              value={localFilters.experience_years?.min || 0}
              onChange={(e) => handleExperienceChange('min', e.target.value)}
            />
            <span>年</span>
          </div>
          <div className="range-input">
            <label>最大</label>
            <input
              type="number"
              min="0"
              max="50"
              value={localFilters.experience_years?.max || 50}
              onChange={(e) => handleExperienceChange('max', e.target.value)}
            />
            <span>年</span>
          </div>
        </div>
      </div>

      {/* Skills Filter */}
      <div className="filter-section">
        <h4>スキル</h4>
        <div className="skills-categories">
          {skillCategories.map((category) => (
            <div key={category.category} className="skill-category">
              <button
                className={`category-toggle ${expandedCategories.has(category.category) ? 'expanded' : ''}`}
                onClick={() => toggleCategory(category.category)}
              >
                <span>{category.category}</span>
                <span className="toggle-icon">
                  {expandedCategories.has(category.category) ? '−' : '+'}
                </span>
              </button>
              
              {expandedCategories.has(category.category) && (
                <div className="skills-list">
                  {category.skills.map((skill) => (
                    <label key={skill} className="skill-checkbox">
                      <input
                        type="checkbox"
                        checked={(localFilters.skills || []).includes(skill)}
                        onChange={() => handleSkillToggle(skill)}
                      />
                      <span>{skill}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Locations Filter */}
      <div className="filter-section">
        <h4>勤務地</h4>
        <div className="checkbox-list">
          {commonLocations.map((location) => (
            <label key={location} className="checkbox-item">
              <input
                type="checkbox"
                checked={(localFilters.locations || []).includes(location)}
                onChange={() => handleLocationToggle(location)}
              />
              <span>{location}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Availability Filter */}
      <div className="filter-section">
        <h4>勤務形態</h4>
        <div className="checkbox-list">
          <label className="checkbox-item">
            <input
              type="checkbox"
              checked={(localFilters.availability || []).includes('full_time')}
              onChange={() => handleAvailabilityToggle('full_time')}
            />
            <span>フルタイム</span>
          </label>
          <label className="checkbox-item">
            <input
              type="checkbox"
              checked={(localFilters.availability || []).includes('part_time')}
              onChange={() => handleAvailabilityToggle('part_time')}
            />
            <span>パートタイム</span>
          </label>
          <label className="checkbox-item">
            <input
              type="checkbox"
              checked={(localFilters.availability || []).includes('consulting')}
              onChange={() => handleAvailabilityToggle('consulting')}
            />
            <span>コンサルティング</span>
          </label>
          <label className="checkbox-item">
            <input
              type="checkbox"
              checked={(localFilters.availability || []).includes('project_based')}
              onChange={() => handleAvailabilityToggle('project_based')}
            />
            <span>プロジェクトベース</span>
          </label>
        </div>
      </div>

      {/* Work Style Filter */}
      <div className="filter-section">
        <h4>働き方</h4>
        <div className="checkbox-list">
          <label className="checkbox-item">
            <input
              type="checkbox"
              checked={(localFilters.work_style || []).includes('remote')}
              onChange={() => handleWorkStyleToggle('remote')}
            />
            <span>リモート</span>
          </label>
          <label className="checkbox-item">
            <input
              type="checkbox"
              checked={(localFilters.work_style || []).includes('hybrid')}
              onChange={() => handleWorkStyleToggle('hybrid')}
            />
            <span>ハイブリッド</span>
          </label>
          <label className="checkbox-item">
            <input
              type="checkbox"
              checked={(localFilters.work_style || []).includes('onsite')}
              onChange={() => handleWorkStyleToggle('onsite')}
            />
            <span>オンサイト</span>
          </label>
          <label className="checkbox-item">
            <input
              type="checkbox"
              checked={(localFilters.work_style || []).includes('flexible')}
              onChange={() => handleWorkStyleToggle('flexible')}
            />
            <span>柔軟</span>
          </label>
        </div>
      </div>
    </div>
  );
};

export default SearchFiltersPanel;