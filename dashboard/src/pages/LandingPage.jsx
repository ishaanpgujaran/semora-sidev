/**
 * @file LandingPage.jsx
 * @description Renders the public welcome landing page explaining Semora capabilities.
 */

import React from 'react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-blue-100 selection:text-blue-900">

      {/* Navigation */}
      <nav className="max-w-6xl mx-auto px-8 py-7 flex justify-between items-center">
        <div className="font-serif text-xl font-semibold tracking-tight text-zinc-900">
          Semora
        </div>
        <div className="flex gap-8 items-center text-sm font-medium text-zinc-500">
          <a href="/docs" className="hover:text-zinc-900 transition-colors duration-150">Documentation</a>
          <a href="/login" className="hover:text-zinc-900 transition-colors duration-150">Sign In</a>
          <a
            href="/signup"
            className="bg-zinc-900 text-zinc-50 px-5 py-2 rounded hover:bg-zinc-700 transition-colors duration-150"
          >
            Get Started
          </a>
        </div>
      </nav>

      {/* Hero */}
      <main>
        <section className="max-w-4xl mx-auto px-8 pt-28 pb-24 text-center">
          <h1 className="font-serif text-5xl md:text-6xl font-normal leading-[1.15] tracking-tight text-zinc-900 mb-7">
            The quality gate for<br className="hidden md:block" /> AI-assisted vibe coding.
          </h1>
          <p className="text-lg text-zinc-500 max-w-2xl mx-auto leading-relaxed mb-12">
            Writing code with AI is fast, but often without formal testing or security review.
            Semora acts as an autonomous local CI, catching vulnerabilities and generating specs
            before your code ever leaves your machine.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
            <a
              href="/signup"
              className="bg-blue-600 text-white px-7 py-3 rounded font-medium text-sm hover:bg-blue-700 transition-colors duration-150 w-full sm:w-auto"
            >
              Start Free Trial
            </a>
            <a
              href="/docs"
              className="text-zinc-800 border border-zinc-300 px-7 py-3 rounded font-medium text-sm hover:bg-zinc-100 transition-colors duration-150 w-full sm:w-auto"
            >
              Read the Documentation
            </a>
          </div>
        </section>

        {/* How it Works */}
        <section className="max-w-6xl mx-auto px-8 py-24 border-t border-zinc-200">
          <div className="text-center mb-16">
            <h2 className="font-serif text-3xl font-normal text-zinc-900 mb-3">How it Works</h2>
            <p className="text-zinc-500 text-base">A seamless integration into your existing workflow.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10 relative">
            {/* Connecting line */}
            <div
              className="hidden md:block absolute top-8 left-[16.67%] right-[16.67%] h-px bg-zinc-200 -z-10"
              aria-hidden="true"
            />

            {[
              {
                n: '1',
                title: 'Commit',
                body: <>You write code with your favorite AI tools and run <code className="font-mono text-xs bg-zinc-100 px-1.5 py-0.5 rounded">git commit</code>. Semora's hook intercepts the changes.</>,
                accent: false,
              },
              {
                n: '2',
                title: 'Agent Graph Analyzes',
                body: 'An autonomous agent graph performs STRIDE threat modeling and generates BDD specifications in an isolated sandbox.',
                accent: true,
              },
              {
                n: '3',
                title: 'Compliance Report',
                body: 'Review the generated specs and security audit in the terminal, synced live to your project dashboard.',
                accent: false,
              },
            ].map(({ n, title, body, accent }) => (
              <div key={n} className="flex flex-col items-center text-center px-4">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-serif text-base mb-6 z-10 border ${
                    accent
                      ? 'bg-blue-50 border-blue-200 text-blue-700'
                      : 'bg-white border-zinc-200 text-zinc-700'
                  }`}
                >
                  {n}
                </div>
                <h3 className="text-base font-medium text-zinc-900 mb-2">{title}</h3>
                <p className="text-sm text-zinc-500 leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200 py-10 mt-auto">
        <div className="max-w-6xl mx-auto px-8 text-center text-sm text-zinc-400">
          &copy; {new Date().getFullYear()} Semora. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
