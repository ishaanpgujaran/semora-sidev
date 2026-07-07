/**
 * @file DocsPage.jsx
 * @description Renders documentation guides detailing CLI settings, setup steps, and STRIDE concepts.
 */

import React from 'react';

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-blue-100 selection:text-blue-900">

      {/* Navigation — matches LandingPage exactly */}
      <nav className="max-w-6xl mx-auto px-8 py-7 flex justify-between items-center">
        <a
          href="/"
          className="font-serif text-xl font-semibold tracking-tight text-zinc-900 hover:opacity-75 transition-opacity duration-150"
        >
          Semora
        </a>
        <div className="flex gap-8 items-center text-sm font-medium text-zinc-500">
          <a href="/docs" className="text-zinc-900">Documentation</a>
          <a href="/login" className="hover:text-zinc-900 transition-colors duration-150">Sign In</a>
        </div>
      </nav>

      {/* Docs Content */}
      <main className="max-w-2xl mx-auto px-8 pt-16 pb-28">

        <header className="mb-16 border-b border-zinc-200 pb-10">
          <h1 className="font-serif text-4xl md:text-5xl font-normal tracking-tight text-zinc-900 mb-4">
            Quick Start
          </h1>
          <p className="text-base text-zinc-500 leading-relaxed">
            Get Semora running in your repository in under two minutes.
          </p>
        </header>

        <ol className="space-y-14">

          {/* Step 1 */}
          <li className="flex gap-6">
            <span className="flex-shrink-0 mt-0.5 w-7 h-7 rounded-full bg-zinc-900 text-zinc-50 font-serif text-sm flex items-center justify-center">
              1
            </span>
            <div className="flex-1 min-w-0">
              <h2 className="font-serif text-xl text-zinc-900 mb-3">Prerequisites</h2>
              <ul className="space-y-2 text-sm text-zinc-600">
                <li className="flex gap-2">
                  <span className="text-zinc-300 mt-0.5">—</span>
                  <span><strong className="text-zinc-800">Python 3.11+</strong> installed on your machine.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-zinc-300 mt-0.5">—</span>
                  <span><strong className="text-zinc-800">Git</strong> initialized in your target repository.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-zinc-300 mt-0.5">—</span>
                  <span>A free <strong className="text-zinc-800">Gemini API key</strong> from Google AI Studio.</span>
                </li>
              </ul>
            </div>
          </li>

          {/* Step 2 */}
          <li className="flex gap-6">
            <span className="flex-shrink-0 mt-0.5 w-7 h-7 rounded-full bg-zinc-900 text-zinc-50 font-serif text-sm flex items-center justify-center">
              2
            </span>
            <div className="flex-1 min-w-0">
              <h2 className="font-serif text-xl text-zinc-900 mb-3">Installation</h2>
              <p className="text-sm text-zinc-500 mb-3">Install the Semora CLI via pip:</p>
              <pre className="bg-zinc-900 text-zinc-100 px-5 py-4 rounded text-sm font-mono leading-relaxed overflow-x-auto">
pip install semora</pre>
            </div>
          </li>

          {/* Step 3 */}
          <li className="flex gap-6">
            <span className="flex-shrink-0 mt-0.5 w-7 h-7 rounded-full bg-zinc-900 text-zinc-50 font-serif text-sm flex items-center justify-center">
              3
            </span>
            <div className="flex-1 min-w-0">
              <h2 className="font-serif text-xl text-zinc-900 mb-3">Initialize Repository</h2>
              <p className="text-sm text-zinc-500 mb-3">Navigate to your project directory and run:</p>
              <pre className="bg-zinc-900 text-zinc-100 px-5 py-4 rounded text-sm font-mono leading-relaxed overflow-x-auto mb-4">
semora init</pre>
              <p className="text-sm text-zinc-500 bg-zinc-100 px-4 py-3 rounded border border-zinc-200 leading-relaxed">
                <strong className="text-zinc-700">Note:</strong> This installs a git pre-commit hook that intercepts each commit
                to run the autonomous CI gate before it is finalized.
              </p>
            </div>
          </li>

          {/* Step 4 */}
          <li className="flex gap-6">
            <span className="flex-shrink-0 mt-0.5 w-7 h-7 rounded-full bg-zinc-900 text-zinc-50 font-serif text-sm flex items-center justify-center">
              4
            </span>
            <div className="flex-1 min-w-0">
              <h2 className="font-serif text-xl text-zinc-900 mb-3">Connect to Dashboard</h2>
              <p className="text-sm text-zinc-500 mb-3">Sync your local runs to the web dashboard:</p>
              <pre className="bg-zinc-900 text-zinc-100 px-5 py-4 rounded text-sm font-mono leading-relaxed overflow-x-auto mb-2">
semora login</pre>
              <p className="text-sm text-zinc-500">You will be prompted for your Semora email and password.</p>
            </div>
          </li>

          {/* Step 5 */}
          <li className="flex gap-6">
            <span className="flex-shrink-0 mt-0.5 w-7 h-7 rounded-full bg-zinc-900 text-zinc-50 font-serif text-sm flex items-center justify-center">
              5
            </span>
            <div className="flex-1 min-w-0">
              <h2 className="font-serif text-xl text-zinc-900 mb-3">Run a Manual Check</h2>
              <p className="text-sm text-zinc-500 mb-3">To trigger a CI run without committing:</p>
              <pre className="bg-zinc-900 text-zinc-100 px-5 py-4 rounded text-sm font-mono leading-relaxed overflow-x-auto">
semora run</pre>
            </div>
          </li>

        </ol>
      </main>

      {/* Footer — matches LandingPage */}
      <footer className="border-t border-zinc-200 py-10">
        <div className="max-w-6xl mx-auto px-8 text-center text-sm text-zinc-400">
          &copy; {new Date().getFullYear()} Semora. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
