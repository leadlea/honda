import termMappingConfig from '../config/term-mapping.json';

export interface BrandingConfig {
  applicationTitle: string;
  navigationTerms: Record<string, string>;
  systemMessages: Record<string, string>;
  colorTheme: ThemeConfig;
}

export interface ThemeConfig {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  surface: string;
  textPrimary: string;
  textSecondary: string;
  success: string;
  warning: string;
  error: string;
}

export interface TermMappingService {
  mapLegacyTerm(legacyTerm: string): string;
  getLocalizedTerm(key: string): string;
  validateTermConsistency(): boolean;
  getBrandingConfig(): BrandingConfig;
  getThemeConfig(): ThemeConfig;
  getSuccessMessage(key: string): string;
  getErrorMessage(key: string): string;
  getInfoMessage(key: string): string;
}

class TermMappingServiceImpl implements TermMappingService {
  private config = termMappingConfig;

  /**
   * Maps a legacy term to its new equivalent
   * @param legacyTerm The old term to be mapped
   * @returns The new term, or the original term if no mapping exists
   */
  mapLegacyTerm(legacyTerm: string): string {
    const mapping = this.config.termMappings.legacy_terms[legacyTerm as keyof typeof this.config.termMappings.legacy_terms];
    if (mapping) {
      console.log(`Term mapping applied: ${legacyTerm} -> ${mapping}`);
      return mapping;
    }
    
    // Fallback: return original term if no mapping found
    if (legacyTerm.trim() !== '') {
      console.warn(`Term mapping not found for: ${legacyTerm}`);
    }
    return legacyTerm;
  }

  /**
   * Gets a localized UI label term
   * @param key The UI label key
   * @returns The localized term
   */
  getLocalizedTerm(key: string): string {
    const term = this.config.termMappings.ui_labels[key as keyof typeof this.config.termMappings.ui_labels];
    if (term) {
      return term;
    }
    
    console.warn(`UI label not found for key: ${key}`);
    return key; // Fallback to key itself
  }

  /**
   * Validates that all required terms are consistently mapped
   * @returns true if all terms are consistent, false otherwise
   */
  validateTermConsistency(): boolean {
    try {
      const requiredTerms = [
        'Honda Veteran Talent Bank',
        'ベテラン',
        '問診',
        'ベテランプロフィール',
        '推薦機会',
        '応募',
        '興味表明',
        'ベテラン検索'
      ];

      const requiredLabels = [
        'app_title',
        'dashboard_title',
        'navigation_talent',
        'navigation_questionnaire',
        'profile_section',
        'recommendations_section',
        'applications_section'
      ];

      // Check legacy term mappings
      for (const term of requiredTerms) {
        const mapped = this.mapLegacyTerm(term);
        if (mapped === term) {
          console.error(`Missing mapping for required term: ${term}`);
          return false;
        }
      }

      // Check UI label mappings
      for (const label of requiredLabels) {
        const localized = this.getLocalizedTerm(label);
        if (localized === label) {
          console.error(`Missing localization for required label: ${label}`);
          return false;
        }
      }

      return true;
    } catch (error) {
      console.error('Term consistency validation failed:', error);
      return false;
    }
  }

  /**
   * Gets the complete branding configuration
   * @returns BrandingConfig object
   */
  getBrandingConfig(): BrandingConfig {
    return {
      applicationTitle: this.getLocalizedTerm('app_title'),
      navigationTerms: {
        talent: this.getLocalizedTerm('navigation_talent'),
        questionnaire: this.getLocalizedTerm('navigation_questionnaire'),
        profile: this.getLocalizedTerm('navigation_profile'),
        recommendations: this.getLocalizedTerm('navigation_recommendations'),
        applications: this.getLocalizedTerm('navigation_applications')
      },
      systemMessages: {
        welcome: this.getInfoMessage('welcome_message'),
        profileHelp: this.getInfoMessage('profile_help'),
        questionnaireHelp: this.getInfoMessage('questionnaire_help')
      },
      colorTheme: this.getThemeConfig()
    };
  }

  /**
   * Gets the theme configuration
   * @returns ThemeConfig object
   */
  getThemeConfig(): ThemeConfig {
    const theme = this.config.branding.theme;
    return {
      primary: theme.primary,
      secondary: theme.secondary,
      accent: theme.accent,
      background: theme.background,
      surface: theme.surface,
      textPrimary: theme.text_primary,
      textSecondary: theme.text_secondary,
      success: theme.success,
      warning: theme.warning,
      error: theme.error
    };
  }

  /**
   * Gets a success message by key
   * @param key Message key
   * @returns Success message
   */
  getSuccessMessage(key: string): string {
    const message = this.config.messages.success[key as keyof typeof this.config.messages.success];
    return message || `Success: ${key}`;
  }

  /**
   * Gets an error message by key
   * @param key Message key
   * @returns Error message
   */
  getErrorMessage(key: string): string {
    const message = this.config.messages.errors[key as keyof typeof this.config.messages.errors];
    return message || `Error: ${key}`;
  }

  /**
   * Gets an info message by key
   * @param key Message key
   * @returns Info message
   */
  getInfoMessage(key: string): string {
    const message = this.config.messages.info[key as keyof typeof this.config.messages.info];
    return message || `Info: ${key}`;
  }

  /**
   * Gets the brand messaging configuration
   * @returns Brand messaging object
   */
  getBrandMessaging() {
    return this.config.branding.messaging;
  }
}

// Export singleton instance
export const termMappingService = new TermMappingServiceImpl();

// Export class for testing
export { TermMappingServiceImpl };