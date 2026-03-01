import { termMappingService } from './termMappingService';

describe('TermMappingService', () => {
  test('should map legacy terms correctly', () => {
    expect(termMappingService.mapLegacyTerm('製造業プラチナアドバイザリー')).toBe('AI人材発掘・配置マッチングMVP（AI CoE支援）');
    expect(termMappingService.mapLegacyTerm('登録人材')).toBe('社内AI人材候補');
    expect(termMappingService.mapLegacyTerm('問診')).toBe('AIスキル棚卸し（セルフ診断）');
    expect(termMappingService.mapLegacyTerm('参画申請')).toBe('自薦応募');
    expect(termMappingService.mapLegacyTerm('参画意向')).toBe('応募意向');
  });

  test('should return original term if no mapping exists', () => {
    expect(termMappingService.mapLegacyTerm('未知の用語')).toBe('未知の用語');
  });

  test('should get localized terms correctly', () => {
    expect(termMappingService.getLocalizedTerm('app_title')).toBe('AI人材発掘・配置マッチングMVP（AI CoE支援）');
    expect(termMappingService.getLocalizedTerm('navigation_talent')).toBe('社内AI人材候補');
    expect(termMappingService.getLocalizedTerm('navigation_questionnaire')).toBe('AIスキル棚卸し（セルフ診断）');
    expect(termMappingService.getLocalizedTerm('skill_portfolio')).toBe('AIスキルポートフォリオ');
  });

  test('should validate term consistency', () => {
    expect(termMappingService.validateTermConsistency()).toBe(true);
  });

  test('should get success messages', () => {
    expect(termMappingService.getSuccessMessage('profile_updated')).toBe('AIスキルポートフォリオが正常に更新されました');
    expect(termMappingService.getSuccessMessage('application_submitted')).toBe('自薦応募が正常に送信されました');
  });

  test('should get error messages', () => {
    expect(termMappingService.getErrorMessage('profile_validation_failed')).toBe('AIスキルポートフォリオの検証に失敗しました');
    expect(termMappingService.getErrorMessage('application_failed')).toBe('自薦応募の処理中にエラーが発生しました');
  });

  test('should get branding config', () => {
    const config = termMappingService.getBrandingConfig();
    expect(config.applicationTitle).toBe('AI人材発掘・配置マッチングMVP（AI CoE支援）');
    expect(config.navigationTerms.talent).toBe('社内AI人材候補');
    expect(config.navigationTerms.questionnaire).toBe('AIスキル棚卸し（セルフ診断）');
  });

  test('should get theme config', () => {
    const theme = termMappingService.getThemeConfig();
    expect(theme.primary).toBe('#2C5282');
    expect(theme.secondary).toBe('#4A5568');
    expect(theme.accent).toBe('#3182CE');
  });
});
