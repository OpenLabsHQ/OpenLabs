// Keyboard navigation utilities

/**
 * Check if an element is focusable
 */
export function isFocusable(element: Element): boolean {
  const focusableSelectors = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable]'
  ];

  return focusableSelectors.some(selector => 
    element.matches(selector) || element.querySelector(selector) !== null
  );
}

/**
 * Get all focusable elements within a container
 */
export function getFocusableElements(container: Element): Element[] {
  const focusableSelectors = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable]'
  ].join(', ');

  return Array.from(container.querySelectorAll(focusableSelectors));
}

/**
 * Focus the first focusable element in a container
 */
export function focusFirst(container: Element): boolean {
  const focusableElements = getFocusableElements(container);
  if (focusableElements.length > 0) {
    (focusableElements[0] as HTMLElement).focus();
    return true;
  }
  return false;
}

/**
 * Focus the last focusable element in a container
 */
export function focusLast(container: Element): boolean {
  const focusableElements = getFocusableElements(container);
  if (focusableElements.length > 0) {
    (focusableElements[focusableElements.length - 1] as HTMLElement).focus();
    return true;
  }
  return false;
}

/**
 * Trap focus within a container (useful for modals)
 */
export function trapFocus(container: Element, event: KeyboardEvent): void {
  if (event.key !== 'Tab') return;

  const focusableElements = getFocusableElements(container);
  if (focusableElements.length === 0) return;

  const firstElement = focusableElements[0] as HTMLElement;
  const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

  if (event.shiftKey) {
    // Shift + Tab: moving backwards
    if (document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
    }
  } else {
    // Tab: moving forwards
    if (document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  }
}

/**
 * Handle arrow key navigation in a list or grid
 */
export function handleArrowKeyNavigation(
  event: KeyboardEvent,
  container: Element,
  orientation: 'horizontal' | 'vertical' | 'grid' = 'vertical'
): void {
  const focusableElements = getFocusableElements(container);
  if (focusableElements.length === 0) return;

  const currentIndex = focusableElements.findIndex(el => el === document.activeElement);
  if (currentIndex === -1) return;

  let nextIndex = currentIndex;

  switch (event.key) {
    case 'ArrowDown':
      if (orientation === 'vertical' || orientation === 'grid') {
        event.preventDefault();
        nextIndex = Math.min(currentIndex + 1, focusableElements.length - 1);
      }
      break;
    case 'ArrowUp':
      if (orientation === 'vertical' || orientation === 'grid') {
        event.preventDefault();
        nextIndex = Math.max(currentIndex - 1, 0);
      }
      break;
    case 'ArrowRight':
      if (orientation === 'horizontal' || orientation === 'grid') {
        event.preventDefault();
        nextIndex = Math.min(currentIndex + 1, focusableElements.length - 1);
      }
      break;
    case 'ArrowLeft':
      if (orientation === 'horizontal' || orientation === 'grid') {
        event.preventDefault();
        nextIndex = Math.max(currentIndex - 1, 0);
      }
      break;
    case 'Home':
      event.preventDefault();
      nextIndex = 0;
      break;
    case 'End':
      event.preventDefault();
      nextIndex = focusableElements.length - 1;
      break;
  }

  if (nextIndex !== currentIndex) {
    (focusableElements[nextIndex] as HTMLElement).focus();
  }
}

/**
 * Create a roving tabindex for a group of elements
 */
export function createRovingTabindex(container: Element): () => void {
  const focusableElements = getFocusableElements(container);
  
  // Set initial tabindex values
  focusableElements.forEach((element, index) => {
    element.setAttribute('tabindex', index === 0 ? '0' : '-1');
  });

  function handleKeyDown(event: KeyboardEvent) {
    handleArrowKeyNavigation(event, container);
    
    // Update tabindex when focus changes
    if (['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      focusableElements.forEach(element => {
        element.setAttribute('tabindex', element === document.activeElement ? '0' : '-1');
      });
    }
  }

  function handleFocus(event: Event) {
    // Update tabindex when focus changes via mouse or other means
    focusableElements.forEach(element => {
      element.setAttribute('tabindex', element === event.target ? '0' : '-1');
    });
  }

  container.addEventListener('keydown', handleKeyDown);
  container.addEventListener('focus', handleFocus, true);

  // Return cleanup function
  return () => {
    container.removeEventListener('keydown', handleKeyDown);
    container.removeEventListener('focus', handleFocus, true);
  };
}

/**
 * Escape key handler
 */
export function onEscape(callback: () => void) {
  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      callback();
    }
  }

  document.addEventListener('keydown', handleKeyDown);

  return () => {
    document.removeEventListener('keydown', handleKeyDown);
  };
}