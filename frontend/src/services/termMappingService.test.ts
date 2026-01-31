import { termMappingService } from './termMappingService';

describe('TermMappingService', () => {
  test('should map legacy terms correctly', () => {
    expect(termMappingService.mapLegacyTerm('Honda Veteran Talent Bank')).toBe('製造業プラチナアドバイザリー');
    expect(termMappingService.mapLegacyTerm('ベテラン')).toBe('登録人材');
    expect(termMappingService.mapLegacyTerm('問診')).toBe('スキル棚卸し');
    expect(termMappingService.mapLegacyTerm('応募')).toBe('参画申請');
    expect(termMappingService.mapLegacyTerm('興味表明')).toBe('参画意向');
  });

  test('should return original term if no mapping exists', () => {
    expect(termMappingService.mapLegacyTerm('未知の用語')).toBe('未知の用語');
  });

  test('should get localized terms correctly', () => {
    expect(termMappingService.getLocalizedTerm('app_title')).toBe('製造業プラチナアドバイザリー');
    expect(termMappingService.getLocalizedTerm('navigation_talent')).toBe('登録人材');
    expect(termMappingService.getLocalizedTerm('navigation_questionnaire')).toBe('スキル棚卸し');
    expect(termMappingService.getLocalizedTerm('skill_portfolio')).toBe('スキルポートフォリオ');
  });

  test('should validate term consistency', () => {
    expect(termMappingService.validateTermConsistency()).toBe(true);
  });

  test('should get success messages', () => {
    expect(termMappingService.getSuccessMessage('profile_updated')).toBe('スキルポートフォリオが正常に更新されました');
    expect(termMappingService.getSuccessMessage('application_submitted')).toBe('参画申請が正常に送信されました');
  });

  test('should get error messages', () => {
    expect(termMappingService.getErrorMessage('profile_validation_failed')).toBe('スキルポートフォリオの検証に失敗しました');
    expect(termMappingService.getErrorMessage('application_failed')).toBe('参画申請の処理中にエラーが発生しました');
  });

  test('should get branding config', () => {
    const config = termMappingService.getBrandingConfig();
    expect(config.applicationTitle).toBe('製造業プラチナアドバイザリー');
    expect(config.navigationTerms.talent).toBe('登録人材');
    expect(config.navigationTerms.questionnaire).toBe('スキル棚卸し');
  });

  test('should get theme config', () => {
    const theme = termMappingService.getThemeConfig();
    expect(theme.primary).toBe('#2C5282');
    expect(theme.secondary).toBe('#4A5568');
    expect(theme.accent).toBe('#3182CE');
  });
});