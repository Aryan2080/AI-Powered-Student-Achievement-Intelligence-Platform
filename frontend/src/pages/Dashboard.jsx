import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Award, 
  Calendar, 
  ArrowRight, 
  CheckCircle2, 
  Clock, 
  Download, 
  TrendingUp, 
  Bookmark,
  ExternalLink
} from 'lucide-react';
import MatchBadge from '../components/MatchBadge';
import ExplanationModal from '../components/ExplanationModal';
import { api } from '../api/client';

export default function Dashboard({ studentId = "STU-2026-0001", setActiveTab }) {
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [savedOpps, setSavedOpps] = useState({});

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        // Load recommendations
        const recRes = await api.getRecommendations(studentId, 4);
        setRecommendations(recRes.data?.recommendations || []);

        // Load profile
        const profRes = await api.getStudentProfile(studentId);
        setProfile(profRes.data);
      } catch (err) {
        console.warn('Using local fallback preview data:', err);
        // Resilient fallback preview
        setProfile({
          student_id: studentId,
          full_name: 'Aarav Sharma',
          department: 'Computer Science',
          year_of_study: 3,
          gpa: 8.85,
          achievement_count: 3,
          verified_achievement_count: 2,
          declared_skills: ['Python', 'PyTorch', 'OpenCV', 'Git', 'Docker'],
          verified_skills: ['Python', 'OpenCV', 'FastAPI', 'PyTorch'],
        });
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [studentId]);

  const handleSave = async (oppId) => {
    try {
      await api.saveOpportunity(oppId);
      setSavedOpps(prev => ({ ...prev, [oppId]: true }));
    } catch (e) {
      setSavedOpps(prev => ({ ...prev, [oppId]: !prev[oppId] }));
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      
      {/* Top Banner: Academic Identity & Official Transcript Action */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-white to-transparent pointer-events-none"></div>
        
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-xs font-semibold text-blue-200 mb-3 border border-white/10">
              <Sparkles className="w-3.5 h-3.5 text-blue-300" />
              <span>AI Semantic Profile Intelligence</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Welcome back, {profile?.full_name || 'Aarav'}
            </h1>
            <p className="text-sm text-blue-200 mt-1 max-w-xl">
              Your profile is verified with {profile?.verified_achievement_count || 2} authenticated credentials. 
              Our multi-criteria hybrid ranker discovered personalized opportunities matching your skills.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <a
              href={`http://localhost:8000/api/v1/reports/transcript/${studentId}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center px-4 py-2.5 bg-white text-blue-950 hover:bg-blue-50 text-xs font-bold rounded-xl shadow-md transition"
            >
              <Download className="w-4 h-4 mr-2" />
              Export Verified Transcript (PDF)
            </a>
          </div>
        </div>

        {/* Quick KPI Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-6 border-t border-white/10">
          <div>
            <span className="text-xs text-blue-300 font-medium">Cumulative GPA</span>
            <p className="text-2xl font-black text-white">{profile?.gpa || '8.85'}</p>
          </div>
          <div>
            <span className="text-xs text-blue-300 font-medium">Verified Credentials</span>
            <p className="text-2xl font-black text-white">{profile?.verified_achievement_count || '2'}</p>
          </div>
          <div>
            <span className="text-xs text-blue-300 font-medium">Verified Skills</span>
            <p className="text-2xl font-black text-white">{profile?.verified_skills?.length || '4'}</p>
          </div>
          <div>
            <span className="text-xs text-blue-300 font-medium">Profile Completion</span>
            <p className="text-2xl font-black text-emerald-400">92%</p>
          </div>
        </div>
      </div>

      {/* Main Grid: Matched Highlights & Upcoming Deadlines */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Top Matched Opportunities (2 Columns) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Award className="w-5 h-5 text-blue-600" />
              <h2 className="text-lg font-bold text-slate-900">Top Recommended Matches</h2>
            </div>
            <button
              onClick={() => setActiveTab('recommendations')}
              className="text-xs font-bold text-blue-600 hover:text-blue-800 inline-flex items-center"
            >
              Explore All 500+ <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </button>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-400">Loading personalized recommendations...</div>
          ) : (
            <div className="space-y-4">
              {recommendations.slice(0, 3).map((item, idx) => {
                const opp = item.opportunity;
                const isSaved = savedOpps[opp.opportunity_id];

                return (
                  <div
                    key={idx}
                    className="bg-white border border-slate-200 hover:border-blue-300 rounded-2xl p-5 shadow-sm hover:shadow-md transition group"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <MatchBadge score={item.match_score} />
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700">
                            {opp.opportunity_type}
                          </span>
                        </div>
                        <h3 className="text-base font-bold text-slate-900 mt-2 group-hover:text-blue-600 transition">
                          {opp.title}
                        </h3>
                        <p className="text-xs text-slate-500 font-medium mt-0.5">
                          {opp.organization} • {opp.location_type}
                        </p>
                      </div>

                      <button
                        onClick={() => handleSave(opp.opportunity_id)}
                        className={`p-2 rounded-lg border transition ${
                          isSaved ? 'bg-blue-50 border-blue-200 text-blue-600' : 'text-slate-400 hover:text-slate-600 bg-slate-50 border-slate-200'
                        }`}
                      >
                        <Bookmark className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Grounded Explanation Preview */}
                    <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl my-3 text-xs text-slate-700">
                      <span className="font-semibold text-slate-900">Why recommended: </span>
                      {item.explanation}
                    </div>

                    {/* Skill Overlap Preview */}
                    <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-100">
                      <div className="flex items-center space-x-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-slate-600">
                          {item.matched_skills?.length || 0} skills matched ({item.matched_skills?.slice(0, 3).join(', ')})
                        </span>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => setSelectedItem(item)}
                          className="px-3 py-1.5 text-xs font-semibold text-blue-600 hover:bg-blue-50 rounded-lg transition"
                        >
                          View XAI Breakdown
                        </button>
                        <a
                          href={opp.external_url}
                          target="_blank"
                          rel="noreferrer"
                          className="px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
                        >
                          Apply
                        </a>
                      </div>
                    </div>

                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Sidebar: Upcoming Critical Deadlines & Skill Growth */}
        <div className="space-y-6">
          
          {/* Urgent Deadlines Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center space-x-2 mb-4">
              <Calendar className="w-5 h-5 text-rose-600" />
              <h3 className="font-bold text-slate-900 text-base">Approaching Deadlines</h3>
            </div>

            <div className="space-y-3">
              <div className="p-3 bg-rose-50/60 border border-rose-100 rounded-xl">
                <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider block">7 Days Remaining</span>
                <h4 className="text-xs font-bold text-slate-900 mt-0.5">National AI & Robotics Hackathon 2026</h4>
                <p className="text-[11px] text-slate-600 mt-0.5">Major League Hacking • Deadline: 2026-12-15</p>
              </div>

              <div className="p-3 bg-amber-50/60 border border-amber-100 rounded-xl">
                <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider block">14 Days Remaining</span>
                <h4 className="text-xs font-bold text-slate-900 mt-0.5">Undergraduate Research Grant in Vision Transformers</h4>
                <p className="text-[11px] text-slate-600 mt-0.5">NSF Foundation • Deadline: 2026-12-22</p>
              </div>
            </div>
          </div>

          {/* Endorsed Skills Radar / Summary */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center space-x-2 mb-3">
              <TrendingUp className="w-5 h-5 text-indigo-600" />
              <h3 className="font-bold text-slate-900 text-base">Verified Skill Portfolio</h3>
            </div>
            <p className="text-xs text-slate-500 mb-3">
              Grounded across {profile?.verified_achievement_count || 2} faculty-authenticated achievements.
            </p>

            <div className="flex flex-wrap gap-1.5">
              {(profile?.verified_skills || ['Python', 'OpenCV', 'FastAPI', 'PyTorch', 'Docker']).map((sk, idx) => (
                <span key={idx} className="px-2.5 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-semibold">
                  {sk}
                </span>
              ))}
            </div>

            <button
              onClick={() => setActiveTab('achievements')}
              className="w-full mt-4 py-2 border border-slate-200 hover:border-slate-300 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50 transition"
            >
              + Submit New Achievement
            </button>
          </div>

        </div>

      </div>

      {/* XAI Explanation Modal */}
      {selectedItem && (
        <ExplanationModal item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}

    </div>
  );
}
