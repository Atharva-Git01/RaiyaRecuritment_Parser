'use client'
import { motion } from 'framer-motion'
import { MapPin, Clock, Briefcase, DollarSign, GraduationCap, Code, Users } from 'lucide-react'

export default function JDPreview({ formData }) {
  const { jobRole, department, employmentType, workMode, location, salaryRange, openPositions, deadline,
    minExperience, maxExperience, qualification, preferredQualification, domainExpertise,
    requiredSkills, preferredSkills, softSkills, technologies, frameworks, databases, tools, cloud,
    responsibilities, screeningQuestions } = formData || {}

  const hasContent = jobRole || department || (requiredSkills?.length > 0)

  if (!hasContent) {
    return (
      <div className="glass-card p-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-raiya-500/10 border border-raiya-500/20 flex items-center justify-center mx-auto mb-3">
          <Briefcase className="w-8 h-8 text-raiya-400/40" />
        </div>
        <p className="text-sm t-faintest">Start filling the form to see a live preview</p>
      </div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold t-heading">{jobRole || 'Untitled Position'}</h2>
          {department && <p className="text-sm t-faint mt-0.5">{department} Department</p>}
        </div>
        <span className="px-3 py-1 rounded-lg bg-raiya-500/15 text-raiya-400 text-xs font-semibold border border-raiya-500/20 whitespace-nowrap">
          Draft Preview
        </span>
      </div>

      {/* Meta badges */}
      <div className="flex flex-wrap gap-2">
        {employmentType && <Badge icon={Briefcase} text={employmentType} />}
        {workMode && <Badge icon={MapPin} text={workMode} />}
        {location && <Badge icon={MapPin} text={location} />}
        {salaryRange && <Badge icon={DollarSign} text={salaryRange} />}
        {openPositions && <Badge icon={Users} text={`${openPositions} position${openPositions > 1 ? 's' : ''}`} />}
        {deadline && <Badge icon={Clock} text={`Deadline: ${deadline}`} />}
      </div>

      <div className="h-px w-full" style={{ background: 'var(--divider)' }} />

      {/* Experience & Qualification */}
      {(minExperience || qualification) && (
        <div className="space-y-2">
          <h4 className="text-xs uppercase tracking-wider t-faintest font-bold flex items-center gap-1.5">
            <GraduationCap className="w-3.5 h-3.5" /> Requirements
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {(minExperience || maxExperience) && <InfoLine label="Experience" value={`${minExperience || 0} - ${maxExperience || '?'} years`} />}
            {qualification && <InfoLine label="Qualification" value={qualification} />}
            {preferredQualification && <InfoLine label="Preferred" value={preferredQualification} />}
            {domainExpertise && <InfoLine label="Domain" value={domainExpertise} />}
          </div>
        </div>
      )}

      {/* Skills */}
      {(requiredSkills?.length > 0 || preferredSkills?.length > 0) && (
        <div className="space-y-2">
          <h4 className="text-xs uppercase tracking-wider t-faintest font-bold flex items-center gap-1.5">
            <Code className="w-3.5 h-3.5" /> Skills
          </h4>
          {requiredSkills?.length > 0 && <TagRow label="Required" tags={requiredSkills} color="raiya" />}
          {preferredSkills?.length > 0 && <TagRow label="Preferred" tags={preferredSkills} color="purple" />}
          {softSkills?.length > 0 && <TagRow label="Soft Skills" tags={softSkills} color="blue" />}
        </div>
      )}

      {/* Tech Stack */}
      {(technologies?.length > 0 || frameworks?.length > 0 || databases?.length > 0) && (
        <div className="space-y-2">
          <h4 className="text-xs uppercase tracking-wider t-faintest font-bold">💻 Tech Stack</h4>
          {technologies?.length > 0 && <TagRow label="Technologies" tags={technologies} color="green" />}
          {frameworks?.length > 0 && <TagRow label="Frameworks" tags={frameworks} color="purple" />}
          {databases?.length > 0 && <TagRow label="Databases" tags={databases} color="blue" />}
          {tools?.length > 0 && <TagRow label="Tools" tags={tools} color="raiya" />}
          {cloud?.length > 0 && <TagRow label="Cloud" tags={cloud} color="green" />}
        </div>
      )}

      {/* Responsibilities */}
      {responsibilities?.length > 0 && responsibilities.some(r => r.trim()) && (
        <div className="space-y-2">
          <h4 className="text-xs uppercase tracking-wider t-faintest font-bold">📋 Responsibilities</h4>
          <ul className="space-y-1.5">
            {responsibilities.filter(r => r.trim()).map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-xs t-muted">
                <span className="text-raiya-400 mt-0.5 flex-shrink-0">▸</span> {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Screening */}
      {screeningQuestions?.length > 0 && screeningQuestions.some(q => q.question.trim()) && (
        <div className="space-y-2">
          <h4 className="text-xs uppercase tracking-wider t-faintest font-bold">❓ Screening Questions</h4>
          {screeningQuestions.filter(q => q.question.trim()).map((q, i) => (
            <div key={i} className="p-2.5 rounded-lg border border-white/5 text-xs t-muted" style={{ background: 'var(--row-alt)' }}>
              <span className="text-raiya-400 font-semibold mr-1">Q{i + 1}.</span> {q.question}
              <span className="ml-2 text-[10px] t-faintest">({q.type === 'yes_no' ? 'Yes/No' : q.type === 'mcq' ? 'MCQ' : 'Text'})</span>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

function Badge({ icon: Icon, text }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium t-muted border border-white/5" style={{ background: 'var(--row-alt)' }}>
      <Icon className="w-3 h-3 t-faintest" /> {text}
    </span>
  )
}

function InfoLine({ label, value }) {
  return (
    <div className="text-xs">
      <span className="t-faintest">{label}: </span>
      <span className="t-muted font-medium">{value}</span>
    </div>
  )
}

function TagRow({ label, tags, color = 'raiya' }) {
  const map = {
    raiya: 'bg-raiya-500/15 text-raiya-300 border-raiya-500/20',
    purple: 'bg-purple-500/15 text-purple-300 border-purple-500/20',
    blue: 'bg-blue-500/15 text-blue-300 border-blue-500/20',
    green: 'bg-green-500/15 text-green-300 border-green-500/20',
  }
  return (
    <div>
      <span className="text-[10px] t-faintest mb-1 block">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {tags.map(t => <span key={t} className={`px-2 py-0.5 rounded-md text-[11px] font-medium border ${map[color]}`}>{t}</span>)}
      </div>
    </div>
  )
}
