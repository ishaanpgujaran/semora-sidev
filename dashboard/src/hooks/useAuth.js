/**
 * @file useAuth.js
 * @description Custom hook that subscribes to Firebase Auth's onAuthStateChanged,
 * returning the current user object (or null) and a loading flag.
 * Used by all authenticated pages to access the current user's uid.
 */

import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../firebase/config';

/**
 * @returns {{ user: import('firebase/auth').User|null, authLoading: boolean }}
 */
export function useAuth() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setAuthLoading(false);
    });
    return () => unsubscribe();
  }, []);

  return { user, authLoading };
}
