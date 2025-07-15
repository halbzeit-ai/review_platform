// Debug script to run in browser console to check localStorage
// Open browser dev tools (F12) and paste this in console

console.log("=== DEBUGGING FRONTEND AUTHENTICATION ===");

// Check what's in localStorage
console.log("1. localStorage contents:");
console.log("   All keys:", Object.keys(localStorage));
console.log("   User data:", localStorage.getItem('user'));
console.log("   Token direct:", localStorage.getItem('token'));

// Try to parse user data
try {
  const user = JSON.parse(localStorage.getItem('user'));
  console.log("2. Parsed user object:", user);
  console.log("   Token from user:", user?.token);
} catch (e) {
  console.log("2. Error parsing user data:", e);
}

// Check if token is valid format
const user = JSON.parse(localStorage.getItem('user'));
const token = user?.token;
if (token) {
  console.log("3. Token analysis:");
  console.log("   Token length:", token.length);
  console.log("   Token starts with:", token.substring(0, 20) + "...");
  console.log("   Token format valid:", token.startsWith('eyJ'));
} else {
  console.log("3. No token found!");
}

// Test API call with token
if (token) {
  console.log("4. Testing API call...");
  fetch('/api/documents/processing-status/9', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  .then(response => {
    console.log("   API response status:", response.status);
    return response.json();
  })
  .then(data => {
    console.log("   API response data:", data);
  })
  .catch(error => {
    console.log("   API error:", error);
  });
}

console.log("=== DEBUG COMPLETE ===");
console.log("Run this after logging in to see token storage");