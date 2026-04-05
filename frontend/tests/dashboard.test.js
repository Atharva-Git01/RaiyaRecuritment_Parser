import { describe, it, expect } from 'vitest';
import {
  formatActivity,
  getValidFiles,
  isValidFile,
  MAX_FILE_SIZE,
  MAX_JDS,
  prepareUploadData,
  processJDFiles,
  processResumeFiles,
} from '../js/dashboard-logic.js';

describe('Dashboard Logic', () => {
  describe('isValidFile', () => {
    it('accepts valid PDF files', () => {
      const file = { name: 'test.pdf', size: 1024 };
      expect(isValidFile(file)).toBe(true);
    });

    it('rejects invalid extensions', () => {
      const file = { name: 'test.exe', size: 1024 };
      expect(isValidFile(file)).toBe(false);
    });

    it('rejects files over 10MB', () => {
      const file = { name: 'large.pdf', size: 11 * 1024 * 1024 };
      expect(isValidFile(file)).toBe(false);
    });

    it('rejects files without an extension', () => {
      const file = { name: 'resume', size: 1024 };
      expect(isValidFile(file)).toBe(false);
    });
  });

  describe('getValidFiles', () => {
    it('filters invalid files and preserves order', () => {
      const files = [
        { name: 'one.pdf', size: 1000 },
        { name: 'bad.exe', size: 1000 },
        { name: 'two.docx', size: 1000 },
      ];

      expect(getValidFiles(files)).toEqual([
        { name: 'one.pdf', size: 1000 },
        { name: 'two.docx', size: 1000 },
      ]);
    });
  });

  describe('processJDFiles', () => {
    it('adds files when slots are available', () => {
      const newFiles = [{ name: 'jd1.pdf', size: 100 }];
      const currentFiles = [];
      const result = processJDFiles(newFiles, currentFiles);
      expect(result.added).toHaveLength(1);
      expect(result.alertMessage).toBeNull();
    });

    it('respects the MAX_JDS limit and provides an alert message', () => {
      const currentFiles = new Array(MAX_JDS).fill({});
      const newFiles = [{ name: 'jd_extra.pdf', size: 100 }];
      const result = processJDFiles(newFiles, currentFiles);
      expect(result.added).toHaveLength(0);
      expect(result.alertMessage).toContain(`maximum ${MAX_JDS}`);
    });

    it('ignores invalid files while keeping valid ones', () => {
      const result = processJDFiles(
        [
          { name: 'good.doc', size: 5000 },
          { name: 'bad.exe', size: 1000 },
          { name: 'too-large.pdf', size: MAX_FILE_SIZE + 1 },
        ],
        [],
      );

      expect(result.added).toEqual([{ name: 'good.doc', size: 5000 }]);
      expect(result.alertMessage).toBeNull();
    });
  });

  describe('processResumeFiles', () => {
    it('returns only valid resume files', () => {
      const result = processResumeFiles([
        { name: 'resume.pdf', size: 1000 },
        { name: 'resume.docx', size: 1000 },
        { name: 'resume.exe', size: 1000 },
      ]);

      expect(result).toEqual([
        { name: 'resume.pdf', size: 1000 },
        { name: 'resume.docx', size: 1000 },
      ]);
    });
  });

  describe('formatActivity', () => {
    it('returns a formatted activity object with timestamp', () => {
      const message = 'Test activity';
      const result = formatActivity(message, 'jd');
      expect(result.message).toBe(message);
      expect(result.type).toBe('jd');
      expect(result.timestamp).toMatch(/\d{2}:\d{2} [AP]M/);
    });
  });

  describe('prepareUploadData', () => {
    it('appends every file under the files key', () => {
      const files = [
        new File(['jd'], 'jd.pdf', { type: 'application/pdf' }),
        new File(['resume'], 'resume.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }),
      ];

      const formData = prepareUploadData(files);
      const entries = formData.getAll('files');

      expect(entries).toHaveLength(2);
      expect(entries[0].name).toBe('jd.pdf');
      expect(entries[1].name).toBe('resume.docx');
    });
  });
});
