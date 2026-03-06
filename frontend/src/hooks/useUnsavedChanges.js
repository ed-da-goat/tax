import { useEffect, useCallback, useRef } from 'react';
import { useBlocker } from 'react-router-dom';

/**
 * Hook to warn users about unsaved changes when navigating away.
 *
 * @param {boolean} isDirty - Whether the form has unsaved changes
 * @param {string} message - Warning message (used for browser beforeunload)
 */
export default function useUnsavedChanges(isDirty, message = 'You have unsaved changes. Are you sure you want to leave?') {
  // Browser tab/window close
  useEffect(() => {
    if (!isDirty) return;
    function handleBeforeUnload(e) {
      e.preventDefault();
      e.returnValue = message;
      return message;
    }
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty, message]);

  // React Router navigation
  const blocker = useBlocker(
    useCallback(() => isDirty, [isDirty])
  );

  useEffect(() => {
    if (blocker.state === 'blocked') {
      const confirmed = window.confirm(message);
      if (confirmed) {
        blocker.proceed();
      } else {
        blocker.reset();
      }
    }
  }, [blocker, message]);

  return blocker;
}
