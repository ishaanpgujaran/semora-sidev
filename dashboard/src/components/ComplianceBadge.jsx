/**
 * @file ComplianceBadge.jsx
 * @description Dynamic status badge indicating quality-gate safety percentage.
 */

import React from 'react';

export default function ComplianceBadge({ score }) {
  // TODO(frontend-agent): Implement color coding and animations depending on score boundaries.
  return (
    <span className="badge">
      Compliance Score: {score}%
    </span>
  );
}
