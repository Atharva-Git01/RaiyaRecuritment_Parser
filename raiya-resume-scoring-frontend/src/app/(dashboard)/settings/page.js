'use client'
import { useState, useEffect } from 'react'
import { User, Palette, Bell, SlidersHorizontal, Save, Briefcase, X, Plus, Building2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { DEMO_RECRUITER_PROFILE } from '@/data/static-data'

const WORK_MODES = ['On-site', 'Remote', 'Hybrid']
const JOB_ROLES = ['Python Backend Developer', 'AI Engineer', 'Frontend Developer', 'Full-Stack Developer', 'DevOps Engineer', 'Data Scientist', 'ML Engineer', 'QA Engineer']

export default function SettingsPage() {
  const [darkMode, setDarkMode] = useState(true)
  const [emailNotif, setEmailNotif] = useState(true)
  const [threshold, setThreshold] = useState(70)

  // Recruiter profile state
  const [profile, setProfile] = useState(DEMO_RECRUITER_PROFILE)
  const [roleInput, setRoleInput] = useState('')

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('raiya_recruiter_profile')
      if (saved) setProfile(JSON.parse(saved))
    } catch {}
  }, [])

  const updateProfile = (field, value) => {
    setProfile(prev => ({ ...prev, [field]: value }))
  }

  const addHiringRole = () => {
    const val = roleInput.trim()
    if (val && !profile.hiringRoles.includes(val)) {
      updateProfile('hiringRoles', [...profile.hiringRoles, val])
      setRoleInput('')
    }
  }

  const removeHiringRole = (role) => {
    updateProfile('hiringRoles', profile.hiringRoles.filter(r => r !== role))
  }

  const handleSave = () => {
    try {
      localStorage.setItem('raiya_recruiter_profile', JSON.stringify(profile))
    } catch {}
    toast.success('All settings saved!')
  }

  const Toggle = ({ checked, onChange }) => (
    <button onClick={() => onChange(!checked)} className={`relative w-11 h-6 rounded-full transition-colors ${checked ? 'bg-raiya-500' : 'bg-white/10'}`}>
      <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${checked ? 'translate-x-5.5' : 'translate-x-0.5'}`} />
    </button>
  )

  const InputField = ({ label, value, onChange, readOnly, placeholder }) => (
    <div>
      <label className="text-xs text-slate-500 mb-1 block">{label}</label>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        readOnly={readOnly}
        placeholder={placeholder}
        className={`w-full px-3 py-2.5 rounded-xl text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none t-input ${readOnly ? 'cursor-not-allowed opacity-60' : ''}`}
      />
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold t-heading flex items-center gap-3"><span className="text-3xl">⚙️</span> Settings</h1>
        <p className="text-sm t-faint mt-1">Manage your preferences and recruiter profile</p>
      </div>

      {/* Profile */}
      <div className="glass-card p-6">
        <h2 className="text-base font-semibold t-heading mb-4 flex items-center gap-2"><User className="w-4 h-4 text-raiya-400" /> Profile</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Full Name</label>
            <input defaultValue="Demo Recruiter" className="w-full px-3 py-2.5 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Email</label>
            <input defaultValue="recruiter@speedtech.ai" className="w-full px-3 py-2.5 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Recruiter ID</label>
            <input defaultValue="RAIYA:001" readOnly className="w-full px-3 py-2.5 rounded-xl t-input text-sm cursor-not-allowed opacity-60" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Company</label>
            <input defaultValue="SpeedTech.ai" className="w-full px-3 py-2.5 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none" />
          </div>
        </div>
      </div>

      {/* Recruiter Profile Settings */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card p-6">
        <h2 className="text-base font-semibold t-heading mb-1 flex items-center gap-2">
          <Building2 className="w-4 h-4 text-raiya-400" /> Recruiter Profile Settings
        </h2>
        <p className="text-xs t-faintest mb-5">These settings auto-fill when creating new Job Descriptions</p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <InputField label="Recruiter Name" value={profile.recruiterName} onChange={v => updateProfile('recruiterName', v)} placeholder="Your name" />
          <InputField label="Company Name" value={profile.companyName} onChange={v => updateProfile('companyName', v)} placeholder="Company" />
          <InputField label="Recruiter ID" value={profile.recruiterId} readOnly onChange={() => {}} />
          <InputField label="Designation" value={profile.designation} onChange={v => updateProfile('designation', v)} placeholder="e.g. Senior Recruiter" />
          <InputField label="Department" value={profile.department} onChange={v => updateProfile('department', v)} placeholder="e.g. Engineering" />

          {/* Preferred Job Role dropdown */}
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Preferred Job Role</label>
            <select
              value={profile.preferredJobRole}
              onChange={e => updateProfile('preferredJobRole', e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none appearance-none cursor-pointer"
            >
              {JOB_ROLES.map(r => <option key={r} value={r} className="t-option">{r}</option>)}
            </select>
          </div>

          {/* Default Work Mode */}
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Default Work Mode</label>
            <select
              value={profile.defaultWorkMode}
              onChange={e => updateProfile('defaultWorkMode', e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none appearance-none cursor-pointer"
            >
              {WORK_MODES.map(m => <option key={m} value={m} className="t-option">{m}</option>)}
            </select>
          </div>

          <InputField label="Default Location" value={profile.defaultLocation} onChange={v => updateProfile('defaultLocation', v)} placeholder="e.g. Pune" />
        </div>

        {/* Hiring Roles Tag Input */}
        <div className="mt-5">
          <label className="text-xs text-slate-500 mb-1.5 block">Hiring Roles</label>
          <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl t-input min-h-[48px]">
            <AnimatePresence mode="popLayout">
              {profile.hiringRoles.map(role => (
                <motion.span
                  key={role}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-raiya-500/20 text-raiya-300 border border-raiya-500/20"
                >
                  <Briefcase className="w-3 h-3" />
                  {role}
                  <button onClick={() => removeHiringRole(role)} className="hover:text-red-400 transition-colors ml-0.5">
                    <X className="w-3 h-3" />
                  </button>
                </motion.span>
              ))}
            </AnimatePresence>
            <div className="flex items-center gap-1 flex-1 min-w-[140px]">
              <input
                value={roleInput}
                onChange={e => setRoleInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addHiringRole() } }}
                placeholder="Add hiring role..."
                className="flex-1 bg-transparent text-sm t-heading outline-none placeholder:t-faintest min-w-[100px]"
              />
              {roleInput.trim() && (
                <button onClick={addHiringRole} className="p-1 rounded-lg hover:bg-raiya-500/20 text-raiya-400 transition-colors">
                  <Plus className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Appearance */}
      <div className="glass-card p-6">
        <h2 className="text-base font-semibold t-heading mb-4 flex items-center gap-2"><Palette className="w-4 h-4 text-raiya-400" /> Appearance</h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm t-heading">Dark Mode</p>
            <p className="text-xs t-faintest">Use dark theme across the application</p>
          </div>
          <Toggle checked={darkMode} onChange={setDarkMode} />
        </div>
      </div>

      {/* Notifications */}
      <div className="glass-card p-6">
        <h2 className="text-base font-semibold t-heading mb-4 flex items-center gap-2"><Bell className="w-4 h-4 text-raiya-400" /> Notifications</h2>
        <div className="space-y-4">
          {[
            { label: 'Email Notifications', desc: 'Get notified when batch scoring completes', checked: emailNotif, onChange: setEmailNotif },
            { label: 'In-App Alerts', desc: 'Show toast notifications for events', checked: true, onChange: () => {} },
          ].map(n => (
            <div key={n.label} className="flex items-center justify-between">
              <div>
                <p className="text-sm t-heading">{n.label}</p>
                <p className="text-xs t-faintest">{n.desc}</p>
              </div>
              <Toggle checked={n.checked} onChange={n.onChange} />
            </div>
          ))}
        </div>
      </div>

      {/* Scoring Config */}
      <div className="glass-card p-6">
        <h2 className="text-base font-semibold t-heading mb-4 flex items-center gap-2"><SlidersHorizontal className="w-4 h-4 text-raiya-400" /> Scoring Configuration</h2>
        <div>
          <label className="text-xs text-slate-500 mb-2 block">Auto-reject threshold: candidates below <span className="t-heading font-bold">{threshold}%</span></label>
          <input type="range" min="0" max="100" value={threshold} onChange={e => setThreshold(Number(e.target.value))}
            className="w-full h-2 rounded-full appearance-none bg-white/10 accent-raiya-500 cursor-pointer" />
          <div className="flex justify-between text-xs text-slate-600 mt-1"><span>0%</span><span>50%</span><span>100%</span></div>
        </div>
      </div>

      {/* Save */}
      <button onClick={handleSave} className="w-full py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 hover:from-raiya-500 hover:to-raiya-400 text-white font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-raiya-500/20">
        <Save className="w-5 h-5" /> Save Settings
      </button>
    </div>
  )
}
