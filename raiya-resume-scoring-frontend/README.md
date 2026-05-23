# RAIYA: Recruiting Resume Scoring System — Next.js Frontend

AI-Powered Resume Screening Platform by **SpeedTech.ai**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Tech Stack](#tech-stack)
3. [Project Architecture](#project-architecture)
4. [Theming System](#theming-system)
5. [Routing & Page Map](#routing--page-map)
6. [Detailed Page Workflows](#detailed-page-workflows)
7. [Reusable Components](#reusable-components)
8. [Static Data Layer](#static-data-layer)
9. [Admin Dashboard](#admin-dashboard)
10. [Build & Deployment](#build--deployment)
11. [Demo Mode](#demo-mode)

---

## Quick Start

```powershell
# 1. Copy the company logo
copy "..\streamlit_frontend_images\company_logo.jpeg" "public\company_logo.jpeg"

# 2. Install dependencies
npm install

# 3. Run development server
npm run dev
# → Opens at http://localhost:3000

# 4. Build static export (optional)
npm run build
# → Outputs to out/ folder
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | **Next.js 15** (App Router) | SSR/SSG routing, layouts, static export |
| Styling | **Tailwind CSS 4** | Utility-first CSS with custom RAIYA theme |
| Charts | **Recharts** | Radar charts, bar charts, donut charts |
| Animations | **Framer Motion** | Page transitions and micro-animations |
| Icons | **Lucide React** | Consistent SVG icon library |
| Toasts | **react-hot-toast** | Toast notification system |
| PDF Export | **@react-pdf/renderer** | Client-side PDF generation |
| Theming | **next-themes** + custom `ThemeProvider` | Dark/Light mode toggling |
| Date Utils | **date-fns** | Date formatting utilities |
| Typography | **Google Fonts (Inter)** | 300–900 weight range |

**Build Configuration** (`next.config.mjs`):
- `output: 'export'` — fully static HTML export (no Node.js server required)
- `trailingSlash: true` — ensures clean URL routing for static hosts
- `images.unoptimized: true` — bypasses Next.js Image Optimization for static export

---

## Project Architecture

```
raiya-nextjs-frontend/
├── public/
│   ├── company_logo.jpeg          # SpeedTech.ai brand logo
│   └── robots.txt                 # SEO crawling rules
├── src/
│   ├── app/
│   │   ├── layout.js              # Root layout (ThemeProvider, Toaster, fonts, SEO meta)
│   │   ├── page.js                # Root "/" → auto-redirects to /login
│   │   ├── globals.css            # Design system (theme tokens, glass-card, animations)
│   │   ├── not-found.js           # Custom 404 page
│   │   ├── login/page.js          # Split-screen login with SpeedTech.ai branding
│   │   ├── signup/page.js         # Recruiter registration with password strength meter
│   │   ├── forgot-password/page.js# Email OTP request flow
│   │   ├── reset-password/page.js # 6-digit OTP + new password form
│   │   ├── (dashboard)/           # Route group — shared Sidebar + Header layout
│   │   │   ├── layout.js          # Dashboard shell (Sidebar + Header + main content)
│   │   │   ├── create-job/page.js # ★ NEW — Manual/Upload JD creation + weight assignment
│   │   │   ├── platform/page.js   # Resume upload + scoring (unlocked after JD creation)
│   │   │   ├── jd-weights/page.js # Full-page JD weight editor with 8 sections + salary
│   │   │   ├── processing/page.js # Real-time batch processing queue with charts
│   │   │   ├── results/page.js    # Ranked candidate table with quick stats
│   │   │   ├── results/[id]/      # Dynamic candidate report (score circle, radar, breakdown)
│   │   │   ├── compare/page.js    # Side-by-side comparison with JD alignment analysis
│   │   │   ├── history/page.js    # Past batch scoring sessions
│   │   │   └── settings/page.js   # Profile + Recruiter Profile + appearance + scoring config
│   │   └── admin/                 # Admin panel — separate layout with red accent branding
│   │       ├── layout.js          # Admin sidebar (red-themed) + header
│   │       ├── page.js            # System overview (batch summary, token usage, ReAct trace)
│   │       ├── recruiters/        # Per-recruiter scoring statistics
│   │       ├── llm-metrics/       # LLM model performance breakdown
│   │       ├── agent-metrics/     # Agent pipeline performance
│   │       ├── processing-time/   # Processing time analytics
│   │       ├── email-perf/        # Email delivery statistics
│   │       └── jd-accuracy/       # JD weight accuracy analysis
│   ├── components/
│   │   ├── ThemeProvider.jsx      # Context-based dark/light theme with localStorage persistence
│   │   ├── charts/
│   │   │   ├── RadarChart.jsx     # Single-candidate radar chart (Recharts)
│   │   │   ├── CompareRadar.jsx   # Multi-candidate overlaid radar (up to 3 series)
│   │   │   ├── ScoreDistChart.jsx # Score distribution bar chart
│   │   │   └── StatusDonutChart.jsx # Processing status donut/pie chart
│   │   ├── jd/                    # ★ NEW — Job Description creation components
│   │   │   ├── JobForm.jsx        # Multi-step form wizard (6 steps)
│   │   │   ├── WeightAssignment.jsx # Weight panel with accordions + auto-suggest
│   │   │   ├── WeightSlider.jsx   # Individual range slider component
│   │   │   ├── CriteriaAccordion.jsx # Expandable section with criteria sliders
│   │   │   ├── TagInput.jsx       # Animated tag input with add/remove
│   │   │   ├── ResponsibilityBuilder.jsx # Dynamic responsibility list builder
│   │   │   ├── ScreeningQuestionBuilder.jsx # Question builder (Yes/No, MCQ, Text)
│   │   │   ├── UploadJD.jsx       # Drag-drop upload with extraction simulation
│   │   │   └── JDPreview.jsx      # Live JD preview card
│   │   └── layout/
│   │       ├── Sidebar.jsx        # 8 nav items (incl. Create Job) with Briefcase icon
│   │       └── Header.jsx         # Sticky header with notifications, theme toggle, profile dropdown
│   └── data/
│       └── static-data.js         # All demo data + recruiter profile + weight presets
├── package.json
├── next.config.mjs
├── postcss.config.mjs
├── eslint.config.mjs
└── jsconfig.json                  # Path alias: @/ → src/
```

---

## Theming System

The app implements a **full dark/light theme system** using CSS custom properties.

### How It Works

1. **`ThemeProvider.jsx`** — A React Context provider that:
   - Defaults to dark mode (`html.dark` class)
   - Persists the user's choice to `localStorage` under key `raiya-theme`
   - Toggles `html.dark` / `html.light` classes on `<html>`
   - Updates `<meta name="theme-color">` dynamically (`#0f0c29` dark / `#f0f4ff` light)
   - Exposes `{ dark, toggle }` via `useTheme()` hook

2. **`globals.css`** — Defines **60+ CSS custom properties** under `html.dark` and `html.light`:
   - Background gradients, text colors, glass-card styles
   - Input/dropdown/scrollbar/tooltip/chart theming
   - Badge variants (Excellent/Good/Average/Poor/Rejected)

3. **Utility Classes** — Theme-aware helpers used throughout:
   - `.t-heading`, `.t-body`, `.t-muted`, `.t-faint`, `.t-faintest` — text colors
   - `.t-input` — themed input styling
   - `.t-row-hover`, `.t-row-alt`, `.t-divider` — table/list row styles
   - `.glass-card` — glassmorphism card with backdrop blur and hover glow
   - `.gradient-text` — indigo gradient text for "RAIYA" branding
   - `.float`, `.pulse-glow`, `.shimmer` — micro-animations

---

## Routing & Page Map

### Authentication Routes (No Sidebar)

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `page.js` | Auto-redirects to `/login` via `useEffect` |
| `/login` | `login/page.js` | Split-screen auth with admin detection |
| `/signup` | `signup/page.js` | Recruiter registration with password strength meter |
| `/forgot-password` | `forgot-password/page.js` | Email-based OTP request |
| `/reset-password` | `reset-password/page.js` | 6-digit OTP verification + new password |

### Dashboard Routes (Sidebar + Header via `(dashboard)/layout.js`)

| Route | Component | Description |
|-------|-----------|-------------|
| `/create-job` | `create-job/page.js` | ★ **NEW** — Manual JD creation + Upload extraction + weight assignment |
| `/platform` | `platform/page.js` | Resume upload + scoring (gated by confirmed JD) |
| `/jd-weights` | `jd-weights/page.js` | Standalone JD weight editor (8 sections + salary) |
| `/processing` | `processing/page.js` | Batch processing queue with real-time progress |
| `/results` | `results/page.js` | Ranked candidate table with export options |
| `/results/[id]` | `results/[id]/page.js` | Individual candidate report with radar chart |
| `/compare` | `compare/page.js` | Side-by-side candidate comparison with JD overlay |
| `/history` | `history/page.js` | Historical batch scoring sessions |
| `/settings` | `settings/page.js` | Profile + Recruiter Profile + appearance + scoring |

### Admin Routes (Separate Red-Themed Layout via `admin/layout.js`)

| Route | Component | Description |
|-------|-----------|-------------|
| `/admin` | `admin/page.js` | System overview dashboard |
| `/admin/recruiters` | `admin/recruiters/page.js` | Per-recruiter scoring statistics |
| `/admin/llm-metrics` | `admin/llm-metrics/page.js` | LLM token usage and cost breakdown |
| `/admin/agent-metrics` | `admin/agent-metrics/page.js` | Agent pipeline performance metrics |
| `/admin/processing-time` | `admin/processing-time/page.js` | Processing time analytics |
| `/admin/email-perf` | `admin/email-perf/page.js` | Email delivery performance stats |
| `/admin/jd-accuracy` | `admin/jd-accuracy/page.js` | JD weight accuracy analysis |

---

## Detailed Page Workflows

### 1. Login Page (`/login`)

**Layout:** Split-screen — left panel (branding) + right panel (form)

**Flow:**
1. Left panel displays SpeedTech.ai logo with floating animation, "RAIYA" gradient title, and feature tags (`AI Scoring`, `Batch Processing`, `Smart Ranking`)
2. Right panel presents email + password form with client-side validation:
   - Email: required, regex validation
   - Password: required, min 4 characters
   - Show/hide password toggle (Eye/EyeOff icons)
3. **Admin Detection:** If credentials are `admin@speedtech.ai` / `admin123` → redirects to `/admin`
4. **Recruiter Login:** Any other valid credentials → redirects to `/platform`
5. Links to `/signup` and `/forgot-password`
6. Demo mode hint box shows both credential sets

### 2. Signup Page (`/signup`)

**Layout:** Split-screen identical to login

**Flow:**
1. Collects: Full Name, Email, Password, Confirm Password
2. **Password Strength Meter** — real-time visual bar with 5 levels:
   - Weak (red 20%) → Fair (amber 40%) → Good (blue 60%) → Strong (green 80%) → Very Strong (emerald 100%)
   - Criteria: length ≥6, length ≥10, uppercase, digits, special characters
3. Password match indicator (green checkmark when confirmed)
4. On submit → simulated 1.5s delay → toast success → redirects to `/login`

### 3. Forgot Password (`/forgot-password`)

**Flow:**
1. Centered card layout with logo
2. Email input with Mail icon prefix and validation
3. On submit → simulated 1.5s loading → shows success state:
   - Green checkmark icon
   - "OTP Sent!" confirmation with user's email
   - "Enter OTP" button linking to `/reset-password`

### 4. Reset Password (`/reset-password`)

**Flow:**
1. Six individual single-character OTP input fields
2. New Password + Confirm Password fields
3. On submit → toast "Password reset successfully!" → redirects to `/login`

### 5. Create Job Description (`/create-job`) ⭐ NEW

**Layout:** Dashboard shell with tabbed interface + 2-column layout

**Purpose:** Central hub for creating JDs (manual or upload). Once a JD is created with confirmed weights, the recruiter is routed to `/platform` to upload resumes and start scoring.

**Tabs:**
```
[ Manual Creation ] | [ Upload JD Document ]
```

**Tab 1 — Manual Creation (2-column desktop, stacked mobile):**

*Left Column — 6-Step Form Wizard:*
1. **Basic Information** — Job Role (auto-filled from recruiter profile), Department, Employment Type, Work Mode, Location, Salary Range, Open Positions, Deadline
2. **Experience & Qualification** — Min/Max Experience, Qualification, Preferred Qualification, Domain Expertise
3. **Skills** — Required Skills (tag input), Preferred Skills, Soft Skills
4. **Technologies** — Technologies, Frameworks, Databases, Tools, Cloud (all tag inputs)
5. **Responsibilities** — Dynamic list builder with add/remove
6. **Screening Questions** — Question builder supporting Yes/No, MCQ, and Text answer types

*Right Column — Sticky Weight Assignment Panel:*
- 10 expandable accordion sections (Relevant Experience, Experience, Qualification, Technologies, Skills, Position, Tools, Certifications, Responsibilities, Salary)
- Each section has a weight slider + individual criteria sliders when expanded
- Real-time total progress bar: green (=100), amber (<100), red (>100)
- **Auto Suggest** — simulates AI weight suggestion with 2s loading spinner
- **Reset** — zeros all weights
- **Confirm Weights** — locks weights (disabled until total = 100)

*Bottom — Live JD Preview:*
- Professional job posting card that updates in real-time as the form is filled
- Shows all entered data: role, meta badges, requirements, skills, tech stack, responsibilities, screening questions

**Tab 2 — Upload JD Document:**
- Drag-and-drop dropzone (PDF/DOCX)
- Simulated 3-stage upload: Uploading → Extracting with AI → Generating Weights
- Extracted JD preview card with all parsed fields
- Auto-generated weight assignment panel (editable)
- Same confirmation flow as manual creation

**Persistence & Data Flow:**
- **Auto-save**: Form data and weights are debounce-saved to `localStorage` every second
- **Draft Restore**: On page load, drafts are restored with a toast notification
- **Save Draft button**: Explicit save with confirmation toast
- **Publish flow**: "Create Job & Go to Platform" button → shadowy confirmation modal ("Are you sure you want to create this job?") with job summary → Confirmed → saved to `localStorage` key `raiya_confirmed_job` → redirects to `/platform`
- **Cancel flow**: "No, Keep Editing" → stays on page with auto-save, toast: "Keep editing! Your data is auto-saved."

**localStorage Keys:**
| Key | Purpose |
|-----|---------|
| `raiya_jd_draft` | Form data draft (cleared on publish) |
| `raiya_jd_weights` | Weight data draft (cleared on publish) |
| `raiya_weights_confirmed` | Boolean flag for weight confirmation |
| `raiya_confirmed_job` | Final confirmed job (read by Platform page) |
| `raiya_recruiter_profile` | Recruiter profile settings (read for auto-fill) |

---

### 6. Recruiter Platform (`/platform`) ⭐ Updated Workflow

**Layout:** Dashboard shell with step indicator

**4-Step Guided Workflow:**

```
Step 1: Create JD → Step 2: Review & Confirm → Step 3: Upload Resumes → Step 4: Start Scoring
```

**Gate Logic:** Platform reads `raiya_confirmed_job` from `localStorage`. If no confirmed job exists, the entire page shows a locked state.

**No Job Created (Locked State):**
- Lock icon with "No Job Description Found" heading
- "Create Job Description" button → routes to `/create-job`
- Resume upload section is completely locked and hidden

**Job Created (Unlocked State):**
- **JD Summary Card** — shows job role, department, location, work mode, employment type, confirmation status, weight total, and creation date
- **"View Details" button** → opens shadowy modal with full JD details:
  - All form fields in a grid layout
  - Skills as pill badges (color-coded by category)
  - Responsibilities bullet list
  - Weight breakdown grid (all 10 sections with values)
  - "Looks Good — Start Resume Scoring" button at bottom
- **"Are you ready for resume scoring?" alert** — shadowy confirmation modal after viewing JD:
  - Job role summary
  - "Review Again" and "Yes, Let's Go!" buttons
  - On confirm → unlocks resume upload with success toast

**Resume Upload (locked until scoring confirmed):**
- Overlay with Lock icon and "Review JD First" message until scoring is confirmed
- Once unlocked, click loads 8 demo resume files
- Each file shows name + size with hover-to-remove button
- Scrollable file list (max-height 256px)

**Start Scoring:**
- "Start Scoring with N Resumes" button
- Shows loading toast → navigates to `/processing`

### 6. JD Weight Assignment (`/jd-weights`)

**Layout:** Full-page standalone weight editor

**Features:**
- **Job Information Panel** — editable fields for title, experience, qualification, etc.
- **Weight Total Bar** — real-time sum with validation indicator (green ✓ / amber ⚠)
- **8 Expandable Sections** — each with:
  - Section weight slider (0–50, step 0.5)
  - Sub-criteria scores (0–100) with individual range sliders
  - Sections: Relevant Experience, Experience, Qualification, Technologies, Skills, Position, Tools, Certifications
- **Salary Section** — separate slider (0–20)
- **Two-Click Confirm** — first click asks "Any further changes?", second click saves and redirects to `/platform`

### 7. Processing Queue (`/processing`)

**Layout:** Full-width dashboard with metrics, table, charts, and activity log

**Sections:**
1. **Batch Summary Panel** — 4 stat cards: Batch ID, Total Files, Status (with animated badge), ETA
2. **Global Progress Bar** — gradient bar with breakdown: Completed, In Progress, Queued, Failed, Avg Score
3. **Search & Filters** — text search (filename/job ID), status filter dropdown, sort dropdown (date/score/status/filename)
4. **Processing Queue Table** — columns: Job ID, File Name, Status (badge with icon), Progress (bar + %), Last Step, Score (color-coded), Actions
   - Actions: "Results" link (completed), Eye icon (pipeline details modal), Alert icon (error details)
5. **Visualizations** — 2-column grid:
   - Score Distribution bar chart (Poor/Average/Good/Excellent)
   - Processing Status donut chart
6. **Recent Activity Timeline** — vertical timeline with color-coded dots:
   - Green (success), Red (error), Blue (info), Amber (milestone), Purple (queue)
7. **Pipeline Details Modal** — shows 6-stage pipeline for any selected job:
   - Text Extraction → Text Normalization → Section Mapping → AI Scoring → Score Aggregation → Report Generation
   - Each stage shows done/active/pending status with timestamps
8. **Export CSV** — generates and downloads a CSV of all processing jobs

### 8. Results Dashboard (`/results`)

**Layout:** Stats cards → search → ranked candidate table → email modal

**Features:**
1. **Quick Stats** — 4 cards: Top Match score, Average score, Excellent count (≥85), Good+ count (≥70)
2. **Search Bar** — filters candidates by name
3. **Sortable Table** — columns: Rank (medal colors for top 3), Candidate (name + email), Score (color-coded), Status (badge), Top Section, Action (View Report link)
   - Click Score header to sort asc/desc
4. **Export Options:**
   - CSV download — headers: Rank, Name, Email, Score, Status, Top Section, Match Level
   - Text Report download — formatted plaintext with all candidate details
5. **Email Top Candidates Modal** — lists all candidates with score ≥ 70
   - Shows name, email, score for each
   - "Send Interview Email to N Candidates" button with loading spinner
   - Simulated email sending with success toast

### 9. Candidate Report (`/results/[id]`)

**Layout:** Detailed single-candidate analysis page

**Static Generation:** Uses `generateStaticParams()` to pre-render all candidate pages at build time.

**Sections:**
1. **Header** — back arrow to `/results`, candidate name + email + resume filename, "Download Report" button
2. **Score Overview Grid** (4 cards):
   - Animated SVG score circle (0–100 with arc fill animation)
   - Match Level, Top Section, Skills Matched ratio
3. **Radar Chart** — 8-axis radar visualization of section raw scores (Recharts)
4. **Section Breakdown** — horizontal bar chart for each section:
   - Section name, progress bar (color-coded), raw score, JD weight, weighted contribution
5. **Skills Grid** (2 columns):
   - Matched Skills — green pill badges
   - Missing Skills — red pill badges (or "No gaps" message)
6. **Strengths & Weaknesses** (2 columns) — bullet lists with green/amber accents
7. **AI Recommendation** — full-text recommendation paragraph in RAIYA-branded card
8. **Report Download** — generates formatted plaintext file with all candidate data

### 10. Compare Candidates (`/compare`)

**Layout:** Two-candidate selector → JD fit summary → radar → tabbed analysis

**Features:**
1. **Candidate Selectors** — two dropdowns to pick candidates (mutual exclusion enforced)
2. **JD Baseline Toggle** — enables/disables JD requirement overlay on radar chart
3. **JD Fit Summary Cards** — for each candidate:
   - Overall JD fit percentage with color-coded bar
   - Alignment label (Exceeds ≥100% / Meets ≥80% / Partial ≥60% / Gap <60%)
   - Score + skills matched count
4. **Overlaid Radar Chart** — up to 3 series (2 candidates + JD baseline)
   - Legend with color indicators
5. **Tabbed Analysis:**
   - **📊 Section Scores Tab** — comparison table with columns: Section, Candidate 1 Score, Candidate 2 Score, Diff, JD Expectation, JD% for each
     - JD% color legend: Exceeds (green) / Meets (blue) / Partial (amber) / Gap (red)
   - **🛠️ Skills vs JD Tab** — three skill blocks:
     - Technologies Required — checkmark/cross matrix per candidate
     - Tools Required — same format
     - Certifications Preferred — same format
     - Missing Skills Comparison — side-by-side missing skill pills
   - **💡 Recommendation Tab** — per-candidate:
     - Strengths list, Weaknesses list, AI Recommendation block, JD Fit bar
     - **🏆 Verdict** — declares winner with JD alignment lead percentage and contextual insight

**JD Alignment Calculation:**
- `jdExpectation(section)` = `max_criteria * 0.7 + avg_criteria * 0.3` (weighted benchmark)
- `jdAlignPct(raw, section)` = `min((raw / expectation) * 100, 100)`
- `overallJdFit(candidate)` = average of all section alignment percentages

### 11. Batch History (`/history`)

**Layout:** Stats row → batch card list

**Features:**
1. **Summary Stats** — Total Batches, Total Resumes, Completed, Active
2. **Batch Cards** — each showing:
   - Batch name, JD title, creation date
   - Status indicator (completed ✓ / processing ⟳)
   - Resume breakdown: done, failed, running, queued
   - Progress bar (% completed)

### 12. Settings (`/settings`) — Enhanced

**Layout:** Stacked settings cards

**Sections:**
1. **Profile** — Full Name, Email, Recruiter ID (read-only), Company
2. **Recruiter Profile Settings** ★ NEW — Auto-fill configuration for Create Job:
   - Recruiter Name, Company Name, Recruiter ID (read-only), Designation, Department
   - Preferred Job Role (dropdown: Python Backend Dev, AI Engineer, Frontend Dev, etc.)
   - Default Work Mode (On-site / Remote / Hybrid)
   - Default Location
   - Hiring Roles (tag input with add/remove)
   - Persisted to `localStorage` key `raiya_recruiter_profile`
   - Auto-fills Job Role, Department, Work Mode, Location in Create Job page
3. **Appearance** — Dark Mode toggle
4. **Notifications** — Email Notifications toggle, In-App Alerts toggle
5. **Scoring Configuration** — Auto-reject threshold slider (0–100%)
6. **Save Button** — saves recruiter profile to `localStorage` + toast confirmation

---

## Reusable Components

### `ThemeProvider.jsx`
- React Context for dark/light theme state
- `useTheme()` hook → `{ dark: boolean, toggle: () => void }`
- Persists to `localStorage`, syncs `<html>` class and `<meta theme-color>`

### `Sidebar.jsx`
- 8 navigation items with icons and descriptions (added **Create Job** with Briefcase icon between Platform and JD Weights)
- Active route detection via `usePathname()`
- **Collapsible** on desktop (72px icon-only mode)
- **Mobile drawer** with overlay backdrop
- SpeedTech.ai logo with link to `/platform`
- User avatar in footer showing "Recruiter Demo / RAIYA:001"

### JD Components (`components/jd/`) ★ NEW
- **`JobForm.jsx`** — 6-step form wizard with stepper progress bar and animated step transitions
- **`WeightAssignment.jsx`** — Full weight panel with accordion sections, progress bar, auto-suggest, reset, and confirm
- **`WeightSlider.jsx`** — Individual range slider with gradient track and live value display
- **`CriteriaAccordion.jsx`** — Expandable section showing section weight + individual criteria sliders
- **`TagInput.jsx`** — Animated tag input with Enter-to-add, backspace-to-remove, and X-to-delete
- **`ResponsibilityBuilder.jsx`** — Dynamic numbered list with add/remove and drag-handle UI
- **`ScreeningQuestionBuilder.jsx`** — Question builder supporting Yes/No, MCQ (with options), and Text answer types
- **`UploadJD.jsx`** — Drag-drop upload zone with 3-stage simulated extraction and confirmation flow
- **`JDPreview.jsx`** — Real-time job posting preview card that updates as form data changes

### `Header.jsx`
- Sticky top header with backdrop blur
- **Mobile menu toggle** (hamburger icon, `lg:hidden`)
- **Theme Toggle** — Sun/Moon icon button, toast feedback
- **Notifications Dropdown** — 8 demo notifications with:
  - Unread count badge (animated pulse)
  - Color-coded dots (success/error/info)
  - "Mark all read" action
  - "View All Activity →" link to `/processing`
- **Profile Dropdown** — user info, session status, links to Settings, Access Control, Preferences, Theme toggle, Sign Out

### Chart Components (all use `dynamic(() => import(...), { ssr: false })`)
- **`RadarChart.jsx`** — single-candidate 8-axis radar (Recharts `RadarChart`)
- **`CompareRadar.jsx`** — multi-series overlaid radar for candidate comparison
- **`ScoreDistChart.jsx`** — bar chart showing score distribution buckets
- **`StatusDonutChart.jsx`** — donut/pie chart for processing job status

---

## Static Data Layer

All frontend data is sourced from `src/data/static-data.js`. **No backend API calls are made.**

### Exports

| Export | Type | Description |
|--------|------|-------------|
| `DEMO_CANDIDATES` | Array (8) | Full candidate profiles with scores, breakdowns, skills, recommendations |
| `DEMO_JD_WEIGHTS` | Object | JD configuration with job info, 8 scoring sections, salary, criteria |
| `DEMO_JOBS` | Array (15) | Processing queue jobs with status, progress, step, score |
| `DEMO_BATCHES` | Array (5) | Historical batch sessions with resume counts and status |
| `SECTION_LABELS` | Object | Emoji-prefixed labels for 8 scoring sections |
| `DEMO_RECRUITER_PROFILE` | Object | ★ NEW — Recruiter name, company, designation, hiring roles, defaults |
| `DEMO_CREATED_JOBS` | Array (2) | ★ NEW — Sample created job descriptions with status |
| `DEMO_WEIGHT_PRESETS` | Object | ★ NEW — Role-based weight presets (Python Backend, AI, Frontend) |
| `DEMO_EXTRACTED_JD` | Object | ★ NEW — Mock extracted JD for upload simulation |
| `getScoreColor(score)` | Function | Returns hex color: ≥85 green, ≥70 blue, ≥55 amber, ≥40 orange, <40 red |
| `getScoreStatus(score)` | Function | Returns label: Excellent / Good / Average / Poor / Rejected |
| `getScoreBadgeClass(score)` | Function | Returns CSS class: `badge-excellent` through `badge-rejected` |

### Scoring Sections (8 + Salary)

| Section | Default Weight | Description |
|---------|---------------|-------------|
| Relevant Experience | 20.0 | Years of relevant industry experience |
| Experience | 15.0 | Total years of professional experience |
| Qualification | 10.0 | Academic degree level |
| Technologies | 20.0 | Required tech stack match |
| Skills | 10.0 | Soft skills and competencies |
| Position | 5.0 | Seniority level alignment |
| Tools | 10.0 | DevOps and productivity tools |
| Certifications | 5.0 | Professional certifications |
| Salary | 5.0 | Salary expectation alignment |
| **Total** | **100.0** | |

---

## Admin Dashboard

Accessed via `admin@speedtech.ai` / `admin123` login. Uses a **separate layout** with red-accent branding.

### Admin Overview (`/admin`)

Displays real pipeline data modeled after the backend's `agent_controller.py`, `token_usage_monitor.py`, and `react_trace.json`:

1. **Batch Processing Summary** — 6 metrics: Total Resumes, Extracted, Schema Validated, Math Validated, Scored, Failed
2. **JD Extraction & Weight Validation** — 5 checks: JD Extracted, Schema Valid, Weight Sum (100%), LLM Weight Gen, Math Validation
3. **LLM Token Usage** — 6 metrics: Prompt/Completion/Total Tokens, Est. Cost (USD), Total Latency, API Calls
   - Component breakdown table: LLM Context Layer, AI Scorer, Corrective RAG, Explainability Engine, JD Weight Generator
4. **Per-Resume Pipeline Table** — 8 columns: Resume, Extracted, Schema Valid, Math Valid, Score, Hallucinations, Accuracy, Authority
5. **Agent ReAct Trace** — 10-node LangGraph pipeline visualization:
   - `validate_inputs → run_pinecone → run_corrective_rag → run_llm_context → run_ai_scorer → run_evidence → run_final_validation → generate_explanation → generate_report → authority_check`
   - Each node shows: Thought, Action, Observation, Answer, Time
6. **Authority Validation** — 6 integrity checks: score_in_range, has_explanation, has_evidence, no_hallucinations, math_confident, has_pinecone_scores

### Admin Sub-Pages

| Page | Content |
|------|---------|
| `/admin/recruiters` | Per-recruiter scoring statistics and usage |
| `/admin/llm-metrics` | LLM model performance, token costs, latency |
| `/admin/agent-metrics` | Agent pipeline performance and reliability |
| `/admin/processing-time` | Processing time distribution and analytics |
| `/admin/email-perf` | Email delivery success rates and stats |
| `/admin/jd-accuracy` | JD weight generation accuracy analysis |

---

## Build & Deployment

```powershell
# Development
npm run dev          # → http://localhost:3000

# Production build (static export)
npm run build        # → out/ folder

# Lint
npm run lint         # ESLint with Next.js config
```

**Static Export:** The app is configured for `output: 'export'`, generating a fully static `out/` folder that can be deployed to any static hosting (Vercel, Netlify, GitHub Pages, S3, etc.) without a Node.js server.

**Dynamic Routes:** Candidate report pages (`/results/[id]`) use `generateStaticParams()` to pre-render all candidate pages at build time from `DEMO_CANDIDATES`.

---

## Demo Mode

This is a **fully static frontend** — all data comes from `src/data/static-data.js`. No backend API calls are made. All interactions (uploads, scoring, emails) are simulated with timeouts and toast notifications.

**Demo Credentials:**

| Role | Email | Password | Redirects To |
|------|-------|----------|--------------|
| Recruiter | Any valid email | Any (min 4 chars) | `/platform` |
| Admin | `admin@speedtech.ai` | `admin123` | `/admin` |

---

*Powered by SpeedTech.ai*
