import React, { useState, useEffect } from 'react';
import { User, BookOpen, Award, CheckCircle2, Download, Save } from 'lucide-react';
import { api } from '../api/client';

export default function Profile({ studentId = "STU-2026-0001" }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form Fields
  const [gpa, setGpa] = useState(8.85);
  const [declaredSkills, setDeclaredSkills] = useState('');
  const [declaredInterests, setDeclaredInterests] = useState('');
  const [careerGoals, setCareerGoals] = useState('');

  useEffect(() => {
    async function fetchProfile() {
      try {
        setLoading(true);
        const res = await api.getStudentProfile(studentId);
        setProfile(res.data);
        setGpa(res.data.gpa || 8.85);
        setDeclaredSkills((res.data.declared_skills || []).join(', '));
        setDeclaredInterests((res.data.declared_interests || []).join(', '));
        setCareerGoals(res.data.career_goals || '');
      } catch (err) {
        console.warn('Fallback profile:', err);
        setProfile({
          student_id: studentId,
          full_name: 'Aarav Sharma',
          department: 'Computer Science',
          program: 'B.Tech',
          year_of_study: 3,
          gpa: 8.85,
          declared_skills: ['Python', 'PyTorch', 'OpenCV', 'Git', 'Docker'],
          declared_interests: ['Artificial Intelligence', 'Autonomous Robotics'],
          verified_skills: ['Python', 'OpenCV', 'FastAPI', 'PyTorch', 'Docker'],
          career_goals: 'Aspiring AI Research & Robotics Engineer'
        });
      } finally {
        setLoading(false);
      }
    }
    fetchProfile();
  }, [studentId]);

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      await api.updateStudentProfile(studentId, {
        gpa: parseFloat(gpa),
        declared_skills: declaredSkills.split(',').map(s => s.trim()).filter(Boolean),
        declared_interests: declaredInterests.split(',').map(i => i.trim()).filter(Boolean),
        career_goals: careerGoals,
      });
      alert('Profile preferences updated successfully! Recommendations refreshed.');
    } catch (err) {
      alert('Update failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-16 text-center text-slate-400">Loading student profile...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-300">
      
      {/* Profile Header */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-700 to-indigo-600 text-white font-extrabold text-2xl flex items-center justify-center shadow-lg shadow-blue-500/20">
            {profile?.full_name ? profile.full_name[0] : 'S'}
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900">{profile?.full_name}</h1>
            <p className="text-xs text-slate-500 font-medium">
              ID: {profile?.student_id} • {profile?.department} ({profile?.program}, Year {profile?.year_of_study})
            </p>
          </div>
        </div>

        <a
          href={`http://localhost:8000/api/v1/reports/transcript/${studentId}`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl shadow transition"
        >
          <Download className="w-4 h-4 mr-2" />
          Download Transcript (PDF)
        </a>
      </div>

      {/* Verified Competencies vs Declared Skills */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Verified Skills */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center space-x-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <h3 className="font-bold text-slate-900 text-base">Verified Endorsed Skills</h3>
          </div>
          <p className="text-xs text-slate-500 mb-4">
            Extracted via Member 1 NLP entity recognition and authenticated by university faculty.
          </p>

          <div className="flex flex-wrap gap-2">
            {(profile?.verified_skills || []).map((sk, idx) => (
              <span key={idx} className="px-3 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold flex items-center">
                <CheckCircle2 className="w-3 h-3 mr-1.5 text-emerald-600" />
                {sk}
              </span>
            ))}
          </div>
        </div>

        {/* Academic Standing */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center space-x-2 mb-3">
            <BookOpen className="w-5 h-5 text-blue-600" />
            <h3 className="font-bold text-slate-900 text-base">Academic Standing</h3>
          </div>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Department</span>
              <span className="font-bold text-slate-900">{profile?.department}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Program & Year</span>
              <span className="font-bold text-slate-900">{profile?.program} (Year {profile?.year_of_study})</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-500 font-medium">Verified Credentials</span>
              <span className="font-bold text-slate-900">{profile?.verified_achievement_count} Records</span>
            </div>
          </div>
        </div>

      </div>

      {/* Editable Student Preferences Form */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-slate-900 text-base mb-1">Career Preferences & Declared Skills</h3>
        <p className="text-xs text-slate-500 mb-6">
          Updating your preferences will recalculate your dynamic 384-dimensional profile vector and adjust recommendation rankings.
        </p>

        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Cumulative GPA</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="10"
                value={gpa}
                onChange={(e) => setGpa(e.target.value)}
                className="w-full px-3.5 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Career Goal Statement</label>
              <input
                type="text"
                placeholder="e.g. Aspiring Generative AI Researcher"
                value={careerGoals}
                onChange={(e) => setCareerGoals(e.target.value)}
                className="w-full px-3.5 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Declared Skills (Comma-separated)</label>
            <input
              type="text"
              value={declaredSkills}
              onChange={(e) => setDeclaredSkills(e.target.value)}
              className="w-full px-3.5 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Declared Domain Interests (Comma-separated)</label>
            <input
              type="text"
              value={declaredInterests}
              onChange={(e) => setDeclaredInterests(e.target.value)}
              className="w-full px-3.5 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow transition disabled:opacity-50"
            >
              <Save className="w-4 h-4 mr-1.5" />
              {saving ? 'Updating Profile...' : 'Save & Refresh Profile Vector'}
            </button>
          </div>
        </form>
      </div>

    </div>
  );
}
