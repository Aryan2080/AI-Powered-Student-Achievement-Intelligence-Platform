import React from 'react';

export default function MatchBadge({ score }) {
  const percentage = Math.round(score * 100);

  let colorClasses = "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (percentage < 65) {
    colorClasses = "bg-amber-50 text-amber-700 border-amber-200";
  } else if (percentage < 80) {
    colorClasses = "bg-blue-50 text-blue-700 border-blue-200";
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorClasses}`}>
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current"></span>
      {percentage}% Match
    </span>
  );
}
