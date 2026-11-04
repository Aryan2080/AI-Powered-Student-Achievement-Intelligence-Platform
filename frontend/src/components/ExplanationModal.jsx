import React from 'react';
import { X, CheckCircle2, AlertCircle, Sparkles, Award } from 'lucide-react';

export default function ExplanationModal({ item, onClose }) {
  if (!item) return null;
  const opp = item.opportunity;
  const scores = item.scores || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden border border-slate-100 animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white p-6 relative">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 text-slate-300 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="flex items-center space-x-2 text-blue-200 text-xs font-semibold uppercase tracking-wider mb-1">
            <Sparkles className="w-4 h-4" />
            <span>AI Explainability (XAI) Attribution</span>
          </div>
          <h3 className="text-xl font-bold pr-8">{opp.title}</h3>
          <p className="text-sm text-blue-200 mt-1">{opp.organization} • {opp.opportunity_type}</p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          
          {/* Grounded Natural Language Justification */}
          <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
            <h4 className="text-xs font-bold text-blue-900 uppercase tracking-wider mb-1">Why Recommended</h4>
            <p className="text-sm text-blue-950 font-medium leading-relaxed">
              "{item.explanation}"
            </p>
          </div>

          {/* Scoring Multi-Criteria Components */}
          <div>
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Multi-Objective Score Components</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
                <span className="text-xs text-slate-500">Semantic Alignment</span>
                <p className="text-lg font-bold text-slate-800">{Math.round((scores.semantic_similarity || 0) * 100)}%</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
                <span className="text-xs text-slate-500">Skill Overlap</span>
                <p className="text-lg font-bold text-slate-800">{Math.round((scores.skill_match_score || 0) * 100)}%</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
                <span className="text-xs text-slate-500">Domain Match</span>
                <p className="text-lg font-bold text-slate-800">{Math.round((scores.domain_match_score || 0) * 100)}%</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
                <span className="text-xs text-slate-500">Urgency Score</span>
                <p className="text-lg font-bold text-slate-800">{Math.round((scores.urgency_score || 0) * 100)}%</p>
              </div>
            </div>
          </div>

          {/* Skill Attribution & Gap Analysis */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="flex items-center space-x-1.5 text-xs font-bold text-emerald-700 uppercase tracking-wider mb-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Matched Skills ({item.matched_skills?.length || 0})</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {item.matched_skills && item.matched_skills.length > 0 ? (
                  item.matched_skills.map((s, idx) => (
                    <span key={idx} className="px-2.5 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-md text-xs font-medium">
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-400 italic">No direct required skills matched</span>
                )}
              </div>
            </div>

            <div>
              <div className="flex items-center space-x-1.5 text-xs font-bold text-amber-700 uppercase tracking-wider mb-2">
                <AlertCircle className="w-4 h-4 text-amber-600" />
                <span>Skill Gaps for Growth ({item.missing_skills?.length || 0})</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {item.missing_skills && item.missing_skills.length > 0 ? (
                  item.missing_skills.map((s, idx) => (
                    <span key={idx} className="px-2.5 py-1 bg-amber-50 text-amber-800 border border-amber-200 rounded-md text-xs font-medium">
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-emerald-600 font-medium">100% prerequisite skill coverage!</span>
                )}
              </div>
            </div>
          </div>

          {/* Closest Verified Achievement */}
          {item.closest_achievement_title && (
            <div className="flex items-start space-x-3 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
              <Award className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-800">Closest Evidenced Achievement:</span>
                <p className="text-slate-600 mt-0.5">{item.closest_achievement_title} ({item.closest_achievement_id})</p>
              </div>
            </div>
          )}

          {/* Details & Action */}
          <div className="border-t border-slate-200 pt-4 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Deadline: <strong className="text-slate-700">{opp.deadline || 'Ongoing'}</strong>
            </span>
            <div className="flex space-x-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
              >
                Close
              </button>
              <a
                href={opp.external_url}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition"
              >
                Visit Official Portal
              </a>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
