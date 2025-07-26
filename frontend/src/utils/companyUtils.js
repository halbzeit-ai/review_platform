import { getCompanyInfo } from '../services/api';

/**
 * Get the company ID and dashboard path for the current user
 * This function calls the backend to ensure consistent company ID generation
 * @returns {Promise<{companyId: string, dashboardPath: string, companyName: string}>}
 */
export const getCurrentUserCompanyInfo = async () => {
  try {
    const response = await getCompanyInfo();
    return response.data;
  } catch (error) {
    console.error('Failed to get company info from backend:', error);
    
    // Fallback to local generation if API fails
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    return getCompanyInfoFallback(user);
  }
};

/**
 * Fallback function for generating company info locally
 * Should match the backend logic exactly
 * @param {Object} user - User object from localStorage
 * @returns {Object} Company info object
 */
export const getCompanyInfoFallback = (user) => {
  const getCompanyId = () => {
    if (user?.companyName) {
      // Convert company name to a URL-safe slug - same logic as backend
      return user.companyName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    }
    // Fallback to email prefix if company name is not available
    return user?.email?.split('@')[0] || 'unknown';
  };

  const companyId = getCompanyId();
  
  return {
    company_name: user.companyName,
    company_id: companyId,
    dashboard_path: user.role === 'startup' ? `/project/${companyId}` : '/dashboard/gp'
  };
};

/**
 * Synchronous function to get company ID from user data
 * Use this only when you can't make async calls
 * @param {Object} user - User object from localStorage
 * @returns {string} Company ID
 */
export const getCompanyIdSync = (user) => {
  if (user?.companyName) {
    return user.companyName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  }
  return user?.email?.split('@')[0] || 'unknown';
};