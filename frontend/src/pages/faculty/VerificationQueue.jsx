import React, { useState, useEffect } from 'react';
import { ShieldCheck, Check, X, Clock, ExternalLink, AlertCircle } from 'lucide-react';
import { api } from '../../api/client';

export default function VerificationQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionRemarks, setActionRemarks] = useState({});
  const [submittingId, setSubmittingId] = useState(null);

  useEffect(() => {
    loadQueue();
  }, []);

  async function loadQueue() {
    try {
      setLoading(true);
      const res = await api.getVerificationQueue();
      setQueue(res.data || []);
    } catch (err) {
      console.warn('Fallback verification queue:', err);
      setQueue([
        {
          achievement_id: 'ACH-2026-0003',
          student_id: 'STU-2026-0001',
          title: 'Autonomous Drone Obstacle Avoidance Prototype using ROS2 and LiDAR',
          description: 'Designed quadcopter obstacle avoidance system integrating ROS2, SLAM navigation, and depth camera sensor fusion. Evaluated across 20 obstacle trials.',
          category: 'PROJECT',
          level: 'COLLEGE',
          achievement_date: '2025-10-05',
          skills: ['C++', 'Python', 'Linux', 'Git', 'ROS2'],
          evidence_url: 'https://github.com/student/drone-ros2',
          classifier_confidence: 0.91,
          extraction_confidence: 0.94,
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  const handleVerify = async (id, status) => {
    const remarks = actionRemarks[id] || (status === 'VERIFIED' ? 'Approved by Department Faculty' : 'Insufficient evidence');
    try {
      setSubmittingId(id);
      await api.verifyAchievement(id, status, remarks);
      setQueue(prev => prev.filter(item => item.achievement_id !== id));
      alert(`Achievement ${status === 'VERIFIED' ? 'Approved' : 'Rejected'} successfully!`);
    } catch (err) {
      alert('Verification error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Faculty Verification Queue
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Review, authenticate, or reject pending student achievements and certificates before inclusion in official transcripts.
        </p>
      </div>

      {loading ? (
        <div className="p-16 text-center text-slate-400">Loading pending verification queue...</div>
      ) : queue.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 text-slate-500 text-sm">
          <ShieldCheck className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
          <p className="font-bold text-slate-700">Verification Queue is Clear</p>
          <p className="text-xs text-slate-400 mt-1">All student achievement submissions have been reviewed.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {queue.map(item => (
            <div
              key={item.achievement_id}
              className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-start justify-between gap-6"
            >
              <div className="space-y-3 flex-1">
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {item.category}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">
                    {item.level} Level
                  </span>
                  <span className="text-xs text-slate-400">
                    Student ID: {item.student_id}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900">{item.title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>

                {/* NLP Extracted Skills */}
                {item.skills && item.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {item.skills.map((s, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-xs font-medium">
                        {s}
                      </span>
                    ))}
                  </div>
                )}

                {/* Evidence link & Confidence */}
                <div className="flex items-center space-x-4 text-xs text-slate-500 pt-2 border-t border-slate-100">
                  <span>Confidence: <strong>{Math.round((item.classifier_confidence || 0.9) * 100)}%</strong></span>
                  {item.evidence_url && (
                    <a
                      href={item.evidence_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:text-blue-800 font-medium inline-flex items-center"
                    >
                      Inspect Evidence Link <ExternalLink className="w-3 h-3 ml-1" />
                    </a>
                  )}
                </div>
              </div>

              {/* Action Column */}
              <div className="w-full md:w-72 bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
                <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                  Audit Remarks / Feedback
                </label>
                <input
                  type="text"
                  placeholder="e.g. Verified with registrar records"
                  value={actionRemarks[item.achievement_id] || ''}
                  onChange={(e) => setActionRemarks({ ...actionRemarks, [item.achievement_id]: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    disabled={submittingId === item.achievement_id}
                    onClick={() => handleVerify(item.achievement_id, 'REJECTED')}
                    className="flex items-center justify-center px-3 py-2 text-xs font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-lg transition disabled:opacity-50"
                  >
                    <X className="w-3.5 h-3.5 mr-1" />
                    Reject
                  </button>

                  <button
                    disabled={submittingId === item.achievement_id}
                    onClick={() => handleVerify(item.achievement_id, 'VERIFIED')}
                    className="flex items-center justify-center px-3 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm transition disabled:opacity-50"
                  >
                    <Check className="w-3.5 h-3.5 mr-1" />
                    Approve
                  </button>
                </div>
              </div>

            </div>
          ))}
        </div>
      )}

    </div>
  );
}
