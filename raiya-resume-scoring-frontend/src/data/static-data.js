// ─── RAIYA: Recruiting Resume Scoring System — Static Demo Data ───
// All data used by the static frontend. No API calls.

export const APP_NAME = 'RAIYA: Recruiting Resume Scoring System'
export const COMPANY = 'SpeedTech.ai'

// ─── Candidates ──────────────────────────────────────────────────
export const DEMO_CANDIDATES = [
  {
    id: 'candidate-1',
    name: 'Gurjas Singh Gandhi',
    email: 'gurjas@example.com',
    final_score: 87.5,
    score_status: 'Excellent',
    top_section: 'Technologies',
    match_level: 'Strong Match',
    section_breakdown: {
      relevant_experience: { raw_score: 90, jd_weight: 20, weighted_contribution: 18.0 },
      experience: { raw_score: 85, jd_weight: 15, weighted_contribution: 12.75 },
      qualification: { raw_score: 88, jd_weight: 10, weighted_contribution: 8.8 },
      technologies: { raw_score: 92, jd_weight: 20, weighted_contribution: 18.4 },
      skills: { raw_score: 80, jd_weight: 10, weighted_contribution: 8.0 },
      position: { raw_score: 85, jd_weight: 5, weighted_contribution: 4.25 },
      tools: { raw_score: 88, jd_weight: 10, weighted_contribution: 8.8 },
      certifications: { raw_score: 70, jd_weight: 5, weighted_contribution: 3.5 },
    },
    salary_score: 5.0,
    matched_skills: ['Python', 'TensorFlow', 'PyTorch', 'React', 'Node.js', 'AWS', 'Docker', 'Git'],
    missing_skills: ['Kubernetes', 'Terraform'],
    strengths: [
      'Strong AI/ML background with 5+ years of relevant experience',
      'Excellent proficiency in Python ecosystem and deep learning frameworks',
      'Proven track record of deploying production-grade ML pipelines',
      'Strong communication and leadership skills',
    ],
    weaknesses: [
      'Limited experience with infrastructure-as-code (Terraform)',
      'No Kubernetes orchestration experience mentioned',
    ],
    recommendation: 'Highly recommended for interview. Candidate demonstrates strong technical depth in AI/ML with production deployment experience. Minor gaps in DevOps tooling can be addressed on the job.',
    resume_file: 'Gurjas_Singh_Gandhi_Resume.pdf',
  },
  {
    id: 'candidate-2',
    name: 'Priya Sharma',
    email: 'priya.s@example.com',
    final_score: 82.3,
    score_status: 'Good',
    top_section: 'Skills',
    match_level: 'Good Match',
    section_breakdown: {
      relevant_experience: { raw_score: 75, jd_weight: 20, weighted_contribution: 15.0 },
      experience: { raw_score: 80, jd_weight: 15, weighted_contribution: 12.0 },
      qualification: { raw_score: 95, jd_weight: 10, weighted_contribution: 9.5 },
      technologies: { raw_score: 78, jd_weight: 20, weighted_contribution: 15.6 },
      skills: { raw_score: 88, jd_weight: 10, weighted_contribution: 8.8 },
      position: { raw_score: 70, jd_weight: 5, weighted_contribution: 3.5 },
      tools: { raw_score: 82, jd_weight: 10, weighted_contribution: 8.2 },
      certifications: { raw_score: 80, jd_weight: 5, weighted_contribution: 4.0 },
    },
    salary_score: 5.7,
    matched_skills: ['React', 'TypeScript', 'Node.js', 'PostgreSQL', 'Git', 'Jira'],
    missing_skills: ['Python', 'AWS', 'Docker'],
    strengths: [
      'Master\'s degree in Computer Science from IIT Delhi',
      'Exceptional soft skills and team collaboration abilities',
      'Strong frontend development expertise with React ecosystem',
    ],
    weaknesses: [
      'Limited Python and cloud infrastructure experience',
      'No containerization experience (Docker/Kubernetes)',
      'Backend experience primarily in JavaScript ecosystem',
    ],
    recommendation: 'Good candidate for frontend-heavy roles. Consider for interview with a focus on backend skill assessment.',
    resume_file: 'Priya_Sharma_Resume.pdf',
  },
  {
    id: 'candidate-3',
    name: 'Arjun Patel',
    email: 'arjun.p@example.com',
    final_score: 76.1,
    score_status: 'Good',
    top_section: 'Experience',
    match_level: 'Moderate Match',
    section_breakdown: {
      relevant_experience: { raw_score: 70, jd_weight: 20, weighted_contribution: 14.0 },
      experience: { raw_score: 90, jd_weight: 15, weighted_contribution: 13.5 },
      qualification: { raw_score: 70, jd_weight: 10, weighted_contribution: 7.0 },
      technologies: { raw_score: 72, jd_weight: 20, weighted_contribution: 14.4 },
      skills: { raw_score: 75, jd_weight: 10, weighted_contribution: 7.5 },
      position: { raw_score: 80, jd_weight: 5, weighted_contribution: 4.0 },
      tools: { raw_score: 68, jd_weight: 10, weighted_contribution: 6.8 },
      certifications: { raw_score: 60, jd_weight: 5, weighted_contribution: 3.0 },
    },
    salary_score: 5.9,
    matched_skills: ['Java', 'Spring Boot', 'PostgreSQL', 'Redis', 'Jenkins'],
    missing_skills: ['Python', 'React', 'AWS', 'Docker', 'TensorFlow'],
    strengths: [
      '8+ years of software development experience',
      'Strong Java and Spring Boot backend expertise',
      'Experience leading teams of 5-10 developers',
    ],
    weaknesses: [
      'Technology stack mismatch — primarily Java, not Python/React',
      'No machine learning or AI project experience',
      'Missing modern frontend framework experience',
    ],
    recommendation: 'Experienced developer but technology stack doesn\'t align well. Consider only if team needs Java backend expertise.',
    resume_file: 'Arjun_Patel_Resume.pdf',
  },
  {
    id: 'candidate-4',
    name: 'Sneha Reddy',
    email: 'sneha.r@example.com',
    final_score: 91.2,
    score_status: 'Excellent',
    top_section: 'Technologies',
    match_level: 'Excellent Match',
    section_breakdown: {
      relevant_experience: { raw_score: 95, jd_weight: 20, weighted_contribution: 19.0 },
      experience: { raw_score: 88, jd_weight: 15, weighted_contribution: 13.2 },
      qualification: { raw_score: 90, jd_weight: 10, weighted_contribution: 9.0 },
      technologies: { raw_score: 95, jd_weight: 20, weighted_contribution: 19.0 },
      skills: { raw_score: 85, jd_weight: 10, weighted_contribution: 8.5 },
      position: { raw_score: 90, jd_weight: 5, weighted_contribution: 4.5 },
      tools: { raw_score: 92, jd_weight: 10, weighted_contribution: 9.2 },
      certifications: { raw_score: 90, jd_weight: 5, weighted_contribution: 4.5 },
    },
    salary_score: 4.3,
    matched_skills: ['Python', 'React', 'Node.js', 'AWS', 'Docker', 'Kubernetes', 'TensorFlow', 'Git'],
    missing_skills: [],
    strengths: [
      'Full-stack expertise spanning Python, React, and cloud-native technologies',
      'AWS Certified Solutions Architect with production cloud experience',
      'Led migration of monolith to microservices for 10M+ user platform',
      'Published research in NeurIPS on efficient model training',
    ],
    weaknesses: [
      'Salary expectation may be above budget range',
    ],
    recommendation: 'Top candidate. Immediate interview recommended. Exceptional technical depth with leadership experience.',
    resume_file: 'Sneha_Reddy_Resume.pdf',
  },
  {
    id: 'candidate-5',
    name: 'Rahul Menon',
    email: 'rahul.m@example.com',
    final_score: 58.4,
    score_status: 'Average',
    top_section: 'Qualification',
    match_level: 'Below Average',
    section_breakdown: {
      relevant_experience: { raw_score: 45, jd_weight: 20, weighted_contribution: 9.0 },
      experience: { raw_score: 50, jd_weight: 15, weighted_contribution: 7.5 },
      qualification: { raw_score: 85, jd_weight: 10, weighted_contribution: 8.5 },
      technologies: { raw_score: 55, jd_weight: 20, weighted_contribution: 11.0 },
      skills: { raw_score: 60, jd_weight: 10, weighted_contribution: 6.0 },
      position: { raw_score: 40, jd_weight: 5, weighted_contribution: 2.0 },
      tools: { raw_score: 50, jd_weight: 10, weighted_contribution: 5.0 },
      certifications: { raw_score: 40, jd_weight: 5, weighted_contribution: 2.0 },
    },
    salary_score: 7.4,
    matched_skills: ['Python', 'SQL', 'Git'],
    missing_skills: ['React', 'Node.js', 'AWS', 'Docker', 'TensorFlow', 'Kubernetes'],
    strengths: [
      'M.Tech from IIT Bombay in Computer Science',
      'Strong academic foundation in algorithms and data structures',
    ],
    weaknesses: [
      'Only 2 years of professional experience',
      'Limited exposure to modern web frameworks and cloud platforms',
      'No production deployment or DevOps experience',
      'Missing most required technologies',
    ],
    recommendation: 'Not recommended for senior role. May be suitable for junior/entry-level position with mentoring.',
    resume_file: 'Rahul_Menon_Resume.pdf',
  },
  {
    id: 'candidate-6',
    name: 'Ananya Gupta',
    email: 'ananya.g@example.com',
    final_score: 71.8,
    score_status: 'Good',
    top_section: 'Tools',
    match_level: 'Moderate Match',
    section_breakdown: {
      relevant_experience: { raw_score: 65, jd_weight: 20, weighted_contribution: 13.0 },
      experience: { raw_score: 72, jd_weight: 15, weighted_contribution: 10.8 },
      qualification: { raw_score: 75, jd_weight: 10, weighted_contribution: 7.5 },
      technologies: { raw_score: 70, jd_weight: 20, weighted_contribution: 14.0 },
      skills: { raw_score: 72, jd_weight: 10, weighted_contribution: 7.2 },
      position: { raw_score: 65, jd_weight: 5, weighted_contribution: 3.25 },
      tools: { raw_score: 80, jd_weight: 10, weighted_contribution: 8.0 },
      certifications: { raw_score: 55, jd_weight: 5, weighted_contribution: 2.75 },
    },
    salary_score: 5.3,
    matched_skills: ['Python', 'Django', 'PostgreSQL', 'Docker', 'Jenkins', 'Git'],
    missing_skills: ['React', 'Node.js', 'AWS', 'TensorFlow'],
    strengths: [
      'Solid Python backend development with Django',
      'Good DevOps practices with Docker and Jenkins CI/CD',
      'Experience with database optimization and query tuning',
    ],
    weaknesses: [
      'No frontend framework experience (React/Vue)',
      'Missing cloud platform experience (AWS/GCP/Azure)',
      'No machine learning or AI experience',
    ],
    recommendation: 'Suitable for backend-focused roles. Would need significant upskilling for full-stack or AI/ML positions.',
    resume_file: 'Ananya_Gupta_Resume.pdf',
  },
  {
    id: 'candidate-7',
    name: 'Vikram Joshi',
    email: 'vikram.j@example.com',
    final_score: 44.2,
    score_status: 'Poor',
    top_section: 'Qualification',
    match_level: 'Poor Match',
    section_breakdown: {
      relevant_experience: { raw_score: 30, jd_weight: 20, weighted_contribution: 6.0 },
      experience: { raw_score: 35, jd_weight: 15, weighted_contribution: 5.25 },
      qualification: { raw_score: 70, jd_weight: 10, weighted_contribution: 7.0 },
      technologies: { raw_score: 40, jd_weight: 20, weighted_contribution: 8.0 },
      skills: { raw_score: 45, jd_weight: 10, weighted_contribution: 4.5 },
      position: { raw_score: 30, jd_weight: 5, weighted_contribution: 1.5 },
      tools: { raw_score: 42, jd_weight: 10, weighted_contribution: 4.2 },
      certifications: { raw_score: 25, jd_weight: 5, weighted_contribution: 1.25 },
    },
    salary_score: 6.5,
    matched_skills: ['HTML', 'CSS', 'JavaScript'],
    missing_skills: ['Python', 'React', 'Node.js', 'AWS', 'Docker', 'TensorFlow', 'PostgreSQL', 'Git'],
    strengths: [
      'Bachelor\'s degree in Information Technology',
      'Basic web development skills',
    ],
    weaknesses: [
      'Only 1 year of experience — insufficient for senior role',
      'Missing all core required technologies',
      'No project portfolio or production deployments',
      'No relevant certifications',
    ],
    recommendation: 'Not recommended. Significant skill gap across all scoring sections.',
    resume_file: 'Vikram_Joshi_Resume.pdf',
  },
  {
    id: 'candidate-8',
    name: 'Kavitha Nair',
    email: 'kavitha.n@example.com',
    final_score: 79.6,
    score_status: 'Good',
    top_section: 'Certifications',
    match_level: 'Good Match',
    section_breakdown: {
      relevant_experience: { raw_score: 78, jd_weight: 20, weighted_contribution: 15.6 },
      experience: { raw_score: 75, jd_weight: 15, weighted_contribution: 11.25 },
      qualification: { raw_score: 80, jd_weight: 10, weighted_contribution: 8.0 },
      technologies: { raw_score: 76, jd_weight: 20, weighted_contribution: 15.2 },
      skills: { raw_score: 82, jd_weight: 10, weighted_contribution: 8.2 },
      position: { raw_score: 75, jd_weight: 5, weighted_contribution: 3.75 },
      tools: { raw_score: 74, jd_weight: 10, weighted_contribution: 7.4 },
      certifications: { raw_score: 95, jd_weight: 5, weighted_contribution: 4.75 },
    },
    salary_score: 5.5,
    matched_skills: ['Python', 'React', 'AWS', 'Docker', 'Git', 'PostgreSQL'],
    missing_skills: ['Kubernetes', 'TensorFlow'],
    strengths: [
      'AWS Solutions Architect + PMP certified',
      'Well-rounded full-stack skills across Python and React',
      'Strong project management and agile experience',
      '6 years of progressive experience in tech companies',
    ],
    weaknesses: [
      'No machine learning or AI-specific experience',
      'Missing Kubernetes experience for container orchestration',
    ],
    recommendation: 'Strong candidate with excellent certifications. Recommended for interview — especially for roles requiring PM+Dev hybrid skills.',
    resume_file: 'Kavitha_Nair_Resume.pdf',
  },
]

// ─── JD Weights ──────────────────────────────────────────────────
export const DEMO_JD_WEIGHTS = {
  job_title: 'Senior Full-Stack Developer',
  experience: '5+ years',
  qualification: 'B.Tech / M.Tech in Computer Science',
  technologies: ['React', 'Node.js', 'Python', 'AWS', 'PostgreSQL'],
  skills: ['problem solving', 'system design', 'communication', 'teamwork'],
  tools: ['Docker', 'Jenkins', 'Git', 'Jira'],
  certifications: ['AWS Certified Solutions Architect', 'PMP'],
  location: 'Bangalore, India',
  position: 'Senior',
  employment_type: 'Full-time',
  work_mode: { remote: true, office: false, hybrid: true },
  responsibilities: [
    'Lead development of scalable web applications',
    'Design and implement microservices architecture',
    'Mentor junior developers and conduct code reviews',
    'Collaborate with product and design teams',
    'Ensure CI/CD best practices and deployment automation',
  ],
  scoring: {
    relevant_experience: {
      weight: 20.0,
      criteria: { '≥5 years relevant': 90, '3-4 years relevant': 70, '1-2 years relevant': 40, '<1 year relevant': 10 },
    },
    experience: {
      weight: 15.0,
      criteria: { '≥8 years': 100, '5-7 years': 80, '3-4 years': 50, '<3 years': 20 },
    },
    qualification: {
      weight: 10.0,
      criteria: { PhD: 100, Masters: 85, Bachelors: 70, Diploma: 40, Certification: 30 },
    },
    technologies: {
      weight: 20.0,
      criteria: { React: 90, 'Node.js': 85, Python: 80, AWS: 75, PostgreSQL: 70 },
    },
    skills: {
      weight: 10.0,
      criteria: { 'problem solving': 80, 'system design': 85, communication: 60, teamwork: 60 },
    },
    position: {
      weight: 5.0,
      criteria: { senior_level: 100, mid_level: 70, entry_level: 40 },
    },
    tools: {
      weight: 10.0,
      criteria: { Docker: 80, Jenkins: 70, Git: 90, Jira: 50 },
    },
    certifications: {
      weight: 5.0,
      criteria: { 'AWS Certified Solutions Architect': 90, PMP: 70 },
    },
  },
  salary: {
    weight: 5.0,
    fallback_score: 50.0,
    criteria: { '3-6 LPA': 40, '6-10 LPA': 70, '>10 LPA': 90 },
  },
}

// ─── Processing Jobs ─────────────────────────────────────────────
export const DEMO_JOBS = [
  { id: 'JOB-001', filename: 'Gurjas_Singh_Gandhi_Resume.pdf', status: 'completed', progress: 100, step: 'Report Generated', score: 87.5, duration: '12s' },
  { id: 'JOB-002', filename: 'Priya_Sharma_Resume.pdf', status: 'completed', progress: 100, step: 'Report Generated', score: 82.3, duration: '14s' },
  { id: 'JOB-003', filename: 'Arjun_Patel_Resume.pdf', status: 'completed', progress: 100, step: 'Report Generated', score: 76.1, duration: '11s' },
  { id: 'JOB-004', filename: 'Sneha_Reddy_Resume.pdf', status: 'completed', progress: 100, step: 'Report Generated', score: 91.2, duration: '13s' },
  { id: 'JOB-005', filename: 'Rahul_Menon_Resume.pdf', status: 'completed', progress: 100, step: 'Report Generated', score: 58.4, duration: '10s' },
  { id: 'JOB-006', filename: 'Ananya_Gupta_Resume.pdf', status: 'completed', progress: 100, step: 'Report Generated', score: 71.8, duration: '12s' },
  { id: 'JOB-007', filename: 'Vikram_Joshi_Resume.pdf', status: 'completed', progress: 100, step: 'Report Generated', score: 44.2, duration: '9s' },
  { id: 'JOB-008', filename: 'Kavitha_Nair_Resume.pdf', status: 'completed', progress: 100, step: 'Report Generated', score: 79.6, duration: '11s' },
  { id: 'JOB-009', filename: 'Amit_Kumar_Resume.pdf', status: 'processing', progress: 65, step: 'AI Scoring', score: null, duration: null },
  { id: 'JOB-010', filename: 'Deepa_Iyer_Resume.pdf', status: 'processing', progress: 40, step: 'Pinecone Similarity', score: null, duration: null },
  { id: 'JOB-011', filename: 'Rohan_Verma_Resume.pdf', status: 'queued', progress: 0, step: 'Waiting', score: null, duration: null },
  { id: 'JOB-012', filename: 'Meera_Krishnan_Resume.pdf', status: 'queued', progress: 0, step: 'Waiting', score: null, duration: null },
  { id: 'JOB-013', filename: 'Sanjay_Dubey_Resume.pdf', status: 'failed', progress: 30, step: 'Error: PDF Corrupt', score: null, duration: null },
  { id: 'JOB-014', filename: 'Nisha_Agarwal_Resume.pdf', status: 'queued', progress: 0, step: 'Waiting', score: null, duration: null },
  { id: 'JOB-015', filename: 'Karthik_Raman_Resume.pdf', status: 'queued', progress: 0, step: 'Waiting', score: null, duration: null },
]

// ─── Batches ─────────────────────────────────────────────────────
export const DEMO_BATCHES = [
  { id: 1, name: 'Batch #1 — Senior Full-Stack', resume_count: 15, completed: 8, failed: 1, processing: 2, queued: 4, status: 'processing', created_at: '2026-04-29T10:30:00Z', jd_title: 'Senior Full-Stack Developer' },
  { id: 2, name: 'Batch #2 — ML Engineer', resume_count: 10, completed: 10, failed: 0, processing: 0, queued: 0, status: 'completed', created_at: '2026-04-28T14:15:00Z', jd_title: 'Machine Learning Engineer' },
  { id: 3, name: 'Batch #3 — DevOps Lead', resume_count: 8, completed: 8, failed: 0, processing: 0, queued: 0, status: 'completed', created_at: '2026-04-27T09:00:00Z', jd_title: 'DevOps Lead' },
  { id: 4, name: 'Batch #4 — Frontend Dev', resume_count: 12, completed: 11, failed: 1, processing: 0, queued: 0, status: 'completed', created_at: '2026-04-25T16:45:00Z', jd_title: 'Senior Frontend Developer' },
  { id: 5, name: 'Batch #5 — Data Scientist', resume_count: 6, completed: 6, failed: 0, processing: 0, queued: 0, status: 'completed', created_at: '2026-04-22T11:30:00Z', jd_title: 'Data Scientist' },
]

// ─── Score Helpers ───────────────────────────────────────────────
export function getScoreColor(score) {
  if (score >= 85) return '#10b981'
  if (score >= 70) return '#3b82f6'
  if (score >= 55) return '#f59e0b'
  if (score >= 40) return '#f97316'
  return '#ef4444'
}

export function getScoreStatus(score) {
  if (score >= 85) return 'Excellent'
  if (score >= 70) return 'Good'
  if (score >= 55) return 'Average'
  if (score >= 40) return 'Poor'
  return 'Rejected'
}

export function getScoreBadgeClass(score) {
  if (score >= 85) return 'badge-excellent'
  if (score >= 70) return 'badge-good'
  if (score >= 55) return 'badge-average'
  if (score >= 40) return 'badge-poor'
  return 'badge-rejected'
}

export const SECTION_LABELS = {
  relevant_experience: '🎯 Relevant Experience',
  experience: '📅 Experience',
  qualification: '🎓 Qualification',
  technologies: '💻 Technologies',
  skills: '🛠️ Skills',
  position: '📊 Position',
  tools: '🔧 Tools',
  certifications: '📜 Certifications',
}

// ─── Recruiter Profile ──────────────────────────────────────────
export const DEMO_RECRUITER_PROFILE = {
  recruiterName: 'Rahul Mehta',
  companyName: 'TechNova',
  recruiterId: 'RAIYA001',
  designation: 'Senior Recruiter',
  department: 'Engineering',
  hiringRoles: [
    'Python Backend Developer',
    'AI Engineer',
    'Frontend Developer',
  ],
  preferredJobRole: 'Python Backend Developer',
  defaultWorkMode: 'Hybrid',
  defaultLocation: 'Pune',
}

// ─── Created Jobs ───────────────────────────────────────────────
export const DEMO_CREATED_JOBS = [
  {
    id: 'JD-001',
    jobRole: 'Python Backend Developer',
    department: 'Engineering',
    employmentType: 'Full-time',
    workMode: 'Hybrid',
    location: 'Pune',
    salaryRange: '15-25 LPA',
    openPositions: 3,
    deadline: '2026-06-15',
    status: 'Published',
    createdAt: '2026-05-01T10:30:00Z',
  },
  {
    id: 'JD-002',
    jobRole: 'AI Engineer',
    department: 'AI/ML',
    employmentType: 'Full-time',
    workMode: 'Remote',
    location: 'Bangalore',
    salaryRange: '20-35 LPA',
    openPositions: 2,
    deadline: '2026-06-30',
    status: 'Draft',
    createdAt: '2026-05-05T14:15:00Z',
  },
]

// ─── Weight Presets ─────────────────────────────────────────────
export const DEMO_WEIGHT_PRESETS = {
  'Python Backend Developer': {
    relevant_experience: { weight: 20, criteria: { 'Python 3.x': 10, 'FastAPI': 6, 'Django': 4 } },
    experience: { weight: 15, criteria: { '≥5 years': 8, '3-4 years': 5, '1-2 years': 2 } },
    qualification: { weight: 8, criteria: { 'Masters': 5, 'Bachelors': 3 } },
    technologies: { weight: 25, criteria: { 'Python': 10, 'FastAPI': 6, 'PostgreSQL': 5, 'Docker': 4 } },
    skills: { weight: 10, criteria: { 'System Design': 5, 'Problem Solving': 3, 'Communication': 2 } },
    position: { weight: 5, criteria: { 'Senior': 3, 'Mid': 2 } },
    tools: { weight: 7, criteria: { 'Git': 3, 'Jenkins': 2, 'Jira': 2 } },
    certifications: { weight: 3, criteria: { 'AWS Certified': 2, 'PMP': 1 } },
    responsibilities: { weight: 4, criteria: { 'API Development': 2, 'Code Review': 2 } },
    salary: { weight: 3, criteria: { '15-25 LPA': 2, '>25 LPA': 1 } },
  },
  'AI Engineer': {
    relevant_experience: { weight: 22, criteria: { 'ML/DL Projects': 12, 'Research Papers': 5, 'Production ML': 5 } },
    experience: { weight: 12, criteria: { '≥5 years': 7, '3-4 years': 3, '1-2 years': 2 } },
    qualification: { weight: 12, criteria: { 'PhD': 7, 'Masters': 4, 'Bachelors': 1 } },
    technologies: { weight: 22, criteria: { 'PyTorch': 8, 'TensorFlow': 7, 'Python': 5, 'CUDA': 2 } },
    skills: { weight: 10, criteria: { 'Model Architecture': 5, 'Math/Stats': 3, 'Paper Reading': 2 } },
    position: { weight: 5, criteria: { 'Lead': 3, 'Senior': 2 } },
    tools: { weight: 7, criteria: { 'MLflow': 3, 'Weights & Biases': 2, 'Git': 2 } },
    certifications: { weight: 3, criteria: { 'Deep Learning Specialization': 2, 'GCP ML': 1 } },
    responsibilities: { weight: 4, criteria: { 'Model Development': 2, 'Experimentation': 2 } },
    salary: { weight: 3, criteria: { '20-35 LPA': 2, '>35 LPA': 1 } },
  },
  'Frontend Developer': {
    relevant_experience: { weight: 18, criteria: { 'React Projects': 10, 'TypeScript': 5, 'Next.js': 3 } },
    experience: { weight: 15, criteria: { '≥5 years': 8, '3-4 years': 5, '1-2 years': 2 } },
    qualification: { weight: 8, criteria: { 'Masters': 4, 'Bachelors': 4 } },
    technologies: { weight: 22, criteria: { 'React': 8, 'TypeScript': 6, 'Next.js': 5, 'CSS/Tailwind': 3 } },
    skills: { weight: 12, criteria: { 'UI/UX Sense': 5, 'Responsive Design': 4, 'Performance': 3 } },
    position: { weight: 5, criteria: { 'Senior': 3, 'Mid': 2 } },
    tools: { weight: 8, criteria: { 'Figma': 3, 'Git': 3, 'Storybook': 2 } },
    certifications: { weight: 3, criteria: { 'Meta Frontend': 2, 'Google UX': 1 } },
    responsibilities: { weight: 5, criteria: { 'Component Architecture': 3, 'Code Review': 2 } },
    salary: { weight: 4, criteria: { '12-20 LPA': 2, '>20 LPA': 2 } },
  },
}

// ─── Extracted JD (Upload Simulation) ───────────────────────────
export const DEMO_EXTRACTED_JD = {
  jobRole: 'Senior Python Backend Developer',
  department: 'Engineering',
  employmentType: 'Full-time',
  workMode: 'Hybrid',
  location: 'Pune, India',
  salaryRange: '18-28 LPA',
  openPositions: 2,
  experience: { min: 4, max: 8 },
  qualification: 'B.Tech / M.Tech in Computer Science',
  preferredQualification: 'M.Tech with AI/ML specialization',
  domainExpertise: 'FinTech / SaaS',
  requiredSkills: ['Python', 'FastAPI', 'REST APIs', 'Microservices', 'System Design'],
  preferredSkills: ['GraphQL', 'gRPC', 'Event-Driven Architecture'],
  softSkills: ['Communication', 'Team Leadership', 'Problem Solving'],
  technologies: ['Python 3.x', 'FastAPI', 'Flask'],
  frameworks: ['FastAPI', 'Django', 'Celery'],
  databases: ['PostgreSQL', 'Redis', 'MongoDB'],
  tools: ['Docker', 'Git', 'Jenkins', 'Jira'],
  cloud: ['AWS', 'GCP'],
  responsibilities: [
    'Design and develop scalable backend APIs using Python and FastAPI',
    'Architect microservices for high-traffic SaaS applications',
    'Implement robust authentication and authorization systems',
    'Optimize database queries and ensure data integrity',
    'Lead code reviews and mentor junior engineers',
    'Collaborate with frontend and DevOps teams for seamless deployments',
  ],
  screeningQuestions: [
    { type: 'yes_no', question: 'Do you have 4+ years of Python backend experience?' },
    { type: 'mcq', question: 'Which framework are you most proficient in?', options: ['FastAPI', 'Django', 'Flask', 'Other'] },
    { type: 'text', question: 'Describe a challenging microservices problem you solved.' },
  ],
}
