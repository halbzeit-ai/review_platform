/**
 * Build Information Utilities
 * Automatically generates build version and metadata
 */

// Generate build timestamp in the format we've been using
const generateBuildTimestamp = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hour = String(now.getHours()).padStart(2, '0');
  const minute = String(now.getMinutes()).padStart(2, '0');
  const second = String(now.getSeconds()).padStart(2, '0');
  
  return `${year}${month}${day}_${hour}${minute}${second}`;
};

// Try to get build info from environment variables (set during build)
const getBuildInfo = () => {
  // React apps can access environment variables that start with REACT_APP_
  const buildTimestamp = process.env.REACT_APP_BUILD_TIMESTAMP || generateBuildTimestamp();
  const buildVersion = process.env.REACT_APP_BUILD_VERSION || 'development';
  const gitCommit = process.env.REACT_APP_GIT_COMMIT || 'unknown';
  const buildDescription = process.env.REACT_APP_BUILD_DESCRIPTION || 'AUTO_GENERATED';
  
  return {
    timestamp: buildTimestamp,
    version: buildVersion,
    gitCommit: gitCommit.substring(0, 8), // Short commit hash
    description: buildDescription,
    fullVersion: `build_${buildTimestamp}_${buildDescription}`
  };
};

export const buildInfo = getBuildInfo();
export default buildInfo;