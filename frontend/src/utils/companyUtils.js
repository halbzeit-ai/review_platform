import { getCompanyInfo, getDashboardInfo, getUserProjects } from '../services/api';

/**
 * Get the routing information for the current user
 * Uses clean API separation: company info vs dashboard routing
 * @returns {Promise<{companyId: string, dashboardPath: string, companyName: string, projectId?: number}>}
 */
export const getCurrentUserCompanyInfo = async () => {
  try {
    // Get dashboard routing information (clean API)
    const dashboardResponse = await getDashboardInfo();
    const dashboardData = dashboardResponse.data;
    
    if (dashboardData.user_type === "startup_with_project") {
      // For startup users with project membership - use project ID routing
      return {
        dashboard_path: dashboardData.dashboard_path,
        project_id: dashboardData.project_id,
        project_name: dashboardData.project_name,
        company_id: null, // Not needed for project routing
        company_name: dashboardData.project_name // Use project name as display name
      };
    } else {
      // For GPs or startup users without projects - use standard routing
      return {
        dashboard_path: dashboardData.dashboard_path,
        user_type: dashboardData.user_type,
        message: dashboardData.message
      };
    }
  } catch (error) {
    console.error('Failed to get company info from backend:', error);
    
    // Fallback to local generation if API fails
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    return getCompanyInfoFallback(user);
  }
};

/**
 * Get all projects the current user is a member of
 * @returns {Promise<{projects: Array, totalProjects: number, primaryProject: Object}>}
 */
export const getCurrentUserProjects = async () => {
  try {
    const response = await getUserProjects();
    return response.data;
  } catch (error) {
    console.error('Failed to get user projects from backend:', error);
    throw error; // Let caller handle this error
  }
};

/**
 * Fallback function for generating company info locally
 * NOTE: This fallback still uses company_id for compatibility but ideally 
 * the backend should always be available to provide proper project_id routing
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
    // FALLBACK: Still use company_id when backend is unavailable
    // The backend should provide proper project_id routing when available
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