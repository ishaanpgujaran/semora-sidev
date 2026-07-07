/**
 * @file LandingPage.jsx
 * @description Renders the public welcome landing page explaining Semora capabilities.
 */

import React from 'react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Navigation */}
      <nav className="max-w-6xl mx-auto px-6 py-8 flex justify-between items-center">
        <div className="font-serif text-2xl font-semibold tracking-tight text-zinc-900">
          Semora
        </div>
        <div className="flex gap-6 items-center text-sm font-medium text-zinc-600">
          <a href="/docs" className="hover:text-zinc-900 transition-colors">Documentation</a>
          <a href="/login" className="hover:text-zinc-900 transition-colors">Sign In</a>
          <a href="/signup" className="bg-zinc-900 text-zinc-50 px-5 py-2.5 rounded-md hover:bg-zinc-800 transition-colors">
            Get Started
          </a>
        </div>
      </nav>

      {/* Hero Section */}
      <main>
        <section className="max-w-4xl mx-auto px-6 pt-32 pb-24 text-center">
          <h1 className="font-serif text-5xl md:text-6xl font-normal leading-tight text-zinc-900 mb-8">
            The quality gate for <br className="hidden md:block" /> AI-assisted vibe coding.
          </h1>
          <p className="text-lg md:text-xl text-zinc-600 max-w-2xl mx-auto leading-relaxed mb-12">
            Writing code with AI is incredibly fast, but often lacks formal testing or security review. 
            Semora acts as an autonomous local CI, catching vulnerabilities and generating specs before your code ever leaves your machine.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a href="/signup" className="bg-blue-600 text-white px-8 py-3.5 rounded-md font-medium hover:bg-blue-700 transition-colors w-full sm:w-auto">
              Start Free Trial
            </a>
            <a href="/docs" className="text-zinc-900 border border-zinc-300 px-8 py-3.5 rounded-md font-medium hover:bg-zinc-100 transition-colors w-full sm:w-auto">
              Read the Documentation
            </a>
          </div>
        </section>

        {/* How it Works Section */}
        <section className="max-w-6xl mx-auto px-6 py-24 border-t border-zinc-200">
          <div className="text-center mb-16">
            <h2 className="font-serif text-3xl text-zinc-900 mb-4">How it Works</h2>
            <p className="text-zinc-600">A seamless integration into your existing workflow.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
            {/* Connecting Line (visible on md+) */}
            <div className="hidden md:block absolute top-1/2 left-0 w-full h-[1px] bg-zinc-200 -z-10 translate-y-[-50%]"></div>

            {/* Step 1 */}
            <div className="bg-zinc-50 flex flex-col items-center text-center p-6">
              <div className="w-12 h-12 bg-white border border-zinc-200 rounded-full flex items-center justify-center text-zinc-900 font-serif text-xl mb-6 shadow-sm z-10">
                1
              </div>
              <h3 className="text-lg font-medium text-zinc-900 mb-3">Commit</h3>
              <p className="text-zinc-600 leading-relaxed text-sm">
                You write code with your favorite AI tools and run <code>git commit</code>. Semora's local hook intercepts the changes.
              </p>
            </div>

            {/* Step 2 */}
            <div className="bg-zinc-50 flex flex-col items-center text-center p-6">
              <div className="w-12 h-12 bg-blue-50 border border-blue-200 rounded-full flex items-center justify-center text-blue-700 font-serif text-xl mb-6 shadow-sm z-10">
                2
              </div>
              <h3 className="text-lg font-medium text-zinc-900 mb-3">Agent Graph Analyzes</h3>
              <p className="text-zinc-600 leading-relaxed text-sm">
                An autonomous agent graph performs STRIDE threat modeling and generates BDD specifications in an isolated sandbox.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-zinc-50 flex flex-col items-center text-center p-6">
              <div className="w-12 h-12 bg-white border border-zinc-200 rounded-full flex items-center justify-center text-zinc-900 font-serif text-xl mb-6 shadow-sm z-10">
                3
              </div>
              <h3 className="text-lg font-medium text-zinc-900 mb-3">Compliance Report</h3>
              <p className="text-zinc-600 leading-relaxed text-sm">
                Review the generated specs and security audit directly in the terminal, synced live to your project dashboard.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200 mt-12 py-12">
        <div className="max-w-6xl mx-auto px-6 text-center text-sm text-zinc-500">
          &copy; {new Date().getFullYear()} Semora. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
