"""
AI Content Configuration for 双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）.
Manages AI-generated content templates, prompts, and branding context.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class AIContentConfig:
    """Configuration service for AI-generated content with branding consistency."""
    
    def __init__(self):
        """Initialize AI content configuration."""
        self.questionnaire_prompts: Dict[str, str] = {}
        self.recommendation_templates: Dict[str, str] = {}
        self.business_title_context: str = ""
        self.brand_context: Dict[str, str] = {}
        self.tone_guidelines: Dict[str, str] = {}
        
        # Load configuration
        self._load_config()
    
    def _load_config(self) -> None:
        """Load AI content configuration from file or initialize defaults."""
        try:
            config_path = Path(__file__).parent / 'ai_content_config.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._load_from_config(config)
            else:
                self._initialize_default_config()
        except Exception as e:
            print(f"Warning: Failed to load AI content config: {e}")
            self._initialize_default_config()
    
    def _load_from_config(self, config: Dict[str, Any]) -> None:
        """Load configuration from dictionary."""
        self.questionnaire_prompts = config.get('questionnaire_prompts', {})
        self.recommendation_templates = config.get('recommendation_templates', {})
        self.business_title_context = config.get('business_title_context', '')
        self.brand_context = config.get('brand_context', {})
        self.tone_guidelines = config.get('tone_guidelines', {})
    
    def _initialize_default_config(self) -> None:
        """Initialize default AI content configuration."""
        # Brand context
        self.brand_context = {
            'platform_name': 'AI人材発掘・配置マッチングMVP（AI CoE支援）',
            'mission': 'AI内製化を前進させるための人材発掘と適材配置',
            'target_audience': '社内AI人材候補（社員）',
            'company': '双日テックイノベーション',
            'tone': 'professional_trustworthy',
            'voice': 'reliable_collaborative'
        }
        
        # Tone guidelines
        self.tone_guidelines = {
            'professional_trustworthy': '社内向けの信頼感あるトーン（過度に煽らない、誤解を招かない）',
            'reliable_collaborative': '社内AI人材候補の主体性を尊重し、協働を促進する表現',
            'ai_focused': 'AIスキルポートフォリオと内製化推進の価値を重視した表現',
            'respectful_inclusive': '多様なAIスキルレベルと背景を尊重する包括的な表現'
        }
        
        # Questionnaire prompts
        self.questionnaire_prompts = {
            'system_prompt': """
あなたは双日テックイノベーションのAI人材発掘・配置マッチングMVP（AI CoE支援）における
AIスキル棚卸し（セルフ診断）アドバイザーです。
社内AI人材候補（社員）のAIスキル資産を正確に把握するための質問を生成してください。

【プラットフォームのミッション】
「AI内製化を前進させるための人材発掘と適材配置」

【目的】
- 社内AI人材候補のAIスキルと経験を詳細に把握
- AIポジション／プロジェクト レコメンドへの適切なマッチングを支援
- 双日テックイノベーションにおけるAI内製化推進への貢献可能性を発見

【質問作成の指針】
1. AIスキルの専門性と実務経験を重視した質問構成
2. 技術スキル、プロジェクト経験、AI活用実績を網羅
3. 社内AI人材候補の強みと成長可能性を引き出す質問
4. 応募意向と希望ポジションを明確化
5. 社内向けの信頼感ある、答えやすい表現を使用

【用語の統一】
- 「ベテラン」→「社内AI人材候補」
- 「問診」→「AIスキル棚卸し（セルフ診断）」
- 「推薦」→「AIポジション／プロジェクト レコメンド」
- 「応募」→「自薦応募」

質問は10-15問程度で、社内AI人材候補が自身のAIスキルと経験を振り返り、
新たなAIポジション／プロジェクトへの自薦応募意欲を高められるような内容にしてください。
""",
            'context_prompt': """
以下の社内AI人材候補情報を基に、個別最適化されたAIスキル棚卸し（セルフ診断）質問を生成してください：

名前: {name}
部署: {department}
経験年数: {experience_years}年
主要スキル: {skills}
過去の実績: {achievements}

この社内AI人材候補の背景を考慮し、より具体的で関連性の高い質問を作成してください。
""",
            'fallback_prompt': """
双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）の
AIスキル棚卸し（セルフ診断）を開始します。
あなたのAIスキルと経験を活かした新たなAIポジション／プロジェクトを見つけるため、
以下の質問にお答えください。
"""
        }
        
        # Recommendation templates
        self.recommendation_templates = {
            'match_reason_template': """
【AIポジション／プロジェクト レコメンド理由】

このAIポジション／プロジェクトをお勧めする理由：

✓ AIスキルマッチ度: {skill_match_score}%
{skill_match_details}

✓ 経験活用度: {experience_match_score}%
{experience_match_details}

✓ 成長可能性: {growth_potential}
{growth_details}

✓ AI内製化推進への貢献: {ecosystem_contribution}
{contribution_details}

【AI人材発掘・配置マッチングMVP（AI CoE支援）からのメッセージ】
{personalized_message}

このAIポジション／プロジェクトを通じて、あなたのAIスキルをさらに活かし、
双日テックイノベーションのAI内製化を前進させる適材配置の一員として
貢献していただけることを期待しています。
""",
            'system_context': """
あなたは双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）の
AIレコメンドエンジンです。
社内AI人材候補とAIポジション／プロジェクトのマッチング理由を生成する際は、
以下の観点を重視してください：

1. AIスキルポートフォリオとポジション要件の適合性
2. 経験の活用可能性とAIスキル成長機会
3. 「AI内製化を前進させるための人材発掘と適材配置」への貢献
4. 社内AI人材候補のキャリア発展への寄与
5. 双日テックイノベーションとAI人材候補双方の価値創造

表現は社内向けの信頼感あるトーンで、過度に煽らず、誤解を招かない内容にしてください。
""",
            'tone_instruction': """
以下のトーンガイドラインに従って文章を作成してください：
- 社内向けの信頼感ある、落ち着いた表現
- 社内AI人材候補のAIスキルと経験を尊重する姿勢
- AI内製化推進の価値と可能性を誠実に伝える
- 自薦応募を促す前向きかつ誠実なメッセージ
"""
        }
        
        # Business title context
        self.business_title_context = """
双日テックイノベーション：AI人材発掘・配置マッチングMVP（AI CoE支援）の
AIスキルポートフォリオ見出し生成コンテキスト：

【プラットフォームの特徴】
- 双日テックイノベーションのAI内製化支援に特化した人材マッチングプラットフォーム
- 社内AI人材候補のAIスキルポートフォリオと経験を重視
- 「AI内製化を前進させるための人材発掘と適材配置」の実現

【見出し生成の方針】
1. AIスキルの専門性を正確に反映
2. 社内AI人材候補の経験レベルを適切に表現
3. AI内製化推進への貢献可能性を示唆
4. AIポジションオーナーにとって理解しやすい表現
5. 双日テックイノベーションの社内文化に適合した表現

【推奨表現パターン】
- 「AIエンジニア（〇〇専門）」
- 「AIプロジェクトリーダー候補」
- 「機械学習スペシャリスト」
- 「AI活用推進担当」
- 「データサイエンティスト候補」

【避けるべき表現】
- 過度に誇張した表現
- 誤解を招く可能性のある表現
- 社内文脈で不適切な専門用語のみの表現

生成する見出しは、社内AI人材候補の自信とAIポジションオーナーの関心を
適切に高めるものにしてください。
"""
    
    def get_questionnaire_prompt(self, prompt_type: str = 'system_prompt', **kwargs) -> str:
        """
        Get questionnaire generation prompt.
        
        Args:
            prompt_type: Type of prompt ('system_prompt', 'context_prompt', 'fallback_prompt')
            **kwargs: Format parameters for the prompt
            
        Returns:
            Formatted prompt string
        """
        prompt = self.questionnaire_prompts.get(prompt_type, '')
        if not prompt:
            return self.questionnaire_prompts.get('system_prompt', '')
        
        try:
            return prompt.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing format parameter {e} for questionnaire prompt")
            return prompt
    
    def get_recommendation_template(self, template_type: str = 'match_reason_template', **kwargs) -> str:
        """
        Get recommendation generation template.
        
        Args:
            template_type: Type of template
            **kwargs: Format parameters for the template
            
        Returns:
            Formatted template string
        """
        template = self.recommendation_templates.get(template_type, '')
        if not template:
            return self.recommendation_templates.get('match_reason_template', '')
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing format parameter {e} for recommendation template")
            return template
    
    def get_business_title_context(self) -> str:
        """Get business title generation context."""
        return self.business_title_context
    
    def get_brand_context(self, key: str = None) -> Dict[str, str] | str:
        """
        Get brand context information.
        
        Args:
            key: Specific brand context key (optional)
            
        Returns:
            Brand context dictionary or specific value
        """
        if key:
            return self.brand_context.get(key, '')
        return self.brand_context
    
    def get_tone_guideline(self, tone_type: str) -> str:
        """
        Get tone guideline for specific tone type.
        
        Args:
            tone_type: Type of tone guideline
            
        Returns:
            Tone guideline string
        """
        return self.tone_guidelines.get(tone_type, '')
    
    def apply_branding_context(self, content: str) -> str:
        """
        Apply branding context to content by replacing legacy terms.
        
        Args:
            content: Original content
            
        Returns:
            Content with branding applied
        """
        # Term mappings for branding consistency
        term_mappings = {
            '製造業プラチナアドバイザリー': 'AI人材発掘・配置マッチングMVP（AI CoE支援）',
            'Honda Veteran Talent Bank': 'AI人材発掘・配置マッチングMVP（AI CoE支援）',
            '登録人材': '社内AI人材候補',
            'ベテラン': '社内AI人材候補',
            '問診': 'AIスキル棚卸し（セルフ診断）',
            'スキル棚卸し': 'AIスキル棚卸し（セルフ診断）',
            'ベテランプロフィール': 'AIスキルポートフォリオ',
            'スキルポートフォリオ': 'AIスキルポートフォリオ',
            '参画機会レコメンド': 'AIポジション／プロジェクト レコメンド',
            '推薦機会': 'AIポジション／プロジェクト レコメンド',
            '参画申請': '自薦応募',
            '応募': '自薦応募',
            '参画意向': '応募意向',
            '興味表明': '応募意向',
            '登録人材検索': '社内AI人材候補検索',
            'ベテラン検索': '社内AI人材候補検索'
        }
        
        branded_content = content
        for legacy_term, new_term in term_mappings.items():
            branded_content = branded_content.replace(legacy_term, new_term)
        
        return branded_content
    
    def create_branded_prompt(self, base_prompt: str, context_type: str = 'general') -> str:
        """
        Create a branded prompt with platform context.
        
        Args:
            base_prompt: Base prompt content
            context_type: Type of context to apply
            
        Returns:
            Branded prompt with platform context
        """
        platform_context = f"""
【{self.brand_context['platform_name']}】
{self.brand_context['mission']}

"""
        
        branded_prompt = platform_context + self.apply_branding_context(base_prompt)
        return branded_prompt
    
    def validate_config(self) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        required_prompts = ['system_prompt', 'context_prompt']
        required_templates = ['match_reason_template', 'system_context']
        
        for prompt_key in required_prompts:
            if prompt_key not in self.questionnaire_prompts:
                print(f"Missing required questionnaire prompt: {prompt_key}")
                return False
        
        for template_key in required_templates:
            if template_key not in self.recommendation_templates:
                print(f"Missing required recommendation template: {template_key}")
                return False
        
        if not self.business_title_context:
            print("Missing business title context")
            return False
        
        return True


# Global instance for easy access
ai_content_config = AIContentConfig()