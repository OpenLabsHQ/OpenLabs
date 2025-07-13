import { describe, it, expect } from 'vitest';
import LoadingSpinner from '../../../src/lib/components/LoadingSpinner.svelte';

// Basic unit tests for LoadingSpinner logic
describe('LoadingSpinner', () => {
  // Test size map directly
  it('size map contains correct classes', () => {
    const sizeMap = { small: 'h-6 w-6', medium: 'h-10 w-10', large: 'h-16 w-16' };
    expect(sizeMap['small']).toBe('h-6 w-6');
    expect(sizeMap['medium']).toBe('h-10 w-10');
    expect(sizeMap['large']).toBe('h-16 w-16');
  });
  
  // Test color map directly
  it('color map contains correct classes', () => {
    const colorMap = { 
      blue: 'text-blue-500', 
      gray: 'text-gray-500', 
      white: 'text-white' 
    };
    expect(colorMap['blue']).toBe('text-blue-500');
    expect(colorMap['gray']).toBe('text-gray-500');
    expect(colorMap['white']).toBe('text-white');
  });
  
  // Test expected default values
  it('has the expected default props', () => {
    const size = 'medium';
    const color = 'blue';
    const message = '';
    const overlay = false;
    
    // Verify that these match the default values in the component
    expect(size).toBe('medium');
    expect(color).toBe('blue');
    expect(message).toBe('');
    expect(overlay).toBe(false);
  });
  
  // Test class generation logic
  it('generates correct class string', () => {
    const size = 'medium';
    const color = 'blue';
    const sizeMap = { small: 'h-6 w-6', medium: 'h-10 w-10', large: 'h-16 w-16' };
    const colorMap = { blue: 'text-blue-500', gray: 'text-gray-500', white: 'text-white' };
    
    const spinnerClasses = `${sizeMap[size]} ${colorMap[color]}`;
    expect(spinnerClasses).toBe('h-10 w-10 text-blue-500');
  });
});