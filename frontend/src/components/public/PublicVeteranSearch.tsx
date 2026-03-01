import React, { useState, useEffect } from 'react';
import { PublicVeteranProfile, SearchFilters, SearchResult, SkillCategory } from '../../types/public';
import { PublicSearchService } from '../../services/publicSearchService';
import SearchFiltersPanel from './SearchFiltersPanel';
import VeteranSearchCard from './VeteranSearchCard';
import VeteranProfileModal from './VeteranProfileModal';
import { termMappingService } from '../../services/termMappingService';
import './PublicVeteranSearch.css';

const PublicVeteranSearch: React.FC = () => {
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<SearchFilters>({});
  const [skillCategories, setSkillCategories] = useState<SkillCategory[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedProfile, setSelectedProfile] = useState<PublicVeteranProfile | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    loadSkillCategories();
    performSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    performSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, currentPage]);

  const loadSkillCategories = async () => {
    try {
      const categories = await PublicSearchService.getSkillCategories();
      setSkillCategories(categories);
    } catch (error) {
      console.error('Failed to load skill categories:', error);
    }
  };

  const performSearch = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await PublicSearchService.searchVeterans(filters, currentPage, 12);
      setSearchResult(result);
    } catch (error) {
      setError('社内AI人材候補の検索中にエラーが発生しました。もう一度お試しください。');
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFiltersChange = (newFilters: SearchFilters) => {
    setFilters(newFilters);
    setCurrentPage(1);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleProfileSelect = (profile: PublicVeteranProfile) => {
    setSelectedProfile(profile);
  };

  const handleCloseModal = () => {
    setSelectedProfile(null);
  };

  const renderPagination = () => {
    if (!searchResult || searchResult.total_pages <= 1) return null;

    const pages = [];
    const maxVisiblePages = 5;
    const startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    const endPage = Math.min(searchResult.total_pages, startPage + maxVisiblePages - 1);

    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <button
          key={i}
          className={`pagination-btn ${i === currentPage ? 'active' : ''}`}
          onClick={() => handlePageChange(i)}
        >
          {i}
        </button>
      );
    }

    return (
      <div className="pagination">
        <button
          className="pagination-btn"
          onClick={() => handlePageChange(currentPage - 1)}
          disabled={currentPage === 1}
        >
          前へ
        </button>
        {pages}
        <button
          className="pagination-btn"
          onClick={() => handlePageChange(currentPage + 1)}
          disabled={currentPage === searchResult.total_pages}
        >
          次へ
        </button>
      </div>
    );
  };

  return (
    <div className="public-veteran-search">
      <div className="search-header">
        <h1>{termMappingService.getLocalizedTerm('app_title')}</h1>
        <p>社内のAI人材候補を検索して、最適なAIポジションへの配置を実現しましょう</p>
        
        <div className="search-controls">
          <button
            className={`filter-toggle ${showFilters ? 'active' : ''}`}
            onClick={() => setShowFilters(!showFilters)}
          >
            <span className="filter-icon">🔍</span>
            検索フィルター
            {Object.keys(filters).length > 0 && (
              <span className="filter-count">{Object.keys(filters).length}</span>
            )}
          </button>
        </div>
      </div>

      <div className="search-content">
        {showFilters && (
          <div className="filters-sidebar">
            <SearchFiltersPanel
              filters={filters}
              skillCategories={skillCategories}
              onFiltersChange={handleFiltersChange}
            />
          </div>
        )}

        <div className="search-results">
          {loading && (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>検索中...</p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <p className="error-message">{error}</p>
              <button onClick={performSearch} className="retry-btn">
                再試行
              </button>
            </div>
          )}

          {searchResult && !loading && (
            <>
              <div className="results-header">
                <h2>
                  検索結果: {searchResult.total_count}名の{termMappingService.getLocalizedTerm('navigation_talent')}
                  {searchResult.total_count > 0 && (
                    <span className="page-info">
                      （{((currentPage - 1) * 12) + 1}-{Math.min(currentPage * 12, searchResult.total_count)}件目を表示）
                    </span>
                  )}
                </h2>
              </div>

              {searchResult.profiles.length === 0 ? (
                <div className="no-results">
                  <h3>該当する{termMappingService.getLocalizedTerm('navigation_talent')}が見つかりませんでした</h3>
                  <p>検索条件を変更してもう一度お試しください。</p>
                </div>
              ) : (
                <>
                  <div className="veterans-grid">
                    {searchResult.profiles.map((profile) => (
                      <VeteranSearchCard
                        key={profile.profile_id}
                        profile={profile}
                        onSelect={handleProfileSelect}
                      />
                    ))}
                  </div>
                  {renderPagination()}
                </>
              )}
            </>
          )}
        </div>
      </div>

      {selectedProfile && (
        <VeteranProfileModal
          profile={selectedProfile}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};

export default PublicVeteranSearch;