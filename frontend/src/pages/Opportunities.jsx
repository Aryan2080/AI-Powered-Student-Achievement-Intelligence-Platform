import React, { useState, useEffect } from 'react';
import { Search, Filter, Bookmark, ExternalLink, Sparkles, CheckCircle2 } from 'lucide-react';
import MatchBadge from '../components/MatchBadge';
import ExplanationModal from '../components/ExplanationModal';
import { api } from '../api/client';

const TYPES = ['ALL', 'HACKATHON', 'INTERNSHIP', 'RESEARCH_GRANT', 'COMPETITION', 'SCHOLARSHIP', 'CONFERENCE'];

export default function Opportunities({ studentId = "STU-2026-0001" }) {
  const [loading, setLoading] = useState(true);
  const [recommendations, setRecommendations] = useState([]);
  const [selectedType, setSelectedType] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [savedMap, setSavedMap] = useState({});

  useEffect(() => {
    async function fetchRecs() {
      try {
        setLoading(true);
        const typeParam = selectedType === 'ALL' ? null : selectedType;
        const res = await api.getRecommendations(studentId, 40, typeParam);
        setRecommendations(res.data?.recommendations || []);
      } catch (err) {
        console.error('Error fetching recommendations:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchRecs();
  }, [studentId, selectedType]);

  const handleSave = async (oppId) => {
    try {
      await api.saveOpportunity(oppId);
      setSavedMap(prev => ({ ...prev, [oppId]: true }));
    } catch (e) {
      setSavedMap(prev => ({ ...prev, [oppId]: !prev[oppId] }));
    }
  };

  const filteredItems = recommendations.filter(item => {
    const opp = item.opportunity;
    const q = searchQuery.toLowerCase();
    return (
      opp.title.toLowerCase().includes(q) ||
      opp.organization.toLowerCase().includes(q) ||
      (opp.required_skills && opp.required_skills.some(s => s.toLowerCase().includes(q)))
    );
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* Title & Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Personalized Opportunity Catalog
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Over 500+ curated opportunities ranked in real-time by semantic vector alignment, skill Jaccard overlap, and deadline urgency.
          </p>
        </div>

        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search title, organization, or skill..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          />
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2 scrollbar-none">
        {TYPES.map(type => (
          <button
            key={type}
            onClick={() => setSelectedType(type)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
              selectedType === type
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {type.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Opportunities List */}
      {loading ? (
        <div className="p-16 text-center text-slate-400">Computing hybrid rankings & explanations...</div>
      ) : filteredItems.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 text-slate-500 text-sm">
          No opportunities found matching your search criteria.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredItems.map((item, idx) => {
            const opp = item.opportunity;
            const isSaved = savedMap[opp.opportunity_id];

            return (
              <div
                key={idx}
                className="bg-white border border-slate-200 hover:border-blue-300 rounded-2xl p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-2">
                      <MatchBadge score={item.match_score} />
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700">
                        {opp.opportunity_type}
                      </span>
                    </div>

                    <button
                      onClick={() => handleSave(opp.opportunity_id)}
                      className={`p-1.5 rounded-lg border transition ${
                        isSaved ? 'bg-blue-50 border-blue-200 text-blue-600' : 'text-slate-400 hover:text-slate-600 bg-slate-50 border-slate-200'
                      }`}
                    >
                      <Bookmark className="w-4 h-4" />
                    </button>
                  </div>

                  <h3 className="font-bold text-slate-900 text-base mt-2.5 line-clamp-1">{opp.title}</h3>
                  <p className="text-xs text-slate-500 font-medium">{opp.organization} • {opp.location}</p>

                  <p className="text-xs text-slate-600 mt-2 line-clamp-2 leading-relaxed">
                    {opp.description}
                  </p>

                  {/* Required Skills Tags */}
                  {opp.required_skills && opp.required_skills.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {opp.required_skills.map((s, sIdx) => {
                        const isMatched = item.matched_skills?.includes(s);
                        return (
                          <span
                            key={sIdx}
                            className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                              isMatched
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : 'bg-slate-50 text-slate-600 border-slate-200'
                            }`}
                          >
                            {s}
                          </span>
                        );
                      })}
                    </div>
                  )}

                  {/* Grounded snippet */}
                  <p className="text-[11px] text-blue-900 bg-blue-50/70 p-2 rounded-lg mt-3 border border-blue-100 italic">
                    "{item.explanation}"
                  </p>
                </div>

                <div className="border-t border-slate-100 pt-3 mt-4 flex items-center justify-between text-xs text-slate-500">
                  <span>Deadline: <strong>{opp.deadline || 'Ongoing'}</strong></span>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setSelectedItem(item)}
                      className="text-xs font-semibold text-blue-600 hover:text-blue-800"
                    >
                      Why Recommended?
                    </button>
                    <a
                      href={opp.external_url}
                      target="_blank"
                      rel="noreferrer"
                      className="px-3 py-1 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
                    >
                      Apply Now
                    </a>
                  </div>
                </div>

              </div>
            );
          })}
        </div>
      )}

      {selectedItem && (
        <ExplanationModal item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}

    </div>
  );
}
