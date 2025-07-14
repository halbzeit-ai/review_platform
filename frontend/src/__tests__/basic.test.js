/**
 * Basic test to verify test setup
 */

describe('Basic Test Setup', () => {
  it('should run basic tests', () => {
    expect(true).toBe(true);
  });

  it('should have access to localStorage mock', () => {
    localStorage.setItem('test', 'value');
    expect(localStorage.getItem('test')).toBe('value');
  });

  it('should have access to basic utilities', () => {
    const testArray = [1, 2, 3];
    expect(testArray.length).toBe(3);
  });
});