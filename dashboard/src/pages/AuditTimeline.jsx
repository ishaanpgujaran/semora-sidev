/**
 * @file AuditTimeline.jsx
 * @description Renders chronological quality-gate executions for a selected repository,
 * with compliance score badges and expandable STRIDE findings tables.
 */

import React, { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useFirestoreLive } from '../hooks/useFirestoreLive';
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';

/**
 * Derives Tailwind color classes from a numeric compliance score.
 * Green ≥85 | Amber 60-84 | Red <60
 */
function scoreBadgeClass(score) {
  if (score >= 85) return 'bg-green-100 text-green-700 border-green-200';
  if (score >= 60) return 'bg-amber-100 text-amber-700 border-amber-200';
  return 'bg-red-100 text-red-700 border-red-200';
}

function ScoreBadge({ score }) {
  const cls = scoreBadgeClass(score);
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full border ${cls}`}>
      {score >= 85 ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
      Score: {score}
    </span>
  );
}

const STRIDE_SEVERITY_COLORS = {
  Critical: 'text-red-700 bg-red-50',
  High: 'text-orange-700 bg-orange-50',
  Medium: 'text-amber-700 bg-amber-50',
  Low: 'text-zinc-600 bg-zinc-100',
};

function StrideTable({ findings }) {
  if (!findings || findings.length === 0) {
    return <p className="text-sm text-zinc-500 py-3">No STRIDE findings recorded for this run.</p>;
  }
  return (
    <div className="overflow-x-auto mt-2">
      <table className="w-full text-sm text-left border-collapse">
        <thead>
          <tr className="border-b border-zinc-200">
            <th className="py-2 pr-4 font-medium text-zinc-500 w-32">Category</th>
            <th className="py-2 pr-4 font-medium text-zinc-500">Description</th>
            <th className="py-2 font-medium text-zinc-500 w-24 text-right">Severity</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((f, i) => {
            const sevCls = STRIDE_SEVERITY_COLORS[f.severity] ?? 'text-zinc-600 bg-zinc-100';
            return (
              <tr key={f.id ?? i} className="border-b border-zinc-100 last:border-0">
                <td className="py-2.5 pr-4 font-mono text-xs text-zinc-700">{f.category}</td>
                <td className="py-2.5 pr-4 text-zinc-700">{f.description}</td>
                <td className="py-2.5 text-right">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${sevCls}`}>
                    {f.severity}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RunRow({ run }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-zinc-50 transition-colors"
        aria-expanded={expanded}
      >
        <span className="flex-shrink-0 text-zinc-400">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            {run.compliance_score !== undefined && (
              <ScoreBadge score={run.compliance_score} />
            )}
            {run.commit_sha && (
              <code className="text-xs text-zinc-500 font-mono bg-zinc-100 px-2 py-0.5 rounded">
                {run.commit_sha.slice(0, 8)}
              </code>
            )}
          </div>
          {run.timestamp && (
            <p className="text-xs text-zinc-500 mt-1 flex items-center gap-1">
              <Clock size={11} />
              {run.timestamp.toLocaleString(undefined, {
                month: 'short', day: 'numeric', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </p>
          )}
        </div>

        <span className="text-xs text-zinc-400 flex-shrink-0">
          {run.stride_findings?.length ?? 0} finding{run.stride_findings?.length !== 1 ? 's' : ''}
        </span>
      </button>

      {expanded && (
        <div className="px-5 pb-5 pt-2 border-t border-zinc-100">
          <h4 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-2">
            STRIDE Findings
          </h4>
          <StrideTable findings={run.stride_findings} />
        </div>
      )}
    </div>
  );
}

function EmptyState({ repo }) {
  return (
    <div className="text-center py-24 text-zinc-500">
      <AlertTriangle size={36} className="mx-auto mb-4 text-zinc-300" />
      <p className="font-medium text-zinc-700 mb-1">No runs found</p>
      <p className="text-sm">No audit runs recorded for <strong>{repo || 'this repository'}</strong>.</p>
    </div>
  );
}

export default function AuditTimeline() {
  const [searchParams] = useSearchParams();
  const selectedRepo = searchParams.get('repo') ?? '';
  const { user } = useAuth();
  const { runs, loading, error } = useFirestoreLive(user?.uid);

  const filteredRuns = useMemo(() => {
    if (!selectedRepo) return runs;
    return runs.filter((r) => r.repo_name === selectedRepo);
  }, [runs, selectedRepo]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-400">
        Loading timeline…
      </div>
    );
  }

  return (
    <div>
      <header className="mb-10">
        <h1 className="font-serif text-3xl text-zinc-900 mb-1">Audit Timeline</h1>
        {selectedRepo ? (
          <p className="text-zinc-600">
            Showing all runs for <strong className="text-zinc-800">{selectedRepo}</strong>
          </p>
        ) : (
          <p className="text-zinc-600">Showing all runs across all repositories.</p>
        )}
      </header>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
          {error}
        </div>
      )}

      {filteredRuns.length === 0 && !error ? (
        <EmptyState repo={selectedRepo} />
      ) : (
        <div className="space-y-3">
          {filteredRuns.map((run) => (
            <RunRow key={run.id} run={run} />
          ))}
        </div>
      )}
    </div>
  );
}
