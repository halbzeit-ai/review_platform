# Frontend Test Suite

This directory contains the comprehensive test suite for the React frontend application.

## Structure

```
src/__tests__/
├── README.md                    # This documentation
├── test-utils.js               # Test utilities and helpers
├── mocks/                      # Mock service workers and data
│   ├── handlers.js             # MSW API handlers
│   └── server.js               # MSW server setup
├── unit/                       # Unit tests
│   ├── components/             # Component unit tests
│   │   ├── Navigation.test.js
│   │   ├── LanguageSwitcher.test.js
│   │   └── ...
│   ├── services/               # Service layer tests
│   │   ├── api.test.js
│   │   └── ...
│   └── utils/                  # Utility function tests
└── integration/                # Integration tests
    ├── auth-flow.test.js       # Authentication workflows
    ├── dashboard-flow.test.js  # Dashboard functionality
    └── ...
```

## Test Types

### Unit Tests (`unit/`)
- **Component Tests**: Test individual React components in isolation
- **Service Tests**: Test API service functions and utilities
- **Utility Tests**: Test helper functions and utilities
- Fast execution with mocked dependencies

### Integration Tests (`integration/`)
- **User Flow Tests**: Complete user journeys and workflows
- **Cross-Component Tests**: Component interactions
- **API Integration**: Real API interactions with MSW
- End-to-end scenarios

## Technologies Used

- **Jest**: Test framework and test runner
- **React Testing Library**: Component testing utilities
- **MSW (Mock Service Worker)**: API mocking
- **@testing-library/user-event**: User interaction simulation
- **@testing-library/jest-dom**: Custom Jest matchers

## Running Tests

### Using npm scripts
```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test Navigation.test.js

# Run tests matching pattern
npm test -- --testNamePattern="auth"
```

### Using Jest directly
```bash
# Run unit tests only
npx jest src/__tests__/unit

# Run integration tests only
npx jest src/__tests__/integration

# Run with verbose output
npx jest --verbose

# Run tests and update snapshots
npx jest --updateSnapshot
```

## Test Configuration

### setupTests.js
Contains global test setup:
- Jest DOM extensions
- i18next mocking
- Global mocks (localStorage, IntersectionObserver, etc.)
- Browser API polyfills

### test-utils.js
Provides testing utilities:
- `renderWithProviders`: Render components with all necessary providers
- `mockUsers`: Predefined user objects for testing
- `mockApiResponses`: Standard API response objects
- `mockFiles`: File objects for upload testing
- Helper functions for common testing scenarios

### MSW Setup
Mock Service Worker provides realistic API mocking:
- **handlers.js**: Defines API endpoint behaviors
- **server.js**: Configures MSW for Node.js environment
- Intercepts HTTP requests during tests
- Returns realistic responses for different scenarios

## Writing Tests

### Component Unit Test Example
```javascript
import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import MyComponent from '../../components/MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    renderWithProviders(<MyComponent />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });

  it('handles user interaction', async () => {
    const user = userEvent.setup();
    renderWithProviders(<MyComponent />);
    
    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Updated Text')).toBeInTheDocument();
  });
});
```

### Integration Test Example
```javascript
import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import App from '../../App';

describe('User Registration Flow', () => {
  it('completes full registration process', async () => {
    const user = userEvent.setup();
    renderWithProviders(<App />, { route: '/register' });

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() => {
      expect(screen.getByText(/success/i)).toBeInTheDocument();
    });
  });
});
```

### API Service Test Example
```javascript
import { loginUser } from '../../services/api';
import { mockApiResponses } from '../test-utils';

describe('API Service', () => {
  it('successfully logs in user', async () => {
    const response = await loginUser({
      email: 'test@example.com',
      password: 'password123'
    });
    
    expect(response.data).toEqual(mockApiResponses.login.success);
  });
});
```

## Best Practices

### 1. Test Structure
- Follow **Arrange, Act, Assert** pattern
- Use descriptive test names: `should display error when email is invalid`
- Group related tests with `describe` blocks
- One assertion per test when possible

### 2. Component Testing
- Test behavior, not implementation
- Use accessible queries (`getByRole`, `getByLabelText`)
- Mock external dependencies and child components
- Test user interactions with `@testing-library/user-event`

### 3. Async Testing
- Use `waitFor` for async operations
- Avoid `act()` warnings with proper async/await
- Mock timers when testing time-dependent code
- Use `findBy` queries for elements that appear asynchronously

### 4. Mocking Strategy
- Mock external APIs with MSW
- Mock complex child components in unit tests
- Use `jest.mock()` for module mocking
- Provide realistic mock data

### 5. Accessibility Testing
- Test with screen reader friendly queries
- Verify ARIA attributes when necessary
- Test keyboard navigation
- Ensure proper focus management

## Coverage Goals

- **Unit Tests**: 90%+ code coverage
- **Integration Tests**: Cover critical user paths
- **Overall**: 85%+ combined coverage

Generate coverage report:
```bash
npm test -- --coverage --watchAll=false
```

## CI/CD Integration

Tests are designed for continuous integration:
- No external dependencies (using MSW for API mocking)
- Deterministic results
- Parallel execution support
- Coverage reporting for quality gates

### GitHub Actions Example
```yaml
- name: Run Frontend Tests
  run: |
    cd frontend
    npm ci
    npm test -- --coverage --watchAll=false
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./frontend/coverage/lcov.info
```

## Debugging Tests

### Common Issues
1. **Act Warnings**: Wrap state updates in `await waitFor()`
2. **Element Not Found**: Use `findBy` for async elements
3. **Timer Issues**: Mock timers with `jest.useFakeTimers()`
4. **MSW Not Working**: Ensure server is set up in `setupTests.js`

### Debug Tools
```bash
# Debug specific test
npm test -- --testNamePattern="specific test" --verbose

# Run tests without coverage (faster)
npm test -- --no-coverage

# Debug with Node.js inspector
node --inspect-brk node_modules/.bin/jest --runInBand
```

### Helpful Debugging Methods
```javascript
// Print component tree
import { screen } from '@testing-library/react';
screen.debug(); // Prints current DOM

// Print specific element
screen.debug(screen.getByTestId('my-element'));

// Check what queries are available
screen.logTestingPlaygroundURL();
```

## Performance

### Test Performance Tips
- Use `beforeEach` sparingly (prefer test isolation)
- Mock heavy dependencies
- Use shallow rendering when appropriate
- Avoid unnecessary `waitFor` delays
- Group slow tests separately

### Monitoring Test Performance
```bash
# Show test execution times
npm test -- --verbose

# Profile test performance
npm test -- --detectOpenHandles --forceExit
```

## Troubleshooting

### Common Test Failures
1. **Timeout Errors**: Increase timeout or fix async handling
2. **Memory Leaks**: Ensure proper cleanup in `afterEach`
3. **Flaky Tests**: Add proper waits for async operations
4. **Mock Issues**: Verify mock setup and reset between tests

### Getting Help
- Check React Testing Library docs: https://testing-library.com/
- MSW documentation: https://mswjs.io/
- Jest documentation: https://jestjs.io/

## Contributing

When adding new tests:
1. Follow existing patterns and structure
2. Add to appropriate directory (unit vs integration)
3. Update this README if adding new patterns
4. Ensure tests are deterministic and fast
5. Add proper documentation for complex test utilities