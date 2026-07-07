/**
 * @file ProjectPortfolio.jsx
 * @description Lists repositories and showcases general compliance score graphs across codebases.
 * Reads live from users/{uid}/runs via useFirestoreLive and groups runs by repo_name.
 */

import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useFirestoreLive } from '../hooks/useFirestoreLive';
import { GitBranch, Clock, ArrowRight, ShieldCheck } from 'lucide-react';

function ScorePill({ score }) {
  let colorClass = 'bg-red-100 text-red-700';
  if (score >= 85) colorClass = 'bg-green-100 text-green-700';
  else if (score >= 60) colorClass = 'bg-amber-100 text-amber-700';
  return (
    <span className={`inline-flex items-center gap-1 text-sm font-medium px-2.5 py-1 rounded-full ${colorClass}`}>
      <ShieldCheck size={13} />
      {score}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-24 text-zinc-500">
      <GitBranch size={36} className="mx-auto mb-4 text-zinc-300" />
      <p className="font-medium text-zinc-700 mb-1">No runs yet</p>
      <p className="text-sm">Run <code className="bg-zinc-100 px-1 rounded">semora run</code> in your project to see data here.</p>
    </div>
  );
}

export default function ProjectPortfolio() {
  const { user } = useAuth();
  const { runs, loading, error } = useFirestoreLive(user?.uid);

  const projects = useMemo(() => {
    const map = {};
    for (const run of runs) {
      const repo = run.repo_name ?? 'Unknown Repository';
      if (!map[repo]) {
        map[repo] = { repo_name: repo, runs: [] };
      }
      map[repo].runs.push(run);
    }
    return Object.values(map).map((proj) => {
      const latest = proj.runs[0]; // already ordered desc by timestamp
      return {
        ...proj,
        latestScore: latest?.compliance_score ?? null,
        latestTimestamp: latest?.timestamp ?? null,
        runCount: proj.runs.length,
      };
    });
  }, [runs]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-400">
        Loading projects…
      </div>
    );
  }

  return (
    <div>
      <header className="mb-10">
        <h1 className="font-serif text-3xl text-zinc-900 mb-2">Project Portfolio</h1>
        <p className="text-zinc-600">All repositories synced to your Semora account.</p>
      </header>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
          {error}
        </div>
      )}

      {projects.length === 0 && !error && <EmptyState />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {projects.map((proj) => (
          <Link
            key={proj.repo_name}
            to={`/timeline?repo=${encodeURIComponent(proj.repo_name)}`}
            className="group block bg-white border border-zinc-200 rounded-lg p-6 hover:border-zinc-400 hover:shadow-sm transition-all"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-2 text-zinc-700">
                <GitBranch size={15} className="text-zinc-400 flex-shrink-0" />
                <span className="font-medium text-zinc-900 truncate">{proj.repo_name}</span>
              </div>
              {proj.latestScore !== null && <ScorePill score={proj.latestScore} />}
            </div>

            <div className="flex items-center gap-4 text-xs text-zinc-500 mt-4">
              <span>{proj.runCount} {proj.runCount === 1 ? 'run' : 'runs'}</span>
              {proj.latestTimestamp && (
                <span className="flex items-center gap-1">
                  <Clock size={11} />
                  {proj.latestTimestamp.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                </span>
              )}
            </div>

            <div className="mt-4 flex items-center gap-1 text-xs font-medium text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
              View Audit Timeline <ArrowRight size={12} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
