/**
 * @file SpecMatrix.jsx
 * @description Renders a grid mapping code areas to their generated BDD spec status and unit coverage.
 * Aggregates spec coverage data across all runs in users/{uid}/runs.
 */

import React, { useMemo } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useFirestoreLive } from '../hooks/useFirestoreLive';
import { CheckCircle2, XCircle, FileCode, ChevronRight } from 'lucide-react';

function CoverageCell({ covered }) {
  return covered ? (
    <div className="flex items-center justify-center h-full" title="Covered">
      <CheckCircle2 size={16} className="text-green-600" />
    </div>
  ) : (
    <div className="flex items-center justify-center h-full" title="Not covered">
      <XCircle size={16} className="text-red-400" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-24 text-zinc-500">
      <FileCode size={36} className="mx-auto mb-4 text-zinc-300" />
      <p className="font-medium text-zinc-700 mb-1">No spec data yet</p>
      <p className="text-sm">Run <code className="bg-zinc-100 px-1 rounded">semora run</code> to generate BDD specs and see coverage here.</p>
    </div>
  );
}

export default function SpecMatrix() {
  const { user } = useAuth();
  const { runs, loading, error } = useFirestoreLive(user?.uid);

  /**
   * Builds a map of { feature/file → { covered: bool, lastSeen: Date, repo: string } }
   * by taking the most recent coverage status for each unique (feature, file) pair.
   */
  const matrix = useMemo(() => {
    const map = {};
    // runs are ordered desc; we want the latest status per (feature+file)
    for (const run of [...runs].reverse()) {
      if (!Array.isArray(run.specs)) continue;
      for (const spec of run.specs) {
        const key = `${spec.feature ?? ''}|||${spec.file ?? ''}`;
        map[key] = {
          feature: spec.feature ?? '—',
          file: spec.file ?? '—',
          covered: !!spec.covered,
          lastSeen: run.timestamp,
          repo: run.repo_name ?? '—',
        };
      }
    }
    // Return sorted: uncovered first (call to action), then covered
    return Object.values(map).sort((a, b) => {
      if (a.covered !== b.covered) return a.covered ? 1 : -1;
      return a.feature.localeCompare(b.feature);
    });
  }, [runs]);

  const coveredCount = matrix.filter((r) => r.covered).length;
  const totalCount = matrix.length;
  const pct = totalCount > 0 ? Math.round((coveredCount / totalCount) * 100) : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-400">
        Loading spec matrix…
      </div>
    );
  }

  return (
    <div>
      <header className="mb-10">
        <h1 className="font-serif text-3xl text-zinc-900 mb-2">Spec Matrix</h1>
        <p className="text-zinc-600">Gherkin BDD spec coverage across all features and files.</p>
        {pct !== null && (
          <div className="mt-4 flex items-center gap-3">
            <div className="flex-1 max-w-xs bg-zinc-200 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full bg-blue-600 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-sm font-medium text-zinc-700">
              {coveredCount} / {totalCount} covered ({pct}%)
            </span>
          </div>
        )}
      </header>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
          {error}
        </div>
      )}

      {matrix.length === 0 && !error ? (
        <EmptyState />
      ) : (
        <div className="border border-zinc-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-zinc-50 border-b border-zinc-200">
              <tr>
                <th className="px-5 py-3 font-medium text-zinc-500">Feature</th>
                <th className="px-5 py-3 font-medium text-zinc-500">File</th>
                <th className="px-5 py-3 font-medium text-zinc-500">Repository</th>
                <th className="px-5 py-3 font-medium text-zinc-500 text-center w-24">Covered</th>
                <th className="px-5 py-3 font-medium text-zinc-500 text-right w-32">Last Run</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {matrix.map((row, i) => (
                <tr
                  key={i}
                  className={`${!row.covered ? 'bg-red-50/40' : 'bg-white'} hover:bg-zinc-50 transition-colors`}
                >
                  <td className="px-5 py-3 text-zinc-800 font-medium">
                    <div className="flex items-center gap-1.5">
                      <ChevronRight size={12} className="text-zinc-400" />
                      {row.feature}
                    </div>
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-zinc-600">{row.file}</td>
                  <td className="px-5 py-3 text-zinc-600">{row.repo}</td>
                  <td className="px-5 py-3 text-center">
                    <CoverageCell covered={row.covered} />
                  </td>
                  <td className="px-5 py-3 text-right text-xs text-zinc-500">
                    {row.lastSeen
                      ? row.lastSeen.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
