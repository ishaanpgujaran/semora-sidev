/**
 * @file ProtectedRoute.jsx
 * @description Redirects unauthenticated users to /login before they can access
 * any authenticated route. Uses useAuth to read Firebase Auth state.
 */

import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function ProtectedRoute() {
  const { user, authLoading } = useAuth();

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-zinc-400 font-sans">
        Authenticating…
      </div>
    );
  }

  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
