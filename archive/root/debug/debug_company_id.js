// Debug script to check company ID generation
// Run this in the browser console while logged in

console.log('=== Company ID Debug ===');

// Get user data from localStorage
const user = JSON.parse(localStorage.getItem('user') || '{}');
console.log('User data:', user);

// Frontend company ID generation logic
const getCompanyId = () => {
  if (user?.companyName) {
    console.log('Using company name:', user.companyName);
    const result = user.companyName.toLowerCase().replace(' ', '-').replace(/[^a-z0-9-]/g, '');
    console.log('Generated company ID:', result);
    return result;
  }
  console.log('No company name, using email fallback');
  const fallback = user?.email?.split('@')[0] || 'unknown';
  console.log('Fallback company ID:', fallback);
  return fallback;
};

const companyId = getCompanyId();
console.log('Final company ID:', companyId);
console.log('Current URL should be:', `/project/${companyId}`);
console.log('Current actual URL:', window.location.pathname);