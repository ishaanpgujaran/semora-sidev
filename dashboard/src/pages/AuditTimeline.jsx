/**
 * @file AuditTimeline.jsx
 * @description Renders chronological quality-gate executions for a selected repository,
 * with compliance score badges, a slide-in animation for new runs arriving via the
 * live Firestore listener, and a STRIDE findings table sortable by severity.
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useFirestoreLive } from '../hooks/useFirestoreLive';
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, Clock, ChevronsUpDown } from 'lucide-react';

/* --------------------------------------------------------------------------
   Severity ordering used for sorting
   -------------------------------------------------------------------------- */
const SEVERITY_RANK = { Critical: 0, High: 1, Medium: 2, Low: 3 };

/**
 * Derives Tailwind color classes from a numeric compliance score.
 * Green ≥85 | Amber 60–84 | Red <60
 */
function scoreBadgeClass(score) {
  if (score >= 85) return 'bg-green-100 text-green-700 border-green-200';
  if (score >= 60) return 'bg-amber-100 text-amber-700 border-amber-200';
  return 'bg-red-100 text-red-700 border-red-200';
}

function ScoreBadge({ score }) {
  const cls = scoreBadgeClass(score);
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${cls}`}>
      {score >= 85 ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
      Score: {score}
    </span>
  );
}

/* --------------------------------------------------------------------------
   Severity badge inside the STRIDE table
   -------------------------------------------------------------------------- */
const STRIDE_SEVERITY_COLORS = {
  Critical: 'text-red-700 bg-red-50 border-red-200',
  High:     'text-orange-700 bg-orange-50 border-orange-200',
  Medium:   'text-amber-700 bg-amber-50 border-amber-200',
  Low:      'text-zinc-600 bg-zinc-100 border-zinc-200',
};

/* --------------------------------------------------------------------------
   Sortable STRIDE findings table
   -------------------------------------------------------------------------- */
function StrideTable({ findings }) {
  const [sortDir, setSortDir] = useState('asc'); // 'asc' = Critical first

  if (!findings || findings.length === 0) {
    return (
      <p className="text-sm text-zinc-400 py-3">
        No STRIDE findings recorded for this run.
      </p>
    );
  }

  const sorted = [...findings].sort((a, b) => {
    const ra = SEVERITY_RANK[a.severity] ?? 99;
    const rb = SEVERITY_RANK[b.severity] ?? 99;
    return sortDir === 'asc' ? ra - rb : rb - ra;
  });

  return (
    <div className="overflow-x-auto mt-2">
      <table className="w-full text-sm text-left border-collapse">
        <thead>
          <tr className="border-b border-zinc-200">
            <th className="py-2 pr-4 text-xs font-medium text-zinc-400 uppercase tracking-wider w-32">
              Category
            </th>
            <th className="py-2 pr-4 text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Description
            </th>
            {/* Sortable severity column */}
            <th className="py-2 text-xs font-medium text-zinc-400 uppercase tracking-wider w-28 text-right">
              <button
                type="button"
                onClick={() => setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))}
                className="inline-flex items-center gap-1 hover:text-zinc-700 transition-colors duration-100 ml-auto"
                title={`Sort by severity ${sortDir === 'asc' ? '(lowest first)' : '(highest first)'}`}
              >
                Severity <ChevronsUpDown size={11} />
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((f, i) => {
            const sevCls = STRIDE_SEVERITY_COLORS[f.severity] ?? 'text-zinc-600 bg-zinc-100 border-zinc-200';
            return (
              <tr key={f.id ?? i} className="border-b border-zinc-100 last:border-0">
                <td className="py-3 pr-4 font-mono text-xs text-zinc-600">{f.category}</td>
                <td className="py-3 pr-4 text-zinc-700 text-sm leading-snug">{f.description}</td>
                <td className="py-3 text-right">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded border ${sevCls}`}>
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

/* --------------------------------------------------------------------------
   Single run row with slide-in animation on first mount
   -------------------------------------------------------------------------- */
function RunRow({ run, isNew }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`border border-zinc-200 rounded-lg overflow-hidden bg-white ${isNew ? 'animate-slide-in' : ''}`}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-zinc-50 transition-colors duration-100"
        aria-expanded={expanded}
      >
        <span className="flex-shrink-0 text-zinc-400">
          {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            {run.compliance_score !== undefined && (
              <ScoreBadge score={run.compliance_score} />
            )}
            {run.commit_sha && (
              <code className="text-xs text-zinc-400 font-mono bg-zinc-100 px-2 py-0.5 rounded">
                {run.commit_sha.slice(0, 8)}
              </code>
            )}
          </div>
          {run.timestamp && (
            <p className="text-xs text-zinc-400 mt-1.5 flex items-center gap-1">
              <Clock size={10} />
              {run.timestamp.toLocaleString(undefined, {
                month: 'short', day: 'numeric', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </p>
          )}
        </div>

        <span className="text-xs text-zinc-400 flex-shrink-0 tabular-nums">
          {run.stride_findings?.length ?? 0}&nbsp;finding
          {run.stride_findings?.length !== 1 ? 's' : ''}
        </span>
      </button>

      {expanded && (
        <div className="px-5 pb-5 pt-3 border-t border-zinc-100 animate-expand">
          <h4 className="text-xs font-semibold uppercase tracking-widest text-zinc-400 mb-3">
            STRIDE Findings
          </h4>
          <StrideTable findings={run.stride_findings} />
        </div>
      )}
    </div>
  );
}

/* --------------------------------------------------------------------------
   Empty state
   -------------------------------------------------------------------------- */
function EmptyState({ repo }) {
  return (
    <div className="text-center py-24">
      <AlertTriangle size={32} className="mx-auto mb-4 text-zinc-300" />
      <p className="font-medium text-zinc-700 mb-1">No runs found</p>
      <p className="text-sm text-zinc-400">
        No audit runs recorded for <strong className="text-zinc-600">{repo || 'this repository'}</strong>.
      </p>
    </div>
  );
}

/* --------------------------------------------------------------------------
   Page
   -------------------------------------------------------------------------- */
export default function AuditTimeline() {
  const [searchParams] = useSearchParams();
  const selectedRepo = searchParams.get('repo') ?? '';
  const { user } = useAuth();
  const { runs, loading, error } = useFirestoreLive(user?.uid);

  /**
   * Track which run IDs we have already seen so that brand-new arrivals
   * (pushed by the onSnapshot listener) receive the slide-in animation.
   */
  const seenIds = useRef(new Set());
  const [newIds, setNewIds] = useState(new Set());

  const filteredRuns = useMemo(() => {
    if (!selectedRepo) return runs;
    return runs.filter((r) => r.repo_name === selectedRepo);
  }, [runs, selectedRepo]);

  useEffect(() => {
    if (loading) return;
    const fresh = new Set();
    filteredRuns.forEach((run) => {
      if (!seenIds.current.has(run.id)) {
        fresh.add(run.id);
        seenIds.current.add(run.id);
      }
    });
    if (fresh.size > 0) {
      setNewIds(fresh);
      // Remove the animation class after it completes so it doesn't replay on re-render
      const t = setTimeout(() => setNewIds(new Set()), 500);
      return () => clearTimeout(t);
    }
  }, [filteredRuns, loading]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-400 text-sm">
        Loading timeline…
      </div>
    );
  }

  return (
    <div>
      <header className="mb-12">
        <h1 className="font-serif text-3xl font-normal text-zinc-900 mb-1.5">Audit Timeline</h1>
        {selectedRepo ? (
          <p className="text-sm text-zinc-500">
            Showing all runs for{' '}
            <strong className="text-zinc-800 font-medium">{selectedRepo}</strong>
          </p>
        ) : (
          <p className="text-sm text-zinc-500">Showing all runs across all repositories.</p>
        )}
      </header>

      {error && (
        <div className="mb-8 px-4 py-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded">
          {error}
        </div>
      )}

      {filteredRuns.length === 0 && !error ? (
        <EmptyState repo={selectedRepo} />
      ) : (
        <div className="space-y-2.5">
          {filteredRuns.map((run) => (
            <RunRow key={run.id} run={run} isNew={newIds.has(run.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
