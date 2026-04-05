import {
  formatActivity,
  prepareUploadData,
  processJDFiles,
  processResumeFiles,
} from './dashboard-logic.js';

export function createState() {
  return {
    jdFiles: [],
    resumeFiles: [],
    pollIntervalId: null,
  };
}

export function getElements(doc = document) {
  return {
    doc,
    mobileMenuBtn: doc.getElementById('mobileMenuBtn'),
    sidebar: doc.getElementById('sidebar'),
    sidebarOverlay: doc.getElementById('sidebarOverlay'),
    closeSidebar: doc.getElementById('closeSidebar'),
    browseJDsHeader: doc.getElementById('browseJDsHeader'),
    browseResumesHeader: doc.getElementById('browseResumesHeader'),
    jdDropZone: doc.getElementById('jdDropZone'),
    jdInput: doc.getElementById('jdInput'),
    jdList: doc.getElementById('jdList'),
    jdCount: doc.getElementById('jdCount'),
    resumeDropZone: doc.getElementById('resumeDropZone'),
    resumeInput: doc.getElementById('resumeInput'),
    resumeList: doc.getElementById('resumeList'),
    resumeCount: doc.getElementById('resumeCount'),
    startProcessing: doc.getElementById('startProcessing'),
    activityFeed: doc.getElementById('activityFeed'),
    jdOverviewList: doc.getElementById('jdOverviewList'),
    resumeOverviewList: doc.getElementById('resumeOverviewList'),
    sessionDot: doc.getElementById('sessionDot'),
    sessionText: doc.getElementById('sessionText'),
    sidebarName: doc.getElementById('sidebar-name'),
    sidebarInitials: doc.getElementById('sidebar-initials'),
    sidebarRole: doc.getElementById('sidebar-role'),
  };
}

export function normalizeLegacyUiText(doc = document) {
  const badges = doc.querySelectorAll('.badge');
  if (badges[0]) badges[0].innerHTML = '<span aria-hidden="true">AI</span><span>AI-Powered</span>';
  if (badges[1]) badges[1].innerHTML = '<span aria-hidden="true">UP</span><span>Bulk Processing</span>';

  const startProcessing = doc.getElementById('startProcessing');
  if (startProcessing) startProcessing.textContent = 'Start Screening';

  doc.querySelectorAll('.upload-icon').forEach((icon) => {
    icon.textContent = '+';
    icon.setAttribute('aria-hidden', 'true');
  });

  const defaultActivityIcon = doc.querySelector('#defaultActivity .icon');
  if (defaultActivityIcon) defaultActivityIcon.textContent = '+';
}

function getActivityVisual(type) {
  if (type === 'jd') {
    return {
      iconBg: 'bg-blue-100 dark:bg-blue-900',
      iconColor: 'text-blue-600 dark:text-blue-200',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    };
  }

  if (type === 'resume') {
    return {
      iconBg: 'bg-emerald-100 dark:bg-emerald-900',
      iconColor: 'text-emerald-600 dark:text-emerald-200',
      icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
    };
  }

  if (type === 'success') {
    return {
      iconBg: 'bg-emerald-100 dark:bg-emerald-900',
      iconColor: 'text-emerald-600 dark:text-emerald-200',
      icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    };
  }

  return {
    iconBg: 'bg-slate-100 dark:bg-slate-700',
    iconColor: 'text-slate-600 dark:text-slate-400',
    icon: 'M12 6v6m0 0v6m0-6h6m0 0h6',
  };
}

export function addActivity(elements, message, type = 'default') {
  if (!elements.activityFeed) return null;

  const defaultActivity = elements.doc.getElementById('defaultActivity');
  if (defaultActivity) defaultActivity.style.display = 'none';

  const activityData = formatActivity(message, type);
  const visual = getActivityVisual(type);

  const activity = elements.doc.createElement('div');
  activity.className = 'card p-4 flex items-start gap-4 mb-3';
  activity.innerHTML = `
    <div class="p-2 ${visual.iconBg} rounded-lg flex-shrink-0">
      <svg class="w-5 h-5 ${visual.iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${visual.icon}"></path>
      </svg>
    </div>
    <div class="flex-1 min-w-0">
      <p class="activity-title text-slate-900 dark:text-white">
        <span class="activity-text">${activityData.message}</span>
      </p>
      <p class="activity-meta text-slate-500 dark:text-slate-400">${activityData.timestamp}</p>
    </div>
  `;

  elements.activityFeed.insertBefore(activity, elements.activityFeed.firstChild);
  while (elements.activityFeed.children.length > 5) {
    elements.activityFeed.removeChild(elements.activityFeed.lastChild);
  }

  return activity;
}

export function updateOverviewLists(state, elements) {
  if (elements.jdOverviewList) {
    elements.jdOverviewList.innerHTML =
      state.jdFiles.length === 0 ? '' : state.jdFiles.map((file) => `<div>${file.name}</div>`).join('');
  }

  if (elements.resumeOverviewList) {
    elements.resumeOverviewList.innerHTML =
      state.resumeFiles.length === 0 ? '' : state.resumeFiles.map((file) => `<div>${file.name}</div>`).join('');
  }
}

export function updateProcessButton(state, elements) {
  if (elements.startProcessing) {
    elements.startProcessing.disabled = !(state.jdFiles.length > 0 && state.resumeFiles.length > 0);
  }
}

export function updateJDDisplay(state, elements) {
  if (elements.jdCount) elements.jdCount.textContent = String(state.jdFiles.length);

  if (elements.jdList) {
    elements.jdList.innerHTML =
      state.jdFiles.length === 0
        ? ''
        : state.jdFiles
            .map(
              (file, index) => `
              <div class="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200 dark:bg-blue-900/20 dark:border-blue-800">
                <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.707.293V19a2 2 0 01-2 2z"></path>
                </svg>
                <div class="flex-1 min-w-0">
                  <p class="font-medium text-slate-900 truncate dark:text-white">${file.name}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">${(file.size / 1024).toFixed(1)} KB</p>
                </div>
                <button type="button" data-remove-jd="${index}" class="p-1 hover:bg-blue-100 rounded transition-colors dark:hover:bg-blue-800">
                  <svg class="w-4 h-4 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>
            `,
            )
            .join('');
  }

  updateOverviewLists(state, elements);
  updateProcessButton(state, elements);
}

export function updateResumeDisplay(state, elements) {
  if (elements.resumeCount) elements.resumeCount.textContent = String(state.resumeFiles.length);

  if (elements.resumeList) {
    elements.resumeList.innerHTML =
      state.resumeFiles.length === 0
        ? ''
        : state.resumeFiles
            .map(
              (file, index) => `
              <div class="flex items-center gap-3 p-3 bg-emerald-50 rounded-lg border border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800">
                <svg class="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
                </svg>
                <div class="flex-1 min-w-0">
                  <p class="font-medium text-slate-900 truncate dark:text-white">${file.name}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">${(file.size / 1024).toFixed(1)} KB</p>
                </div>
                <button type="button" data-remove-resume="${index}" class="p-1 hover:bg-emerald-100 rounded transition-colors dark:hover:bg-emerald-800">
                  <svg class="w-4 h-4 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>
            `,
            )
            .join('');
  }

  updateOverviewLists(state, elements);
  updateProcessButton(state, elements);
}

export function handleJDFiles(files, state, elements, deps) {
  const { added, alertMessage } = processJDFiles(files, state.jdFiles);
  if (alertMessage) deps.alertFn(alertMessage);

  state.jdFiles.push(...added);
  if (added.length > 0) {
    addActivity(
      elements,
      `Added ${added.length} job description${added.length > 1 ? 's' : ''}: ${added.map((file) => file.name).join(', ')}`,
      'jd',
    );
  }

  updateJDDisplay(state, elements);
  return added;
}

export function handleResumeFiles(files, state, elements) {
  const added = processResumeFiles(files);
  state.resumeFiles.push(...added);

  if (added.length > 0) {
    addActivity(
      elements,
      `Added ${added.length} resume${added.length > 1 ? 's' : ''}: ${added.map((file) => file.name).join(', ')}`,
      'resume',
    );
  }

  updateResumeDisplay(state, elements);
  return added;
}

export function removeJD(index, state, elements) {
  state.jdFiles.splice(index, 1);
  updateJDDisplay(state, elements);
  addActivity(elements, 'Removed a job description', 'jd');
}

export function removeResume(index, state, elements) {
  state.resumeFiles.splice(index, 1);
  updateResumeDisplay(state, elements);
  addActivity(elements, 'Removed a resume', 'resume');
}

export async function startProcessingFlow(state, elements, deps) {
  if (state.jdFiles.length === 0 || state.resumeFiles.length === 0) {
    deps.alertFn('Please upload both job descriptions and resumes before starting.');
    return false;
  }

  const totalCombinations = state.jdFiles.length * state.resumeFiles.length;
  const confirmed = deps.confirmFn(
    `Ready to process ${state.resumeFiles.length} resumes against ${state.jdFiles.length} job descriptions (${totalCombinations} total comparisons)?`,
  );

  if (!confirmed) return false;

  elements.startProcessing.disabled = true;
  elements.startProcessing.textContent = 'Processing...';
  addActivity(elements, `Screening process started: ${state.jdFiles.length} JD x ${state.resumeFiles.length} resumes...`, 'success');

  try {
    addActivity(elements, 'Uploading Job Descriptions...', 'jd');
    const jdResponse = await deps.fetchFn('/api/upload?type=jd', {
      method: 'POST',
      body: prepareUploadData(state.jdFiles),
    });
    if (!jdResponse.ok) throw new Error('Failed to upload JDs');

    addActivity(elements, 'Uploading Resumes...', 'resume');
    const resumeResponse = await deps.fetchFn('/api/upload?type=resume', {
      method: 'POST',
      body: prepareUploadData(state.resumeFiles),
    });
    if (!resumeResponse.ok) throw new Error('Failed to upload Resumes');

    addActivity(elements, 'Running AI Analysis...', 'default');
    const processResponse = await deps.fetchFn('/api/process', { method: 'POST' });
    if (!processResponse.ok) throw new Error('Processing failed');

    addActivity(elements, 'Processing Started! Redirecting to queue...', 'success');
    if (typeof deps.navigateFn === 'function') {
      deps.navigateFn('bulk-processing.html');
    } else {
      deps.windowRef.location.href = 'bulk-processing.html';
    }
    return true;
  } catch (error) {
    deps.alertFn(`Error: ${error.message}`);
    addActivity(elements, `Error: ${error.message}`, 'default');
    return false;
  } finally {
    elements.startProcessing.disabled = false;
    elements.startProcessing.textContent = 'Start Screening';
    updateProcessButton(state, elements);
  }
}

export async function updateActiveSession(doc = document, fetchFn = globalThis.fetch, logger = console) {
  if (typeof fetchFn !== 'function') return false;

  try {
    const response = await fetchFn('/api/jobs');
    if (!response.ok) return false;

    const jobs = await response.json();
    const isProcessing = jobs.some((job) => ['In Progress', 'Queued'].includes(job.status));
    const sessionDot = doc.getElementById('sessionDot');
    const sessionText = doc.getElementById('sessionText');

    if (sessionDot && sessionText) {
      sessionDot.className = isProcessing
        ? 'h-2 w-2 rounded-full bg-emerald-400 animate-pulse'
        : 'h-2 w-2 rounded-full bg-red-500';
      sessionText.textContent = isProcessing ? 'Active Session' : 'Idle';
    }

    return isProcessing;
  } catch (error) {
    logger.error?.(error);
    return false;
  }
}

export function syncSidebar(doc = document, storage = globalThis.localStorage) {
  const name = storage?.getItem?.('profileName');
  const email = storage?.getItem?.('profileEmail');

  if (name) {
    const nameEl = doc.getElementById('sidebar-name');
    const initialsEl = doc.getElementById('sidebar-initials');
    if (nameEl) nameEl.textContent = name;
    if (initialsEl) {
      initialsEl.textContent = name
        .split(' ')
        .map((part) => part[0])
        .join('')
        .substring(0, 2)
        .toUpperCase();
    }
  }

  if (email) {
    const roleEl = doc.getElementById('sidebar-role');
    if (roleEl) roleEl.textContent = email;
  }
}

function bindMobileMenu(elements) {
  elements.mobileMenuBtn?.addEventListener('click', () => {
    elements.sidebar?.classList.remove('-translate-x-full');
    elements.sidebarOverlay?.classList.remove('hidden');
  });

  elements.closeSidebar?.addEventListener('click', () => {
    elements.sidebar?.classList.add('-translate-x-full');
    elements.sidebarOverlay?.classList.add('hidden');
  });

  elements.sidebarOverlay?.addEventListener('click', () => {
    elements.sidebar?.classList.add('-translate-x-full');
    elements.sidebarOverlay?.classList.add('hidden');
  });
}

function bindUploadEvents(state, elements, deps) {
  elements.browseJDsHeader?.addEventListener('click', () => elements.jdInput?.click());
  elements.browseResumesHeader?.addEventListener('click', () => elements.resumeInput?.click());

  elements.jdDropZone?.addEventListener('click', () => elements.jdInput?.click());
  elements.jdDropZone?.addEventListener('dragover', (event) => {
    event.preventDefault();
    elements.jdDropZone.classList.add('drag-active');
  });
  elements.jdDropZone?.addEventListener('dragleave', () => {
    elements.jdDropZone.classList.remove('drag-active');
  });
  elements.jdDropZone?.addEventListener('drop', (event) => {
    event.preventDefault();
    elements.jdDropZone.classList.remove('drag-active');
    handleJDFiles(event.dataTransfer.files, state, elements, deps);
  });
  elements.jdInput?.addEventListener('change', (event) => handleJDFiles(event.target.files, state, elements, deps));

  elements.resumeDropZone?.addEventListener('click', () => elements.resumeInput?.click());
  elements.resumeDropZone?.addEventListener('dragover', (event) => {
    event.preventDefault();
    elements.resumeDropZone.classList.add('drag-active');
  });
  elements.resumeDropZone?.addEventListener('dragleave', () => {
    elements.resumeDropZone.classList.remove('drag-active');
  });
  elements.resumeDropZone?.addEventListener('drop', (event) => {
    event.preventDefault();
    elements.resumeDropZone.classList.remove('drag-active');
    handleResumeFiles(event.dataTransfer.files, state, elements);
  });
  elements.resumeInput?.addEventListener('change', (event) => handleResumeFiles(event.target.files, state, elements));
}

function bindListActions(state, elements) {
  elements.jdList?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-remove-jd]');
    if (!button) return;
    removeJD(Number(button.dataset.removeJd), state, elements);
  });

  elements.resumeList?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-remove-resume]');
    if (!button) return;
    removeResume(Number(button.dataset.removeResume), state, elements);
  });
}

export function initRecruiterPlatform({
  doc = document,
  windowRef = window,
  fetchFn = windowRef.fetch?.bind(windowRef),
  alertFn = windowRef.alert?.bind(windowRef) ?? (() => {}),
  confirmFn = windowRef.confirm?.bind(windowRef) ?? (() => true),
  storage = windowRef.localStorage,
  setIntervalFn = windowRef.setInterval?.bind(windowRef),
  logger = console,
  state = createState(),
} = {}) {
  const elements = getElements(doc);
  const deps = { windowRef, fetchFn, alertFn, confirmFn, storage, setIntervalFn, logger };
  deps.navigateFn = (href) => {
    windowRef.location.href = href;
  };

  normalizeLegacyUiText(doc);
  bindMobileMenu(elements);
  bindUploadEvents(state, elements, deps);
  bindListActions(state, elements);

  if (elements.startProcessing) {
    elements.startProcessing.addEventListener('click', () => startProcessingFlow(state, elements, deps));
  }

  syncSidebar(doc, storage);
  updateProcessButton(state, elements);

  const poll = () => updateActiveSession(doc, fetchFn, logger);
  if (setIntervalFn) {
    state.pollIntervalId = setIntervalFn(poll, 2000);
  }
  poll();

  return { state, elements, deps, poll };
}
