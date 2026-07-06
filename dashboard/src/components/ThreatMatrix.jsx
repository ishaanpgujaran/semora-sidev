/**
 * @file ThreatMatrix.jsx
 * @description Threat modeling matrix displaying audit findings mapped against STRIDE classification vectors.
 */

import React from 'react';

export default function ThreatMatrix({ threats = [] }) {
  // TODO(frontend-agent): Draw interactive grid indicating high, medium, and low risk threats across STRIDE classes.
  return (
    <div className="threat-matrix">
      <h3>STRIDE Threat Matrix</h3>
      <p>{threats.length} threats found.</p>
    </div>
  );
}
