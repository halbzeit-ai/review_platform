import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import deCommon from './locales/de/common.json';
import deAuth from './locales/de/auth.json';
import deDashboard from './locales/de/dashboard.json';
import deTemplates from './locales/de/templates.json';

import enCommon from './locales/en/common.json';
import enAuth from './locales/en/auth.json';
import enDashboard from './locales/en/dashboard.json';
import enTemplates from './locales/en/templates.json';

const resources = {
  de: {
    common: deCommon,
    auth: deAuth,
    dashboard: deDashboard,
    templates: deTemplates,
  },
  en: {
    common: enCommon,
    auth: enAuth,
    dashboard: enDashboard,
    templates: enTemplates,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'de', // German as default
    lng: 'de', // Start with German
    
    // Language detection options
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },

    interpolation: {
      escapeValue: false, // React already escapes values
    },

    // Namespace handling
    defaultNS: 'common',
    ns: ['common', 'auth', 'dashboard', 'templates'],

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