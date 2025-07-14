"""
Unit tests for I18n service functionality
"""

import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import json

from app.services.i18n_service import I18nService


class TestI18nService:
    """Test cases for I18nService"""
    
    def test_service_initialization(self):
        """Test I18n service initialization"""
        service = I18nService()
        assert service.default_language == "en"
        assert service.supported_languages == ["en", "de"]
        assert isinstance(service.translations, dict)
    
    def test_get_supported_languages(self):
        """Test getting supported languages"""
        service = I18nService()
        languages = service.get_supported_languages()
        assert languages == ["en", "de"]
        assert isinstance(languages, list)
    
    def test_is_language_supported(self):
        """Test language support check"""
        service = I18nService()
        assert service.is_language_supported("en") is True
        assert service.is_language_supported("de") is True
        assert service.is_language_supported("fr") is False
        assert service.is_language_supported("invalid") is False
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"verification": {"subject": "Verify your account"}}')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.glob')
    def test_translation_loading(self, mock_glob, mock_exists, mock_file):
        """Test translation file loading"""
        # Mock the glob to return a fake JSON file
        mock_json_file = MagicMock()
        mock_json_file.stem = 'emails'
        mock_glob.return_value = [mock_json_file]
        
        service = I18nService()
        service._load_translations()
        
        # Should have attempted to load translations
        assert mock_file.called
    
    def test_basic_translation_lookup(self):
        """Test basic translation lookup"""
        service = I18nService()
        
        # Mock some translations
        service.translations = {
            "en": {
                "emails": {
                    "verification": {
                        "subject": "Verify your account"
                    }
                }
            },
            "de": {
                "emails": {
                    "verification": {
                        "subject": "Verifizieren Sie Ihr Konto"
                    }
                }
            }
        }
        
        # Test English translation
        result = service.t("emails.verification.subject", "en")
        assert result == "Verify your account"
        
        # Test German translation
        result = service.t("emails.verification.subject", "de")
        assert result == "Verifizieren Sie Ihr Konto"
    
    def test_variable_substitution(self):
        """Test variable substitution in translations"""
        service = I18nService()
        
        # Mock translation with variable
        service.translations = {
            "en": {
                "emails": {
                    "welcome": {
                        "title": "Welcome to HALBZEIT AI, {company_name}!"
                    }
                }
            }
        }
        
        result = service.t("emails.welcome.title", "en", company_name="Test Company")
        assert result == "Welcome to HALBZEIT AI, Test Company!"
    
    def test_fallback_to_default_language(self):
        """Test fallback to default language for unsupported language"""
        service = I18nService()
        
        # Mock English translation only
        service.translations = {
            "en": {
                "emails": {
                    "verification": {
                        "subject": "Verify your account"
                    }
                }
            }
        }
        
        # Request French (unsupported) should fallback to English
        result = service.t("emails.verification.subject", "fr")
        assert result == "Verify your account"
    
    def test_invalid_key_handling(self):
        """Test handling of invalid translation keys"""
        service = I18nService()
        
        # Mock empty translations
        service.translations = {"en": {}}
        
        # Invalid key should return the key itself
        result = service.t("nonexistent.key", "en")
        assert result == "nonexistent.key"
    
    def test_missing_variable_handling(self):
        """Test handling of missing variables in templates"""
        service = I18nService()
        
        # Mock translation with variable
        service.translations = {
            "en": {
                "emails": {
                    "welcome": {
                        "title": "Welcome {name}!"
                    }
                }
            }
        }
        
        # Missing variable should return template as-is
        result = service.t("emails.welcome.title", "en")
        assert result == "Welcome {name}!"
    
    def test_reload_translations(self):
        """Test translation reload functionality"""
        service = I18nService()
        
        # Add some mock translations
        service.translations = {"test": "data"}
        
        # Reload should clear and reload
        with patch.object(service, '_load_translations') as mock_load:
            service.reload_translations()
            assert service.translations == {}
            mock_load.assert_called_once()