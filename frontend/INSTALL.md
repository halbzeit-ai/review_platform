# Frontend Installation Guide

## Prerequisites

- Node.js (v16 or higher)
- npm (v8 or higher)

## Quick Setup

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

## Dependencies Overview

### Core React Dependencies
- `react` & `react-dom` - Core React framework
- `react-router-dom` - Client-side routing
- `react-scripts` - Build tooling and development server

### UI Components & Styling
- `@mui/material` - Material-UI component library
- `@mui/icons-material` - Material-UI icons
- `@emotion/react` & `@emotion/styled` - CSS-in-JS styling

### Data Visualization
- `recharts` - React charting library for radar/polar plots

### API & Data Handling
- `axios` - HTTP client for API requests

### Internationalization
- `i18next` - Internationalization framework
- `react-i18next` - React bindings for i18next
- `i18next-browser-languagedetector` - Browser language detection

### Testing
- `@testing-library/react` - React testing utilities
- `@testing-library/jest-dom` - Jest DOM matchers
- `@testing-library/user-event` - User event simulation
- `msw` - Mock Service Worker for API mocking

## Production Deployment

### 1. Build the Application
```bash
npm run build
```

### 2. Serve Static Files
The build creates a `build/` directory with static files that can be served by any web server (nginx, apache, etc.).

### 3. Environment Configuration
Ensure your API endpoints are configured correctly in the build environment.

## Development Scripts

- `npm start` - Start development server (port 3000)
- `npm run build` - Create production build
- `npm test` - Run tests in watch mode
- `npm run test:unit` - Run unit tests only
- `npm run test:integration` - Run integration tests only
- `npm run test:coverage` - Run tests with coverage report
- `npm run test:ci` - Run tests for CI/CD pipeline

## New Server Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd review_platform/frontend
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Configure Environment
- Set up API endpoints
- Configure build settings if needed

### 4. Build and Deploy
```bash
npm run build
# Deploy build/ directory to web server
```

## Troubleshooting

### Common Issues

1. **Node version incompatibility**
   - Ensure Node.js v16+ is installed
   - Use `nvm` to manage Node versions

2. **Dependencies not found**
   - Run `npm install` to install all dependencies
   - Check package.json for version conflicts

3. **Build failures**
   - Clear npm cache: `npm cache clean --force`
   - Delete node_modules and reinstall: `rm -rf node_modules && npm install`

4. **Port conflicts**
   - Development server runs on port 3000 by default
   - Use `PORT=3001 npm start` to change port

### Performance

- Use `npm run build` for production builds (optimized and minified)
- Enable gzip compression on your web server
- Consider implementing service workers for caching

## Key Features Supported

- **Dynamic Polar Plots**: Recharts-powered radar charts for investment analysis
- **Healthcare Templates**: Support for structured healthcare startup analysis
- **Responsive Design**: Works on desktop and mobile devices
- **Internationalization**: Support for multiple languages
- **Comprehensive Testing**: Unit, integration, and coverage testing
- **Modern React**: Hooks, context, and modern React patterns