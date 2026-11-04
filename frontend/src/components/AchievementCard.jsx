import React from 'react';
import { Award, CheckCircle2, Clock, XCircle, ExternalLink } from 'lucide-react';

export default function AchievementCard({ achievement }) {
  const isVerified = achievement.evidence_status === 'VERIFIED';
  const isPending = achievement.evidence_status === 'PENDING';

  return (
    <div className="bg-white border border-slate-200 hover:border-slate-300 rounded-xl p-5 shadow-sm hover:shadow transition">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-2">
          <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">
            {achievement.category}
          </span>
          <span className="text-xs text-slate-500 font-medium">
            {achievement.level}
          </span>
        </div>

        {isVerified ? (
          <span className="inline-flex items-center text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
            Verified
          </span>
        ) : isPending ? (
          <span className="inline-flex items-center text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
            <Clock className="w-3.5 h-3.5 mr-1 text-amber-600" />
            Pending Review
          </span>
        ) : (
          <span className="inline-flex items-center text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
            <XCircle className="w-3.5 h-3.5 mr-1 text-rose-600" />
            Rejected
          </span>
        )}
      </div>

      <h4 className="font-bold text-slate-900 text-base mt-2.5">{achievement.title}</h4>
      <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed">
        {achievement.description}
      </p>

      {/* Skills */}
      {achievement.skills && achievement.skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {achievement.skills.map((s, idx) => (
            <span key={idx} className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[11px] font-medium">
              {s}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="border-t border-slate-100 pt-3 mt-4 flex items-center justify-between text-xs text-slate-500">
        <span>Date: {achievement.achievement_date || 'N/A'}</span>
        {achievement.evidence_url && (
          <a
            href={achievement.evidence_url}
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 hover:text-blue-800 font-medium inline-flex items-center"
          >
            Evidence Link <ExternalLink className="w-3 h-3 ml-1" />
          </a>
        )}
      </div>
    </div>
  );
}
