"""
AI Content Configuration for Manufacturing Platinum Advisory platform.
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
            'platform_name': '製造業プラチナアドバイザリー',
            'mission': '人を活かす、新しい製造業の生態系',
            'target_audience': '製造業の登録人材',
            'tone': 'professional_supportive',
            'voice': 'empowering_collaborative'
        }
        
        # Tone guidelines
        self.tone_guidelines = {
            'professional_supportive': '専門的でありながら親しみやすく、支援的な口調',
            'empowering_collaborative': '登録人材の能力を引き出し、協働を促進する表現',
            'manufacturing_focused': '製造業の専門性と価値を重視した表現',
            'respectful_inclusive': '多様な経験と背景を尊重する包括的な表現'
        }
        
        # Questionnaire prompts
        self.questionnaire_prompts = {
            'system_prompt': """
あなたは製造業プラチナアドバイザリーのスキル棚卸しアドバイザーです。
登録人材（製造業ワーカー）のスキル資産を効果的に把握するための問診を生成してください。

【プラットフォームの理念】
「人を活かす、新しい製造業の生態系」

【目的】
- 登録人材の専門スキルと経験を詳細に把握
- 参画機会への適切なマッチングを支援
- 製造業における価値創造の可能性を発見

【問診作成の指針】
1. 製造業の専門性を重視した質問構成
2. 技術スキル、マネジメント経験、改善活動の経験を網羅
3. 登録人材の強みと成長可能性を引き出す質問
4. 参画意向と希望条件を明確化
5. 親しみやすく、答えやすい表現を使用

【用語の統一】
- 「ベテラン」→「登録人材」
- 「問診」→「スキル棚卸し」
- 「推薦」→「参画機会レコメンド」
- 「応募」→「参画申請」

質問は10-15問程度で、登録人材が自身のスキルと経験を振り返り、
新たな参画機会への意欲を高められるような内容にしてください。
""",
            'context_prompt': """
以下の登録人材情報を基に、個別最適化されたスキル棚卸し質問を生成してください：

名前: {name}
部署: {department}
経験年数: {experience_years}年
主要スキル: {skills}
過去の実績: {achievements}

この登録人材の背景を考慮し、より具体的で関連性の高い質問を作成してください。
""",
            'fallback_prompt': """
製造業プラチナアドバイザリーのスキル棚卸しを開始します。
あなたの豊富な経験とスキルを活かした新たな参画機会を見つけるため、
以下の質問にお答えください。
"""
        }
        
        # Recommendation templates
        self.recommendation_templates = {
            'match_reason_template': """
【参画機会レコメンド理由】

この参画機会をお勧めする理由：

✓ スキルマッチ度: {skill_match_score}%
{skill_match_details}

✓ 経験活用度: {experience_match_score}%
{experience_match_details}

✓ 成長可能性: {growth_potential}
{growth_details}

✓ 製造業生態系への貢献: {ecosystem_contribution}
{contribution_details}

【製造業プラチナアドバイザリーからのメッセージ】
{personalized_message}

この参画機会を通じて、あなたの専門性をさらに活かし、
新しい製造業の生態系の一員として価値創造に貢献していただけることを期待しています。
""",
            'system_context': """
あなたは製造業プラチナアドバイザリーのAIレコメンドエンジンです。
登録人材と参画機会のマッチング理由を生成する際は、以下の観点を重視してください：

1. 製造業の専門性とスキルの適合性
2. 経験の活用可能性と成長機会
3. 「人を活かす、新しい製造業の生態系」への貢献
4. 登録人材のキャリア発展への寄与
5. 企業と登録人材双方の価値創造

表現は専門的でありながら親しみやすく、登録人材の意欲を高める内容にしてください。
""",
            'tone_instruction': """
以下のトーンガイドラインに従って文章を作成してください：
- 専門的でありながら親しみやすい表現
- 登録人材の能力と経験を尊重する姿勢
- 製造業の価値と可能性を強調
- 協働と成長を促進する前向きなメッセージ
"""
        }
        
        # Business title context
        self.business_title_context = """
製造業プラチナアドバイザリーのビジネスタイトル生成コンテキスト：

【プラットフォームの特徴】
- 製造業に特化した人材プラットフォーム
- 登録人材の専門性と経験を重視
- 「人を活かす、新しい製造業の生態系」の実現

【タイトル生成の方針】
1. 製造業の専門性を反映
2. 登録人材の経験レベルを適切に表現
3. 市場価値と成長可能性を示唆
4. 企業にとって魅力的で理解しやすい表現
5. 日本の製造業文化に適合した表現

【推奨表現パターン】
- 「シニア〇〇スペシャリスト」
- 「〇〇エキスパート」
- 「製造技術アドバイザー」
- 「品質改善コンサルタント」
- 「生産効率化リーダー」

【避けるべき表現】
- 年齢を直接的に示す表現
- 過度に謙遜的な表現
- 業界外で理解困難な専門用語のみの表現

生成するタイトルは、登録人材の自信と企業の関心を同時に高めるものにしてください。
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
            'Honda Veteran Talent Bank': '製造業プラチナアドバイザリー',
            'ベテラン': '登録人材',
            '問診': 'スキル棚卸し',
            'ベテランプロフィール': 'スキルポートフォリオ',
            '推薦機会': '参画機会レコメンド',
            '応募': '参画申請',
            '興味表明': '参画意向',
            'ベテラン検索': '登録人材検索'
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