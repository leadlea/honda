/**
 * Branding utilities for AI人材発掘・配置マッチングMVP（AI CoE支援）
 * 双日テックイノベーション ブランディングユーティリティ
 */

export interface BrandingConfig {
  platformName: string;
  mission: string;
  targetAudience: string;
  tone: string;
  voice: string;
}

export const BRANDING_CONFIG: BrandingConfig = {
  platformName: 'AI人材発掘・配置マッチングMVP（AI CoE支援）',
  mission: 'AI内製化を前進させるための人材発掘と適材配置',
  targetAudience: '社内AI人材候補（社員）',
  tone: 'trustworthy_internal',
  voice: 'reliable_supportive'
};

export const TONE_GUIDELINES = {
  trustworthy_internal: '社内向けの信頼感あるトーン（過度に煽らない、誤解を招かない）',
  reliable_supportive: '社員の能力を正確に把握し、適材配置を支援する表現',
  ai_focused: 'AI内製化とスキル活用を重視した表現',
  respectful_inclusive: '多様なスキルレベルと背景を尊重する包括的な表現'
};

export const TERM_MAPPINGS: Record<string, string> = {
  'Honda Veteran Talent Bank': 'AI人材発掘・配置マッチングMVP（AI CoE支援）',
  '製造業プラチナアドバイザリー': 'AI人材発掘・配置マッチングMVP（AI CoE支援）',
  'ベテラン': '社内AI人材候補',
  '登録人材': '社内AI人材候補',
  '問診': 'AIスキル棚卸し（セルフ診断）',
  'スキル棚卸し': 'AIスキル棚卸し（セルフ診断）',
  'ベテランプロフィール': 'AIスキルポートフォリオ',
  'スキルポートフォリオ': 'AIスキルポートフォリオ',
  '推薦機会': 'AIポジション／プロジェクト レコメンド',
  '参画機会レコメンド': 'AIポジション／プロジェクト レコメンド',
  '応募': '自薦応募',
  '参画申請': '自薦応募',
  '興味表明': '応募意向',
  '参画意向': '応募意向',
  'ベテラン検索': '社内AI人材候補検索',
  '登録人材検索': '社内AI人材候補検索'
};

export const BRANDED_MESSAGES = {
  welcome: {
    title: 'AI人材発掘・配置マッチングMVP（AI CoE支援）へようこそ',
    subtitle: 'AI内製化を前進させるための人材発掘と適材配置',
    description: 'あなたのAIスキルと経験を活かし、社内のAI内製化推進に貢献しましょう。'
  },
  dashboard: {
    title: 'ダッシュボード',
    subtitle: 'あなたのAIポジションと活動状況',
    skillPortfolio: 'AIスキルポートフォリオ',
    participationOpportunities: 'AIポジション／プロジェクト レコメンド',
    applicationStatus: '自薦応募状況',
    skillInventory: 'AIスキル棚卸し（セルフ診断）'
  },
  profile: {
    title: 'AIスキルポートフォリオ管理',
    subtitle: 'あなたのAIスキルと経験を効果的に整理',
    updateSuccess: 'AIスキルポートフォリオが正常に更新されました',
    updateError: 'AIスキルポートフォリオの更新中にエラーが発生しました',
    completionPrompt: 'AIスキルポートフォリオを充実させて、最適なAIポジションを見つけましょう'
  },
  questionnaire: {
    title: 'AIスキル棚卸し（セルフ診断）',
    subtitle: 'あなたのAIスキルを詳しく教えてください',
    completionMessage: 'AIスキル棚卸し（セルフ診断）が完了しました。ありがとうございます。',
    helpText: 'この棚卸しを通じて、あなたに最適なAIポジションをご提案いたします。'
  },
  recommendations: {
    title: 'AIポジション／プロジェクト レコメンド',
    subtitle: 'あなたにおすすめのAIポジション',
    noRecommendations: '現在、新しいAIポジション／プロジェクト レコメンドはありません。',
    viewDetails: '詳細を確認',
    applyNow: '自薦応募する',
    expressInterest: '応募意向を表明'
  },
  applications: {
    title: '自薦応募状況',
    subtitle: 'あなたの応募状況を確認',
    submitted: '応募済み',
    inReview: '審査中',
    approved: '承認済み',
    rejected: '見送り',
    withdrawn: '取り下げ済み',
    submitSuccess: '自薦応募が正常に送信されました',
    withdrawSuccess: '自薦応募を取り下げました'
  },
  search: {
    title: '社内AI人材候補検索',
    subtitle: '社内のAI人材候補を見つける',
    searchPlaceholder: 'AIスキル、経験、専門分野で検索',
    noResults: '検索条件に一致する社内AI人材候補が見つかりませんでした',
    resultsCount: '{count}名の社内AI人材候補が見つかりました'
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
    contribution: 'AI内製化推進への貢献',
    valueCreation: '適材配置',
    collaboration: '部門横断連携',
    innovation: 'AI活用推進',
    sustainability: '持続的成長',
    excellence: '専門性向上'
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
  
  return message;
}

/**
 * Apply branding tone to a message
 */
export function applyBrandingTone(
  message: string,
  toneType: keyof typeof TONE_GUIDELINES = 'trustworthy_internal'
): string {
  // Apply term mapping first
  let brandedMessage = applyTermMapping(message);
  
  // Apply tone-specific adjustments
  switch (toneType) {
    case 'trustworthy_internal':
      // Ensure trustworthy internal tone
      brandedMessage = brandedMessage
        .replace(/です。/g, 'です。')
        .replace(/ます。/g, 'ます。');
      break;
      
    case 'reliable_supportive':
      // Emphasize reliable support for talent placement
      if (!brandedMessage.includes('支援') && !brandedMessage.includes('サポート')) {
        brandedMessage = brandedMessage.replace(
          /(します|いたします)/g,
          '$1。適材配置を支援いたします'
        );
      }
      break;
      
    case 'ai_focused':
      // Emphasize AI expertise
      brandedMessage = brandedMessage
        .replace(/技術/g, 'AI技術')
        .replace(/経験/g, 'AI関連経験');
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
      ? 'AI内製化推進に向けて、一歩前進しました。'
      : 'AI人材発掘・配置マッチングMVP（AI CoE支援）がサポートいたします。';
    
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
      pending: '自薦応募を審査中です',
      approved: '自薦応募が承認されました',
      rejected: '自薦応募が見送りとなりました',
      withdrawn: '自薦応募を取り下げました'
    },
    recommendation: {
      new: '新しいAIポジション／プロジェクト レコメンドがあります',
      viewed: 'AIポジション／プロジェクト レコメンドを確認済みです',
      applied: '自薦応募を送信しました',
      dismissed: 'AIポジション／プロジェクト レコメンドを非表示にしました'
    },
    profile: {
      incomplete: 'AIスキルポートフォリオの入力を完了してください',
      complete: 'AIスキルポートフォリオが充実しています',
      updated: 'AIスキルポートフォリオを更新しました'
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
 * Generate AI-focused call-to-action messages
 */
export function generateEcosystemCTA(
  action: 'complete_profile' | 'apply_opportunity' | 'take_questionnaire' | 'explore_opportunities'
): string {
  const ctaMessages = {
    complete_profile: 'AIスキルポートフォリオを充実させて、最適なAIポジションを見つけませんか？',
    apply_opportunity: 'このAIポジションで、あなたのスキルを活かしAI内製化に貢献しましょう。',
    take_questionnaire: 'AIスキル棚卸し（セルフ診断）を通じて、あなたの可能性を最大限に引き出しましょう。',
    explore_opportunities: '新しいAIポジションを探して、AI内製化推進に貢献しましょう。'
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
  if (message.includes('Honda') || message.includes('製造業プラチナアドバイザリー')) {
    issues.push('Platform name inconsistency');
    suggestions.push('Use "AI人材発掘・配置マッチングMVP（AI CoE支援）" instead of legacy platform references');
  }
  
  // Check for tone consistency
  if (message.includes('です') || message.includes('ます')) {
    // Good - polite form
  } else if (message.includes('だ') || message.includes('である')) {
    issues.push('Tone inconsistency - too casual');
    suggestions.push('Use polite form (です/ます調) for trustworthy internal tone');
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