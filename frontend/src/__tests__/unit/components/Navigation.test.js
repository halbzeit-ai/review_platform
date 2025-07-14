/**
 * Simple unit tests for Navigation component
 */

import React from 'react';
import { screen } from '@testing-library/react';
import { renderWithProviders, mockUsers } from '../../test-utils';
import Navigation from '../../../components/Navigation';

// Mock the LanguageSwitcher component
jest.mock('../../../components/LanguageSwitcher', () => {
  return function MockLanguageSwitcher() {
    return <div data-testid="language-switcher">Language Switcher</div>;
  };
});

describe('Navigation Component (Simple)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders the platform title', () => {
    renderWithProviders(<Navigation />);
    
    expect(screen.getByText('HALBZEIT AI Review Platform')).toBeInTheDocument();
  });

  it('renders language switcher', () => {
    renderWithProviders(<Navigation />);
    
    expect(screen.getByTestId('language-switcher')).toBeInTheDocument();
  });

  it('renders login and register buttons when not logged in', () => {
    localStorage.removeItem('user');
    
    renderWithProviders(<Navigation />);
    
    expect(screen.getByText('navigation.login')).toBeInTheDocument();
    expect(screen.getByText('navigation.register')).toBeInTheDocument();
  });

  it('renders logout button when logged in', () => {
    localStorage.setItem('user', JSON.stringify(mockUsers.startup));
    
    renderWithProviders(<Navigation />);
    
    expect(screen.getByText('navigation.logout')).toBeInTheDocument();
    expect(screen.queryByText('navigation.login')).not.toBeInTheDocument();
  });

  it('handles corrupted localStorage gracefully', () => {
    localStorage.setItem('user', 'invalid-json');
    
    renderWithProviders(<Navigation />);
    
    // Should render as if not logged in
    expect(screen.getByText('navigation.login')).toBeInTheDocument();
  });
});