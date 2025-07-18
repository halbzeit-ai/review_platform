import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'de', // German as default
    lng: 'de', // Start with German
    
    // Language detection options
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },

    // Backend configuration for loading translations
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },

    interpolation: {
      escapeValue: false, // React already escapes values
    },

    // Namespace handling
    defaultNS: 'common',
    ns: ['common', 'auth', 'dashboard', 'templates', 'review'],

    // Debug mode for development
    debug: process.env.NODE_ENV === 'development',

    // Load resources synchronously
    load: 'languageOnly', // Don't load country-specific variants (e.g., de-DE)
    
    // React integration
    react: {
      useSuspense: false, // Disable suspense for now
    },
  });

export default i18n;