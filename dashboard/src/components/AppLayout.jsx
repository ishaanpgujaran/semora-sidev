/**
 * @file AppLayout.jsx
 * @description Authenticated shell layout with a persistent left sidebar for navigation
 * between the three dashboard views (Portfolio, Timeline, Spec Matrix).
 */

import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { signOut } from 'firebase/auth';
import { auth } from '../firebase/config';
import { LayoutGrid, Clock, Table2, LogOut } from 'lucide-react';

const navItems = [
  { to: '/portfolio', label: 'Portfolio', icon: LayoutGrid },
  { to: '/timeline', label: 'Audit Timeline', icon: Clock },
  { to: '/matrix', label: 'Spec Matrix', icon: Table2 },
];

export default function AppLayout() {
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await signOut(auth);
    navigate('/login');
  };

  return (
    <div className="flex min-h-screen bg-zinc-50 font-sans">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-white border-r border-zinc-200 flex flex-col">
        <div className="px-6 py-6 border-b border-zinc-100">
          <a href="/" className="font-serif text-xl font-semibold tracking-tight text-zinc-900 hover:opacity-80 transition-opacity">
            Semora
          </a>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-zinc-100 text-zinc-900'
                    : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
                }`
              }
            >
              <Icon size={16} className="flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-zinc-100">
          <button
            type="button"
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 transition-colors"
          >
            <LogOut size={16} className="flex-shrink-0" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 px-12 py-12 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
