import React, { useState } from 'react';
import { 
  Compass, 
  Award, 
  Briefcase, 
  UserCheck, 
  ShieldCheck, 
  Search, 
  BarChart3, 
  Bell, 
  FileText,
  LogOut
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, currentRole, setRole, user, unreadCount = 0 }) {
  const isFaculty = currentRole === 'FACULTY';

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <span className="font-extrabold text-slate-900 tracking-tight text-base sm:text-lg block leading-none">
                Student Intelligence
              </span>
              <span className="text-[10px] text-blue-600 font-bold uppercase tracking-widest block mt-0.5">
                AI Recommendation Platform
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {!isFaculty ? (
              <>
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition ${
                    activeTab === 'dashboard' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setActiveTab('recommendations')}
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition ${
                    activeTab === 'recommendations' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  Matched Opportunities
                </button>
                <button
                  onClick={() => setActiveTab('achievements')}
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition ${
                    activeTab === 'achievements' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  My Achievements
                </button>
                <button
                  onClick={() => setActiveTab('profile')}
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition ${
                    activeTab === 'profile' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  Profile & Skills
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setActiveTab('verificationQueue')}
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition ${
                    activeTab === 'verificationQueue' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  Verification Queue
                </button>
                <button
                  onClick={() => setActiveTab('talentSearch')}
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition ${
                    activeTab === 'talentSearch' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  Talent Search
                </button>
                <button
                  onClick={() => setActiveTab('institutionalAnalytics')}
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition ${
                    activeTab === 'institutionalAnalytics' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  Department Analytics
                </button>
              </>
            )}
          </nav>

          {/* Right Controls: Role Switcher & Profile Badge */}
          <div className="flex items-center space-x-3">
            
            {/* Quick Persona Switcher for Evaluation / Demo */}
            <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-semibold">
              <button
                onClick={() => {
                  setRole('STUDENT');
                  setActiveTab('dashboard');
                }}
                className={`px-2.5 py-1 rounded-md transition ${
                  currentRole === 'STUDENT' ? 'bg-white shadow text-blue-700 font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Student
              </button>
              <button
                onClick={() => {
                  setRole('FACULTY');
                  setActiveTab('verificationQueue');
                }}
                className={`px-2.5 py-1 rounded-md transition ${
                  currentRole === 'FACULTY' ? 'bg-white shadow text-indigo-700 font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Faculty
              </button>
            </div>

            {/* Notification Indicator */}
            <div className="relative cursor-pointer p-1.5 text-slate-500 hover:text-slate-700">
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-0 right-0 w-4 h-4 bg-rose-500 text-white rounded-full text-[10px] font-bold flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </div>

            {/* User Profile Pill */}
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
              <div className="w-8 h-8 rounded-full bg-slate-800 text-white text-xs font-bold flex items-center justify-center">
                {user?.full_name ? user.full_name[0] : (isFaculty ? 'F' : 'S')}
              </div>
              <div className="hidden lg:block text-left">
                <span className="text-xs font-bold text-slate-800 block leading-tight">
                  {user?.full_name || (isFaculty ? 'Dr. Rajesh Raman' : 'Aarav Sharma')}
                </span>
                <span className="text-[10px] text-slate-500 block leading-tight">
                  {isFaculty ? 'Faculty / HOD' : 'B.Tech CS (Year 3)'}
                </span>
              </div>
            </div>

          </div>

        </div>
      </div>
    </header>
  );
}
