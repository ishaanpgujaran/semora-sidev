/**
 * @file useFirestoreLive.js
 * @description Custom hook that wraps Firestore's onSnapshot listener to provide
 * real-time updates from the users/{uid}/runs collection. New CLI runs surface in
 * the UI within seconds with no manual refresh required.
 */

import { useState, useEffect } from 'react';
import { collection, query, orderBy, onSnapshot } from 'firebase/firestore';
import { db } from '../firebase/config';

/**
 * Subscribes to all runs for a given user in real time via Firestore's onSnapshot.
 *
 * @param {string|null} uid - The Firebase user ID. Hook is a no-op when null.
 * @returns {{ runs: Array, loading: boolean, error: string|null }}
 */
export function useFirestoreLive(uid) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!uid) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    const runsRef = collection(db, 'users', uid, 'runs');
    const q = query(runsRef, orderBy('timestamp', 'desc'));

    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        const data = snapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
          // Normalise the Firestore Timestamp into a JS Date for convenience
          timestamp: doc.data().timestamp?.toDate?.() ?? null,
        }));
        setRuns(data);
        setLoading(false);
      },
      (err) => {
        console.error('[useFirestoreLive] onSnapshot error:', err);
        setError('Failed to load run data. Please refresh.');
        setLoading(false);
      }
    );

    // Cleanup: unsubscribe when the component unmounts or uid changes.
    return () => unsubscribe();
  }, [uid]);

  return { runs, loading, error };
}
