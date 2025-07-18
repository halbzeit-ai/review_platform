"""
Internationalization service for handling translations
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class I18nService:
    def __init__(self):
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.default_language = "en"
        self.supported_languages = ["en", "de"]
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Load all translation files from the locales directory"""
        # Get the locales directory path
        current_dir = Path(__file__).parent.parent
        locales_dir = current_dir / "locales"
        
        if not locales_dir.exists():
            logger.warning(f"Locales directory not found at {locales_dir}")
            return
        
        for language in self.supported_languages:
            lang_dir = locales_dir / language
            if not lang_dir.exists():
                logger.warning(f"Language directory not found: {lang_dir}")
                continue
            
            self.translations[language] = {}
            
            # Load all JSON files in the language directory
            for json_file in lang_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        namespace = json_file.stem  # filename without extension
                        self.translations[language][namespace] = json.load(f)
                        logger.info(f"Loaded translations for {language}/{namespace}")
                except Exception as e:
                    logger.error(f"Failed to load translation file {json_file}: {e}")
    
    def t(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        Translate a key to the specified language
        
        Args:
            key: Translation key in format "namespace.section.key" (e.g., "emails.verification.subject")
            language: Target language code (defaults to default_language)
            **kwargs: Variables to substitute in the translation
            
        Returns:
            Translated string with variables substituted
        """
        if language is None:
            language = self.default_language
        
        # Fallback to default language if requested language not supported
        if language not in self.supported_languages:
            language = self.default_language
        
        # Parse the key
        key_parts = key.split('.')
        if len(key_parts) < 2:
            logger.warning(f"Invalid translation key format: {key}")
            return key
        
        namespace = key_parts[0]
        nested_key = key_parts[1:]
        
        # Get the translation
        try:
            # Start with the language translations
            current = self.translations.get(language, {})
            
            # Navigate to the namespace
            current = current.get(namespace, {})
            
            # Navigate through nested keys
            for part in nested_key:
                if isinstance(current, dict):
                    current = current.get(part, {})
                else:
                    raise KeyError(f"Invalid key path: {key}")
            
            if not isinstance(current, str):
                raise KeyError(f"Translation not found or not a string: {key}")
            
            # Substitute variables
            if kwargs:
                try:
                    return current.format(**kwargs)
                except KeyError as e:
                    logger.warning(f"Missing variable for translation {key}: {e}")
                    return current
            
            return current
            
        except KeyError:
            # Try fallback to default language
            if language != self.default_language:
                logger.warning(f"Translation not found for {key} in {language}, trying {self.default_language}")
                return self.t(key, self.default_language, **kwargs)
            
            # Return the key itself as fallback
            logger.error(f"Translation not found: {key}")
            return key
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        return self.supported_languages.copy()
    
    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported"""
        return language in self.supported_languages
    
    def reload_translations(self) -> None:
        """Reload all translation files (useful for development)"""
        self.translations.clear()
        self._load_translations()

# Global i18n service instance
i18n_service = I18nService()