'use client'
import { motion } from 'framer-motion'
import { Briefcase, GraduationCap, Code, Cpu, ListChecks, HelpCircle } from 'lucide-react'
import TagInput from './TagInput'
import ResponsibilityBuilder from './ResponsibilityBuilder'
import ScreeningQuestionBuilder from './ScreeningQuestionBuilder'

const EMPLOYMENT_TYPES = ['Full-time', 'Part-time', 'Contract', 'Internship', 'Freelance']
const WORK_MODES = ['On-site', 'Remote', 'Hybrid']
const QUALIFICATIONS = ['High School', 'Diploma', 'Bachelors', 'Masters', 'PhD']

const STEPS = [
  { id: 'basic', label: 'Basic Info', icon: Briefcase },
  { id: 'experience', label: 'Experience', icon: GraduationCap },
  { id: 'skills', label: 'Skills', icon: Code },
  { id: 'tech', label: 'Technologies', icon: Cpu },
  { id: 'responsibilities', label: 'Duties', icon: ListChecks },
  { id: 'screening', label: 'Screening', icon: HelpCircle },
]

function InputField({ label, ...props }) {
  return (
    <div>
      <label className="text-xs t-faint mb-1.5 block font-medium">{label}</label>
      <input
        {...props}
        className="w-full px-3 py-2.5 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none transition-all"
      />
    </div>
  )
}

function SelectField({ label, options, ...props }) {
  return (
    <div>
      <label className="text-xs t-faint mb-1.5 block font-medium">{label}</label>
      <select
        {...props}
        className="w-full px-3 py-2.5 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none transition-all appearance-none cursor-pointer"
      >
        <option value="" className="t-option">Select...</option>
        {options.map(o => (
          <option key={o} value={o} className="t-option">{o}</option>
        ))}
      </select>
    </div>
  )
}

export default function JobForm({ formData, setFormData, currentStep, setCurrentStep }) {
  const update = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const stepIndex = STEPS.findIndex(s => s.id === currentStep)

  const sectionVariant = {
    initial: { opacity: 0, x: 20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
  }

  return (
    <div className="space-y-6">
      {/* Stepper */}
      <div className="glass-card p-4">
        <div className="flex items-center justify-between gap-1 overflow-x-auto">
          {STEPS.map((step, i) => {
            const Icon = step.icon
            const isActive = i === stepIndex
            const isDone = i < stepIndex
            return (
              <button
                key={step.id}
                onClick={() => setCurrentStep(step.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-raiya-600/20 text-raiya-300 border border-raiya-500/20 shadow-lg shadow-raiya-500/5'
                    : isDone
                    ? 'text-green-400 bg-green-500/5 border border-green-500/10'
                    : 't-faintest border border-transparent hover:bg-white/5'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{step.label}</span>
                {isDone && <span className="text-green-400">✓</span>}
              </button>
            )
          })}
        </div>
        {/* Progress line */}
        <div className="mt-3 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-raiya-600 to-raiya-400"
            initial={false}
            animate={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
      </div>

      {/* Form Sections */}
      <motion.div
        key={currentStep}
        variants={sectionVariant}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={{ duration: 0.3 }}
        className="glass-card p-6"
      >
        {currentStep === 'basic' && (
          <div className="space-y-5">
            <h3 className="text-base font-semibold t-heading flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-raiya-400" /> Basic Information
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <InputField label="Job Role *" value={formData.jobRole || ''} onChange={e => update('jobRole', e.target.value)} placeholder="e.g. Python Backend Developer" />
              <InputField label="Department" value={formData.department || ''} onChange={e => update('department', e.target.value)} placeholder="e.g. Engineering" />
              <SelectField label="Employment Type" options={EMPLOYMENT_TYPES} value={formData.employmentType || ''} onChange={e => update('employmentType', e.target.value)} />
              <SelectField label="Work Mode" options={WORK_MODES} value={formData.workMode || ''} onChange={e => update('workMode', e.target.value)} />
              <InputField label="Location" value={formData.location || ''} onChange={e => update('location', e.target.value)} placeholder="e.g. Pune, India" />
              <InputField label="Salary Range" value={formData.salaryRange || ''} onChange={e => update('salaryRange', e.target.value)} placeholder="e.g. 15-25 LPA" />
              <InputField label="Open Positions" type="number" min={1} value={formData.openPositions || ''} onChange={e => update('openPositions', e.target.value)} placeholder="e.g. 3" />
              <InputField label="Application Deadline" type="date" value={formData.deadline || ''} onChange={e => update('deadline', e.target.value)} />
            </div>
          </div>
        )}

        {currentStep === 'experience' && (
          <div className="space-y-5">
            <h3 className="text-base font-semibold t-heading flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-raiya-400" /> Experience & Qualification
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <InputField label="Min Experience (years)" type="number" min={0} value={formData.minExperience || ''} onChange={e => update('minExperience', e.target.value)} placeholder="e.g. 3" />
              <InputField label="Max Experience (years)" type="number" min={0} value={formData.maxExperience || ''} onChange={e => update('maxExperience', e.target.value)} placeholder="e.g. 8" />
              <SelectField label="Qualification" options={QUALIFICATIONS} value={formData.qualification || ''} onChange={e => update('qualification', e.target.value)} />
              <InputField label="Preferred Qualification" value={formData.preferredQualification || ''} onChange={e => update('preferredQualification', e.target.value)} placeholder="e.g. M.Tech AI/ML" />
              <div className="sm:col-span-2">
                <InputField label="Domain Expertise" value={formData.domainExpertise || ''} onChange={e => update('domainExpertise', e.target.value)} placeholder="e.g. FinTech, SaaS, Healthcare" />
              </div>
            </div>
          </div>
        )}

        {currentStep === 'skills' && (
          <div className="space-y-5">
            <h3 className="text-base font-semibold t-heading flex items-center gap-2">
              <Code className="w-4 h-4 text-raiya-400" /> Skills
            </h3>
            <TagInput label="Required Skills *" tags={formData.requiredSkills || []} onChange={v => update('requiredSkills', v)} placeholder="e.g. Python, REST APIs..." />
            <TagInput label="Preferred Skills" tags={formData.preferredSkills || []} onChange={v => update('preferredSkills', v)} placeholder="e.g. GraphQL, gRPC..." />
            <TagInput label="Soft Skills" tags={formData.softSkills || []} onChange={v => update('softSkills', v)} placeholder="e.g. Communication, Leadership..." />
          </div>
        )}

        {currentStep === 'tech' && (
          <div className="space-y-5">
            <h3 className="text-base font-semibold t-heading flex items-center gap-2">
              <Cpu className="w-4 h-4 text-raiya-400" /> Technologies
            </h3>
            <TagInput label="Technologies" tags={formData.technologies || []} onChange={v => update('technologies', v)} placeholder="e.g. Python 3.x, Java..." />
            <TagInput label="Frameworks" tags={formData.frameworks || []} onChange={v => update('frameworks', v)} placeholder="e.g. FastAPI, React..." />
            <TagInput label="Databases" tags={formData.databases || []} onChange={v => update('databases', v)} placeholder="e.g. PostgreSQL, Redis..." />
            <TagInput label="Tools" tags={formData.tools || []} onChange={v => update('tools', v)} placeholder="e.g. Docker, Git..." />
            <TagInput label="Cloud" tags={formData.cloud || []} onChange={v => update('cloud', v)} placeholder="e.g. AWS, GCP..." />
          </div>
        )}

        {currentStep === 'responsibilities' && (
          <div className="space-y-5">
            <h3 className="text-base font-semibold t-heading flex items-center gap-2">
              <ListChecks className="w-4 h-4 text-raiya-400" /> Responsibilities
            </h3>
            <ResponsibilityBuilder
              responsibilities={formData.responsibilities || []}
              onChange={v => update('responsibilities', v)}
            />
          </div>
        )}

        {currentStep === 'screening' && (
          <div className="space-y-5">
            <h3 className="text-base font-semibold t-heading flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-raiya-400" /> Screening Questions
            </h3>
            <ScreeningQuestionBuilder
              questions={formData.screeningQuestions || []}
              onChange={v => update('screeningQuestions', v)}
            />
          </div>
        )}
      </motion.div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={() => stepIndex > 0 && setCurrentStep(STEPS[stepIndex - 1].id)}
          disabled={stepIndex === 0}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
            stepIndex === 0
              ? 't-faintest cursor-not-allowed border border-white/5'
              : 't-muted border border-white/10 hover:border-white/20 hover:bg-white/5 hover:text-white'
          }`}
        >
          ← Previous
        </button>
        <button
          onClick={() => stepIndex < STEPS.length - 1 && setCurrentStep(STEPS[stepIndex + 1].id)}
          disabled={stepIndex === STEPS.length - 1}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
            stepIndex === STEPS.length - 1
              ? 't-faintest cursor-not-allowed border border-white/5'
              : 'bg-gradient-to-r from-raiya-600 to-raiya-500 hover:from-raiya-500 hover:to-raiya-400 text-white shadow-lg shadow-raiya-500/15'
          }`}
        >
          Next →
        </button>
      </div>
    </div>
  )
}
