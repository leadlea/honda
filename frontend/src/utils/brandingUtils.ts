/**
 * Branding utilities for Manufacturing Platinum Advisory platform
 * 製造業プラチナアドバイザリー ブランディングユーティリティ
 */

export interface BrandingConfig {
  platformName: string;
  mission: string;
  targetAudience: string;
  tone: string;
  voice: string;
}

export const BRANDING_CONFIG: BrandingConfig = {
  platformName: '製造業プラチナアドバイザリー',
  mission: '人を活かす、新しい製造業の生態系',
  targetAudience: '製造業の登録人材',
  tone: 'professional_supportive',
  voice: 'empowering_collaborative'
};

export const TONE_GUIDELINES = {
  professional_supportive: '専門的でありながら親しみやすく、支援的な口調',
  empowering_collaborative: '登録人材の能力を引き出し、協働を促進する表現',
  manufacturing_focused: '製造業の専門性と価値を重視した表現',
  respectful_inclusive: '多様な経験と背景を尊重する包括的な表現'
};

export const TERM_MAPPINGS: Record<string, string> = {
  'Honda Veteran Talent Bank': '製造業プラチナアドバイザリー',
  'ベテラン': '登録人材',
  '問診': 'スキル棚卸し',
  'ベテランプロフィール': 'スキルポートフォリオ',
  '推薦機会': '参画機会レコメンド',
  '応募': '参画申請',
  '興味表明': '参画意向',
  'ベテラン検索': '登録人材検索'
};

export const BRANDED_MESSAGES = {
  welcome: {
    title: '製造業プラチナアドバイザリーへようこそ',
    subtitle: '人を活かす、新しい製造業の生態系',
    description: 'あなたの豊富な経験とスキルを活かし、製造業の未来を共に創造しましょう。'
  },
  dashboard: {
    title: 'ダッシュボード',
    subtitle: 'あなたの参画機会と活動状況',
    skillPortfolio: 'スキルポートフォリオ',
    participationOpportunities: '参画機会レコメンド',
    applicationStatus: '参画申請状況',
    skillInventory: 'スキル棚卸し'
  },
  profile: {
    title: 'スキルポートフォリオ管理',
    subtitle: 'あなたの専門性と経験を効果的にアピール',
    updateSuccess: 'スキルポートフォリオが正常に更新されました',
    updateError: 'スキルポートフォリオの更新中にエラーが発生しました',
    completionPrompt: 'プロフィールを充実させて、最適な参画機会を見つけましょう'
  },
  questionnaire: {
    title: 'スキル棚卸し',
    subtitle: 'あなたの専門性を詳しく教えてください',
    completionMessage: 'スキル棚卸しが完了しました。ありがとうございます。',
    helpText: 'この棚卸しを通じて、あなたに最適な参画機会をご提案いたします。'
  },
  recommendations: {
    title: '参画機会レコメンド',
    subtitle: 'あなたにおすすめの参画機会',
    noRecommendations: '現在、新しい参画機会レコメンドはありません。',
    viewDetails: '詳細を確認',
    applyNow: '参画申請する',
    expressInterest: '参画意向を表明'
  },
  applications: {
    title: '参画申請状況',
    subtitle: 'あなたの申請状況を確認',
    submitted: '申請済み',
    inReview: '審査中',
    approved: '承認済み',
    rejected: '見送り',
    withdrawn: '取り下げ済み',
    submitSuccess: '参画申請が正常に送信されました',
    withdrawSuccess: '参画申請を取り下げました'
  },
  search: {
    title: '登録人材検索',
    subtitle: '製造業の専門人材を見つける',
    searchPlaceholder: 'スキル、経験、専門分野で検索',
    noResults: '検索条件に一致する登録人材が見つかりませんでした',
    resultsCount: '{count}名の登録人材が見つかりました'
  },
  common: {
    loading: '読み込み中...',
    error: 'エラーが発生しました',
    success: '正常に完了しました',
    save: '保存',
    cancel: 'キャンセル',
    edit: '編集',
    delete: '削除',
    confirm: '確認',
    back: '戻る',
    next: '次へ',
    previous: '前へ',
    close: '閉じる',
    retry: '再試行',
    refresh: '更新'
  },
  ecosystem: {
    contribution: '製造業生態系への貢献',
    valueCreation: '価値創造',
    collaboration: '協働',
    innovation: '革新',
    sustainability: '持続可能性',
    excellence: '卓越性'
  }
};

/**
 * Apply term mapping to replace legacy terms with new branding
 */
export function applyTermMapping(text: string): string {
  let mappedText = text;
  
  Object.entries(TERM_MAPPINGS).forEach(([legacyTerm, newTerm]) => {
    const regex = new RegExp(legacyTerm, 'g');
    mappedText = mappedText.replace(regex, newTerm);
  });
  
  return mappedText;
}

/**
 * Get branded message with optional parameters
 */
export function getBrandedMessage(
  category: keyof typeof BRANDED_MESSAGES,
  key: string,
  params?: Record<string, string | number>
): string {
  const categoryMessages = BRANDED_MESSAGES[category] as Record<string, string>;
  let message = categoryMessages[key] || key;
  
  // Apply parameter substitution
  if (params) {
    Object.entries(params).forEach(([param, value]) => {
      const placeholder = `{${param}}`;
      message = message.replace(new RegExp(placeholder, 'g'), String(value));
    });
  }
  
  return applyTermMapping(message);
}

/**
 * Apply branding tone to a message
 */
export function applyBrandingTone(
  message: string,
  toneType: keyof typeof TONE_GUIDELINES = 'professional_supportive'
): string {
  // Apply term mapping first
  let brandedMessage = applyTermMapping(message);
  
  // Apply tone-specific adjustments
  switch (toneType) {
    case 'professional_supportive':
      // Ensure professional yet friendly tone
      brandedMessage = brandedMessage
        .replace(/です。/g, 'です。')
        .replace(/ます。/g, 'ます。');
      break;
      
    case 'empowering_collaborative':
      // Emphasize empowerment and collaboration
      if (!brandedMessage.includes('一緒に') && !brandedMessage.includes('共に')) {
        brandedMessage = brandedMessage.replace(
          /(します|いたします)/g,
          '$1。一緒に取り組みましょう'
        );
      }
      break;
      
    case 'manufacturing_focused':
      // Emphasize manufacturing expertise
      brandedMessage = brandedMessage
        .replace(/技術/g, '製造技術')
        .replace(/経験/g, '製造業経験');
      break;
      
    case 'respectful_inclusive':
      // Ensure inclusive language
      brandedMessage = brandedMessage
        .replace(/皆さん/g, '皆様')
        .replace(/あなた/g, 'あなた様');
      break;
  }
  
  return brandedMessage;
}

/**
 * Create a branded notification message
 */
export function createBrandedNotification(
  type: 'success' | 'error' | 'warning' | 'info',
  message: string,
  includeEcosystemContext: boolean = false
): string {
  let brandedMessage = applyBrandingTone(message);
  
  if (includeEcosystemContext) {
    const ecosystemMessage = type === 'success' 
      ? '製造業の新しい生態系での価値創造に向けて、一歩前進しました。'
      : '製造業プラチナアドバイザリーがサポートいたします。';
    
    brandedMessage += ` ${ecosystemMessage}`;
  }
  
  return brandedMessage;
}

/**
 * Format user-facing status messages
 */
export function formatStatusMessage(
  status: string,
  context: 'application' | 'recommendation' | 'profile' | 'general' = 'general'
): string {
  const statusMappings = {
    application: {
      pending: '参画申請を審査中です',
      approved: '参画申請が承認されました',
      rejected: '参画申請が見送りとなりました',
      withdrawn: '参画申請を取り下げました'
    },
    recommendation: {
      new: '新しい参画機会レコメンドがあります',
      viewed: '参画機会レコメンドを確認済みです',
      applied: '参画申請を送信しました',
      dismissed: '参画機会レコメンドを非表示にしました'
    },
    profile: {
      incomplete: 'スキルポートフォリオの入力を完了してください',
      complete: 'スキルポートフォリオが充実しています',
      updated: 'スキルポートフォリオを更新しました'
    },
    general: {
      loading: '読み込み中です...',
      error: 'エラーが発生しました',
      success: '正常に完了しました'
    }
  };
  
  const contextMappings = statusMappings[context] as Record<string, string>;
  return contextMappings[status] || applyTermMapping(status);
}

/**
 * Generate ecosystem-focused call-to-action messages
 */
export function generateEcosystemCTA(
  action: 'complete_profile' | 'apply_opportunity' | 'take_questionnaire' | 'explore_opportunities'
): string {
  const ctaMessages = {
    complete_profile: 'スキルポートフォリオを充実させて、製造業の新しい生態系で活躍しませんか？',
    apply_opportunity: 'この参画機会で、あなたの専門性を活かし価値創造に貢献しましょう。',
    take_questionnaire: 'スキル棚卸しを通じて、あなたの可能性を最大限に引き出しましょう。',
    explore_opportunities: '新しい参画機会を探して、製造業の未来を共に創造しましょう。'
  };
  
  return ctaMessages[action];
}

/**
 * Validate message consistency with branding guidelines
 */
export function validateBrandingConsistency(message: string): {
  isConsistent: boolean;
  issues: string[];
  suggestions: string[];
} {
  const issues: string[] = [];
  const suggestions: string[] = [];
  
  // Check for legacy terms
  Object.entries(TERM_MAPPINGS).forEach(([legacyTerm, newTerm]) => {
    if (message.includes(legacyTerm)) {
      issues.push(`Legacy term found: ${legacyTerm}`);
      suggestions.push(`Replace "${legacyTerm}" with "${newTerm}"`);
    }
  });
  
  // Check for platform name consistency
  if (message.includes('Honda') && !message.includes('製造業プラチナアドバイザリー')) {
    issues.push('Platform name inconsistency');
    suggestions.push('Use "製造業プラチナアドバイザリー" instead of Honda references');
  }
  
  // Check for tone consistency
  if (message.includes('です') || message.includes('ます')) {
    // Good - polite form
  } else if (message.includes('だ') || message.includes('である')) {
    issues.push('Tone inconsistency - too casual');
    suggestions.push('Use polite form (です/ます調) for professional tone');
  }
  
  return {
    isConsistent: issues.length === 0,
    issues,
    suggestions
  };
}

const brandingUtils = {
  BRANDING_CONFIG,
  TONE_GUIDELINES,
  TERM_MAPPINGS,
  BRANDED_MESSAGES,
  applyTermMapping,
  getBrandedMessage,
  applyBrandingTone,
  createBrandedNotification,
  formatStatusMessage,
  generateEcosystemCTA,
  validateBrandingConsistency
};

export default brandingUtils;