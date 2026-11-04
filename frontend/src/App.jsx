import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Opportunities from './pages/Opportunities';
import Achievements from './pages/Achievements';
import Profile from './pages/Profile';
import VerificationQueue from './pages/faculty/VerificationQueue';
import TalentSearch from './pages/faculty/TalentSearch';
import InstitutionalAnalytics from './pages/faculty/InstitutionalAnalytics';

export default function App() {
  const [currentRole, setRole] = useState('STUDENT'); // 'STUDENT' or 'FACULTY'
  const [activeTab, setActiveTab] = useState('dashboard');
  const [studentId, setStudentId] = useState('STU-2026-0001');

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentRole={currentRole}
        setRole={setRole}
        unreadCount={2}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentRole === 'STUDENT' ? (
          <>
            {activeTab === 'dashboard' && <Dashboard studentId={studentId} setActiveTab={setActiveTab} />}
            {activeTab === 'recommendations' && <Opportunities studentId={studentId} />}
            {activeTab === 'achievements' && <Achievements studentId={studentId} />}
            {activeTab === 'profile' && <Profile studentId={studentId} />}
          </>
        ) : (
          <>
            {activeTab === 'verificationQueue' && <VerificationQueue />}
            {activeTab === 'talentSearch' && <TalentSearch />}
            {activeTab === 'institutionalAnalytics' && <InstitutionalAnalytics />}
          </>
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-500">
          <p>© 2026 AI-Powered Student Achievement Intelligence Platform • Member 3 Core Deliverable</p>
          <p className="mt-1 text-[11px] text-slate-400">
            Clean Hexagonal Architecture • FastAPI REST Backend • Vector Semantic Similarity • Grounded Explainability
          </p>
        </div>
      </footer>
    </div>
  );
}
