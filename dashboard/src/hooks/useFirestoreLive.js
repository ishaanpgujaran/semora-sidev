/**
 * @file useFirestoreLive.js
 * @description React hook triggering subscription listeners to receive real-time updates from Firestore.
 */

import { useState, useEffect } from 'react';

export default function useFirestoreLive(collectionPath) {
  const [data, setData] = useState([]);

  useEffect(() => {
    // TODO(frontend-agent): Implement firestore onSnapshot listener.
  }, [collectionPath]);

  return data;
}
