/**
 * @file DocsPage.jsx
 * @description Renders documentation guides detailing CLI settings, setup steps, and STRIDE concepts.
 */

import React from 'react';

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Navigation */}
      <nav className="max-w-4xl mx-auto px-6 py-8 flex justify-between items-center border-b border-zinc-200">
        <a href="/" className="font-serif text-2xl font-semibold tracking-tight text-zinc-900 hover:opacity-80 transition-opacity">
          Semora
        </a>
        <div className="flex gap-6 items-center text-sm font-medium text-zinc-600">
          <a href="/docs" className="text-zinc-900 transition-colors">Documentation</a>
          <a href="/login" className="hover:text-zinc-900 transition-colors">Sign In</a>
        </div>
      </nav>

      {/* Docs Content */}
      <main className="max-w-3xl mx-auto px-6 py-16">
        <header className="mb-16">
          <h1 className="font-serif text-4xl md:text-5xl text-zinc-900 mb-4">Quick Start</h1>
          <p className="text-lg text-zinc-600">Get Semora running in your repository in under two minutes.</p>
        </header>

        <div className="space-y-12">
          
          {/* Step 1: Prerequisites */}
          <section>
            <div className="flex items-center gap-4 mb-4">
              <span className="flex-shrink-0 w-8 h-8 rounded bg-zinc-200 text-zinc-900 font-serif font-medium flex items-center justify-center">1</span>
              <h2 className="font-serif text-2xl text-zinc-900">Prerequisites</h2>
            </div>
            <ul className="list-disc list-inside text-zinc-600 space-y-2 ml-12">
              <li><strong>Python 3.11+</strong> installed on your machine.</li>
              <li><strong>Git</strong> initialized in your target repository.</li>
              <li>A free <strong>Gemini API key</strong> from Google AI Studio.</li>
            </ul>
          </section>

          {/* Step 2: Installation */}
          <section>
            <div className="flex items-center gap-4 mb-4">
              <span className="flex-shrink-0 w-8 h-8 rounded bg-zinc-200 text-zinc-900 font-serif font-medium flex items-center justify-center">2</span>
              <h2 className="font-serif text-2xl text-zinc-900">Installation</h2>
            </div>
            <div className="ml-12">
              <p className="text-zinc-600 mb-2">Install the Semora CLI globally via pip:</p>
              <pre className="bg-zinc-900 text-zinc-100 p-4 rounded-md overflow-x-auto text-sm font-mono">
                <code>pip install semora</code>
              </pre>
            </div>
          </section>

          {/* Step 3: Initial Setup */}
          <section>
            <div className="flex items-center gap-4 mb-4">
              <span className="flex-shrink-0 w-8 h-8 rounded bg-zinc-200 text-zinc-900 font-serif font-medium flex items-center justify-center">3</span>
              <h2 className="font-serif text-2xl text-zinc-900">Initialize Repository</h2>
            </div>
            <div className="ml-12">
              <p className="text-zinc-600 mb-2">Navigate to your project directory and run:</p>
              <pre className="bg-zinc-900 text-zinc-100 p-4 rounded-md overflow-x-auto text-sm font-mono mb-4">
                <code>semora init</code>
              </pre>
              <p className="text-sm text-zinc-500 bg-zinc-100 p-3 rounded border border-zinc-200">
                <strong>Note:</strong> This automatically installs a git pre-commit hook that intercepts your commits to run the autonomous CI gate before they are finalized.
              </p>
            </div>
          </section>

          {/* Step 4: Connect Dashboard */}
          <section>
            <div className="flex items-center gap-4 mb-4">
              <span className="flex-shrink-0 w-8 h-8 rounded bg-zinc-200 text-zinc-900 font-serif font-medium flex items-center justify-center">4</span>
              <h2 className="font-serif text-2xl text-zinc-900">Connect to Dashboard</h2>
            </div>
            <div className="ml-12">
              <p className="text-zinc-600 mb-2">Sync your local runs to the web dashboard:</p>
              <pre className="bg-zinc-900 text-zinc-100 p-4 rounded-md overflow-x-auto text-sm font-mono mb-2">
                <code>semora login</code>
              </pre>
              <p className="text-sm text-zinc-500">You will be prompted to enter your Semora email and password.</p>
            </div>
          </section>

          {/* Step 5: Manual Check */}
          <section>
            <div className="flex items-center gap-4 mb-4">
              <span className="flex-shrink-0 w-8 h-8 rounded bg-zinc-200 text-zinc-900 font-serif font-medium flex items-center justify-center">5</span>
              <h2 className="font-serif text-2xl text-zinc-900">Run a Manual Check</h2>
            </div>
            <div className="ml-12">
              <p className="text-zinc-600 mb-2">To trigger a CI run manually without committing:</p>
              <pre className="bg-zinc-900 text-zinc-100 p-4 rounded-md overflow-x-auto text-sm font-mono">
                <code>semora run</code>
              </pre>
            </div>
          </section>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200 py-12 mt-12">
        <div className="max-w-4xl mx-auto px-6 text-center text-sm text-zinc-500">
          &copy; {new Date().getFullYear()} Semora. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
