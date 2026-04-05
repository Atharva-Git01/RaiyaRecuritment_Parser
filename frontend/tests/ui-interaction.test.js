import { beforeEach, describe, expect, it, vi } from 'vitest';
import { JSDOM } from 'jsdom';
import {
  addActivity,
  createState,
  getElements,
  handleJDFiles,
  handleResumeFiles,
  initRecruiterPlatform,
  normalizeLegacyUiText,
  startProcessingFlow,
  updateActiveSession,
  updateJDDisplay,
  updateProcessButton,
  updateResumeDisplay,
} from '../js/recruiter-platform.js';

function buildDom() {
  const dom = new JSDOM(`
    <html>
      <body>
        <div id="sidebar" class="-translate-x-full"></div>
        <div id="sidebarOverlay" class="hidden"></div>
        <button id="mobileMenuBtn"></button>
        <button id="closeSidebar"></button>
        <button id="browseJDsHeader"></button>
        <button id="browseResumesHeader"></button>
        <div class="badge"></div>
        <div class="badge"></div>
        <div id="jdDropZone" class="upload-zone"><div class="upload-icon"></div></div>
        <input id="jdInput" type="file" />
        <div id="jdList"></div>
        <div id="jdCount">0</div>
        <div id="resumeDropZone" class="upload-zone"><div class="upload-icon"></div></div>
        <input id="resumeInput" type="file" />
        <div id="resumeList"></div>
        <div id="resumeCount">0</div>
        <button id="startProcessing" disabled>Broken</button>
        <div id="activityFeed">
          <div id="defaultActivity"><div class="icon">Broken</div></div>
        </div>
        <div id="jdOverviewList"></div>
        <div id="resumeOverviewList"></div>
        <div id="sessionDot"></div>
        <div id="sessionText"></div>
        <div id="sidebar-name"></div>
        <div id="sidebar-initials"></div>
        <div id="sidebar-role"></div>
      </body>
    </html>
  `, { url: 'http://localhost/recruiter-platform.html' });

  return dom;
}

describe('Recruiter Platform Controller', () => {
  let dom;
  let doc;
  let elements;
  let state;

  beforeEach(() => {
    dom = buildDom();
    doc = dom.window.document;
    elements = getElements(doc);
    state = createState();
  });

  it('normalizes legacy UI text and icons', () => {
    normalizeLegacyUiText(doc);

    expect(doc.querySelectorAll('.badge')[0].textContent).toContain('AI-Powered');
    expect(doc.querySelectorAll('.badge')[1].textContent).toContain('Bulk Processing');
    expect(elements.startProcessing.textContent).toBe('Start Screening');
    expect(doc.querySelector('#defaultActivity .icon').textContent).toBe('+');
    expect(doc.querySelectorAll('.upload-icon')[0].textContent).toBe('+');
  });

  it('adds activity entries and caps the feed to five items', () => {
    for (let index = 0; index < 6; index += 1) {
      addActivity(elements, `Event ${index}`, index % 2 === 0 ? 'jd' : 'resume');
    }

    expect(elements.activityFeed.children).toHaveLength(5);
    expect(elements.activityFeed.firstElementChild.textContent).toContain('Event 5');
    expect(elements.activityFeed.textContent).not.toContain('Event 0');
  });

  it('updates JD and resume displays and enables the CTA only when both are present', () => {
    state.jdFiles = [{ name: 'jd.pdf', size: 2048 }];
    state.resumeFiles = [{ name: 'resume.docx', size: 4096 }];

    updateJDDisplay(state, elements);
    updateResumeDisplay(state, elements);
    updateProcessButton(state, elements);

    expect(elements.jdCount.textContent).toBe('1');
    expect(elements.resumeCount.textContent).toBe('1');
    expect(elements.jdList.textContent).toContain('jd.pdf');
    expect(elements.resumeList.textContent).toContain('resume.docx');
    expect(elements.jdOverviewList.textContent).toContain('jd.pdf');
    expect(elements.resumeOverviewList.textContent).toContain('resume.docx');
    expect(elements.startProcessing.disabled).toBe(false);
  });

  it('handles JD uploads, alerts on limit overflow, and keeps only valid files', () => {
    const alertFn = vi.fn();
    state.jdFiles = [
      { name: 'one.pdf', size: 1000 },
      { name: 'two.pdf', size: 1000 },
      { name: 'three.pdf', size: 1000 },
      { name: 'four.pdf', size: 1000 },
    ];

    const added = handleJDFiles(
      [
        { name: 'valid.docx', size: 1000 },
        { name: 'ignored.exe', size: 1000 },
        { name: 'overflow.pdf', size: 1000 },
      ],
      state,
      elements,
      { alertFn },
    );

    expect(added).toHaveLength(1);
    expect(state.jdFiles).toHaveLength(5);
    expect(alertFn).toHaveBeenCalledTimes(1);
    expect(elements.jdList.textContent).toContain('valid.docx');
    expect(elements.jdList.textContent).not.toContain('ignored.exe');
  });

  it('handles resume uploads and ignores invalid files', () => {
    const added = handleResumeFiles(
      [
        { name: 'resume.pdf', size: 1000 },
        { name: 'virus.exe', size: 1000 },
      ],
      state,
      elements,
    );

    expect(added).toHaveLength(1);
    expect(state.resumeFiles).toHaveLength(1);
    expect(elements.resumeList.textContent).toContain('resume.pdf');
    expect(elements.resumeList.textContent).not.toContain('virus.exe');
  });

  it('runs the happy path for processing and redirects to the queue page', async () => {
    state.jdFiles = [{ name: 'jd.pdf', size: 1000 }];
    state.resumeFiles = [{ name: 'resume.pdf', size: 1000 }];

    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true });

    const alertFn = vi.fn();
    const confirmFn = vi.fn(() => true);
    const navigateFn = vi.fn();

    const result = await startProcessingFlow(state, elements, {
      fetchFn,
      alertFn,
      confirmFn,
      windowRef: dom.window,
      navigateFn,
    });

    expect(result).toBe(true);
    expect(confirmFn).toHaveBeenCalledTimes(1);
    expect(fetchFn).toHaveBeenNthCalledWith(
      1,
      '/api/upload?type=jd',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchFn).toHaveBeenNthCalledWith(
      2,
      '/api/upload?type=resume',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchFn).toHaveBeenNthCalledWith(3, '/api/process', { method: 'POST' });
    expect(alertFn).not.toHaveBeenCalled();
    expect(navigateFn).toHaveBeenCalledWith('bulk-processing.html');
    expect(elements.startProcessing.textContent).toBe('Start Screening');
    expect(elements.startProcessing.disabled).toBe(false);
  });

  it('surfaces processing failures and resets the button state', async () => {
    state.jdFiles = [{ name: 'jd.pdf', size: 1000 }];
    state.resumeFiles = [{ name: 'resume.pdf', size: 1000 }];

    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: false });

    const alertFn = vi.fn();

    const result = await startProcessingFlow(state, elements, {
      fetchFn,
      alertFn,
      confirmFn: () => true,
      windowRef: dom.window,
    });

    expect(result).toBe(false);
    expect(alertFn).toHaveBeenCalledWith('Error: Failed to upload Resumes');
    expect(elements.activityFeed.textContent).toContain('Error: Failed to upload Resumes');
    expect(elements.startProcessing.textContent).toBe('Start Screening');
    expect(elements.startProcessing.disabled).toBe(false);
  });

  it('updates the active session indicator based on /api/jobs', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ status: 'Queued' }],
    });

    const isProcessing = await updateActiveSession(doc, fetchFn, console);

    expect(isProcessing).toBe(true);
    expect(elements.sessionText.textContent).toBe('Active Session');
    expect(elements.sessionDot.className).toContain('bg-emerald-400');
  });

  it('initializes the controller, binds events, and syncs sidebar storage', async () => {
    const setIntervalFn = vi.fn(() => 42);
    const fetchFn = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    const storage = {
      getItem: vi.fn((key) => {
        if (key === 'profileName') return 'Raiya Admin';
        if (key === 'profileEmail') return 'admin@raiya.test';
        return null;
      }),
    };

    const controller = initRecruiterPlatform({
      doc,
      windowRef: dom.window,
      fetchFn,
      alertFn: vi.fn(),
      confirmFn: vi.fn(() => true),
      storage,
      setIntervalFn,
      logger: console,
    });

    expect(setIntervalFn).toHaveBeenCalledWith(expect.any(Function), 2000);
    expect(controller.state.pollIntervalId).toBe(42);
    expect(elements.sidebarName.textContent).toBe('Raiya Admin');
    expect(elements.sidebarInitials.textContent).toBe('RA');
    expect(elements.sidebarRole.textContent).toBe('admin@raiya.test');

    elements.mobileMenuBtn.click();
    expect(elements.sidebar.classList.contains('-translate-x-full')).toBe(false);
    expect(elements.sidebarOverlay.classList.contains('hidden')).toBe(false);
  });
});
