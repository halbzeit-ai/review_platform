import React from 'react';
import { render } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../i18n';

describe('Translation System', () => {
  beforeEach(() => {
    // Reset to English before each test
    i18n.changeLanguage('en');
  });

  describe('Dashboard Status Translations', () => {
    test('provides correct English status translations', () => {
      expect(i18n.t('startup.decksSection.status.pending', { ns: 'dashboard' })).toBe('Waiting for processing');
      expect(i18n.t('startup.decksSection.status.processing', { ns: 'dashboard' })).toBe('Being analyzed...');
      expect(i18n.t('startup.decksSection.status.completed', { ns: 'dashboard' })).toBe('Evaluated');
      expect(i18n.t('startup.decksSection.status.failed', { ns: 'dashboard' })).toBe('Failed');
      expect(i18n.t('startup.decksSection.status.uploaded', { ns: 'dashboard' })).toBe('Uploaded');
    });

    test('provides correct German status translations', () => {
      i18n.changeLanguage('de');
      
      expect(i18n.t('startup.decksSection.status.pending', { ns: 'dashboard' })).toBe('Warte auf Verarbeitung');
      expect(i18n.t('startup.decksSection.status.processing', { ns: 'dashboard' })).toBe('Wird analysiert...');
      expect(i18n.t('startup.decksSection.status.completed', { ns: 'dashboard' })).toBe('Bewertet');
      expect(i18n.t('startup.decksSection.status.failed', { ns: 'dashboard' })).toBe('Fehlgeschlagen');
      expect(i18n.t('startup.decksSection.status.uploaded', { ns: 'dashboard' })).toBe('Hochgeladen');
    });
  });

  describe('Upload Section Translations', () => {
    test('provides correct English upload translations', () => {
      expect(i18n.t('startup.uploadSection.title', { ns: 'dashboard' })).toBe('Upload Pitch Deck');
      expect(i18n.t('startup.uploadSection.success', { ns: 'dashboard' })).toBe('File uploaded successfully!');
      expect(i18n.t('startup.uploadSection.uploading', { ns: 'dashboard' })).toBe('Uploading file...');
    });

    test('provides correct German upload translations', () => {
      i18n.changeLanguage('de');
      
      expect(i18n.t('startup.uploadSection.title', { ns: 'dashboard' })).toBe('Pitch Deck hochladen');
      expect(i18n.t('startup.uploadSection.success', { ns: 'dashboard' })).toBe('Datei erfolgreich hochgeladen!');
      expect(i18n.t('startup.uploadSection.uploading', { ns: 'dashboard' })).toBe('Datei wird hochgeladen...');
    });
  });

  describe('Language Switching', () => {
    test('switches language successfully', () => {
      expect(i18n.language).toBe('en');
      
      i18n.changeLanguage('de');
      expect(i18n.language).toBe('de');
      
      i18n.changeLanguage('en');
      expect(i18n.language).toBe('en');
    });

    test('translation function returns string', () => {
      const result = i18n.t('startup.decksSection.status.pending', { ns: 'dashboard' });
      expect(typeof result).toBe('string');
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('Component Integration', () => {
    test('can be used in React components', () => {
      const TestComponent = () => {
        const { t } = i18n;
        return <div>{t('startup.decksSection.status.pending', { ns: 'dashboard' })}</div>;
      };

      const { container } = render(
        <I18nextProvider i18n={i18n}>
          <TestComponent />
        </I18nextProvider>
      );

      expect(container.textContent).toContain('Waiting for processing');
    });
  });
});