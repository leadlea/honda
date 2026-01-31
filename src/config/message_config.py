"""
Message configuration service for the Manufacturing Platinum Advisory platform.
Provides centralized message management with new terminology.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class MessageConfig:
    """Centralized message configuration service for branding consistency."""
    
    def __init__(self):
        """Initialize message configuration with default messages."""
        self.error_messages: Dict[str, str] = {}
        self.success_messages: Dict[str, str] = {}
        self.log_templates: Dict[str, str] = {}
        self.info_messages: Dict[str, str] = {}
        self.term_mappings: Dict[str, str] = {}
        
        # Load configuration from file
        self._load_config()
    
    def _load_config(self) -> None:
        """Load message configuration from JSON file."""
        try:
            config_path = Path(__file__).parent / 'term-mapping.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # Load messages
                messages = config.get('messages', {})
                self.success_messages = messages.get('success', {})
                self.error_messages = messages.get('errors', {})
                self.info_messages = messages.get('info', {})
                
                # Load term mappings
                term_mappings = config.get('termMappings', {})
                self.term_mappings = term_mappings.get('legacy_terms', {})
                
                # Load log templates
                self._initialize_log_templates()
            else:
                # Fallback to default configuration
                self._initialize_default_config()
                
        except Exception as e:
            print(f"Warning: Failed to load message config: {e}")
            self._initialize_default_config()
    
    def _initialize_default_config(self) -> None:
        """Initialize default message configuration."""
        # Success messages
        self.success_messages = {
            'profile_updated': 'スキルポートフォリオが正常に更新されました',
            'application_submitted': '参画申請が正常に送信されました',
            'application_withdrawn': '参画申請が正常に取り下げられました',
            'questionnaire_completed': 'スキル棚卸しが完了しました',
            'registration_completed': '人材登録が完了しました',
            'recommendation_generated': '参画機会レコメンドが生成されました',
            'search_completed': '登録人材検索が完了しました',
            'authentication_success': '認証が成功しました',
            'data_saved': 'データが正常に保存されました'
        }
        
        # Error messages
        self.error_messages = {
            'profile_validation_failed': 'スキルポートフォリオの検証に失敗しました',
            'application_failed': '参画申請の処理中にエラーが発生しました',
            'questionnaire_incomplete': 'スキル棚卸しが不完全です',
            'registration_failed': '人材登録に失敗しました',
            'recommendation_failed': '参画機会レコメンドの生成に失敗しました',
            'search_failed': '登録人材検索に失敗しました',
            'authentication_failed': '認証に失敗しました',
            'authorization_failed': '権限が不足しています',
            'validation_error': 'データの検証に失敗しました',
            'database_error': 'データベースエラーが発生しました',
            'internal_error': '内部エラーが発生しました'
        }
        
        # Info messages
        self.info_messages = {
            'welcome_message': '製造業プラチナアドバイザリーへようこそ',
            'profile_help': 'スキルポートフォリオを充実させて、最適な参画機会を見つけましょう',
            'questionnaire_help': 'スキル棚卸しを通じて、あなたの専門性を可視化します',
            'recommendation_help': 'AIが分析した参画機会レコメンドをご確認ください',
            'application_help': '参画申請の状況をこちらで確認できます'
        }
        
        # Term mappings
        self.term_mappings = {
            'Honda Veteran Talent Bank': '製造業プラチナアドバイザリー',
            'ベテラン': '登録人材',
            '問診': 'スキル棚卸し',
            'ベテランプロフィール': 'スキルポートフォリオ',
            '推薦機会': '参画機会レコメンド',
            '応募': '参画申請',
            '興味表明': '参画意向',
            'ベテラン検索': '登録人材検索'
        }
        
        self._initialize_log_templates()
    
    def _initialize_log_templates(self) -> None:
        """Initialize log message templates."""
        self.log_templates = {
            'user_login': '登録人材がログインしました: {user_id}',
            'user_logout': '登録人材がログアウトしました: {user_id}',
            'profile_updated': 'スキルポートフォリオが更新されました: {user_id}',
            'application_submitted': '参画申請が送信されました: {user_id} -> {opportunity_id}',
            'application_withdrawn': '参画申請が取り下げられました: {user_id} -> {opportunity_id}',
            'questionnaire_completed': 'スキル棚卸しが完了しました: {user_id}',
            'recommendation_generated': '参画機会レコメンドが生成されました: {user_id}',
            'search_performed': '登録人材検索が実行されました: {query}',
            'error_occurred': 'エラーが発生しました: {error_type} - {message}',
            'api_request': 'API リクエスト: {method} {endpoint} - {user_id}',
            'api_response': 'API レスポンス: {status_code} - {endpoint}',
            'database_operation': 'データベース操作: {operation} - {table}',
            'ai_generation': 'AI生成処理: {type} - {user_id}',
            'system_startup': '製造業プラチナアドバイザリーシステムが開始されました',
            'system_shutdown': '製造業プラチナアドバイザリーシステムが停止されました'
        }
    
    def get_message(self, key: str, message_type: str = 'success', **kwargs) -> str:
        """
        Get a formatted message by key and type.
        
        Args:
            key: Message key
            message_type: Type of message ('success', 'error', 'info')
            **kwargs: Format parameters
            
        Returns:
            Formatted message string
        """
        message_dict = {
            'success': self.success_messages,
            'error': self.error_messages,
            'info': self.info_messages
        }.get(message_type, self.success_messages)
        
        message = message_dict.get(key, f'{message_type.title()}: {key}')
        
        try:
            return message.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing format parameter {e} for message key '{key}'")
            return message
    
    def get_success_message(self, key: str, **kwargs) -> str:
        """Get a success message by key."""
        return self.get_message(key, 'success', **kwargs)
    
    def get_error_message(self, key: str, **kwargs) -> str:
        """Get an error message by key."""
        return self.get_message(key, 'error', **kwargs)
    
    def get_info_message(self, key: str, **kwargs) -> str:
        """Get an info message by key."""
        return self.get_message(key, 'info', **kwargs)
    
    def format_log_message(self, template_key: str, **kwargs) -> str:
        """
        Format a log message using a template.
        
        Args:
            template_key: Log template key
            **kwargs: Format parameters
            
        Returns:
            Formatted log message
        """
        template = self.log_templates.get(template_key, f'Log: {template_key}')
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing format parameter {e} for log template '{template_key}'")
            return template
    
    def map_legacy_term(self, legacy_term: str) -> str:
        """
        Map a legacy term to its new equivalent.
        
        Args:
            legacy_term: The old term to be mapped
            
        Returns:
            The new term, or the original term if no mapping exists
        """
        mapped_term = self.term_mappings.get(legacy_term, legacy_term)
        if mapped_term != legacy_term:
            print(f"Term mapping applied: {legacy_term} -> {mapped_term}")
        return mapped_term
    
    def get_branded_message(self, message: str) -> str:
        """
        Apply term mapping to a message to ensure brand consistency.
        
        Args:
            message: Original message
            
        Returns:
            Message with terms mapped to new branding
        """
        branded_message = message
        for legacy_term, new_term in self.term_mappings.items():
            branded_message = branded_message.replace(legacy_term, new_term)
        return branded_message
    
    def validate_config(self) -> bool:
        """
        Validate that all required message keys are present.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        required_success_keys = [
            'profile_updated', 'application_submitted', 'questionnaire_completed'
        ]
        required_error_keys = [
            'profile_validation_failed', 'application_failed', 'authentication_failed'
        ]
        
        for key in required_success_keys:
            if key not in self.success_messages:
                print(f"Missing required success message key: {key}")
                return False
        
        for key in required_error_keys:
            if key not in self.error_messages:
                print(f"Missing required error message key: {key}")
                return False
        
        return True


# Global instance for easy access
message_config = MessageConfig()