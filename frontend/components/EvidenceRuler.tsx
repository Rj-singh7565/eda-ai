'use client';

import React from 'react';

interface EvidenceRulerProps {
  activeCoordinate: string;
  onSelectCoordinate: (coord: string) => void;
}

export default function EvidenceRuler({ activeCoordinate, onSelectCoordinate }: EvidenceRulerProps) {
  const coordinates = ['03', '11', '18', '27', '41', '52', '68', '79', '90', '103', '116'];

  return (
    <aside className="evidence-ruler">
      <div className="ruler-title">EVIDENCE</div>
      {coordinates.map((coord) => {
        const isActive = activeCoordinate === coord || (activeCoordinate.includes('18') && coord === '18');
        return (
          <div
            key={coord}
            onClick={() => onSelectCoordinate(coord)}
            className={`ruler-tick ${isActive ? 'active' : ''}`}
            title={`Source coordinate p. ${coord}`}
          >
            {coord}
          </div>
        );
      })}
    </aside>
  );
}
