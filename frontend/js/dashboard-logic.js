/**
 * Dashboard Logic Module
 * Contains pure functions for file validation, state management, and API formatting.
 * Designed for unit testing with Vitest/JSDOM.
 */

export const MAX_JDS = 5;
export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

/**
 * Validates a single file against extension and size constraints.
 * @param {File} file 
 * @returns {boolean}
 */
export function isValidFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  const validExtensions = ['pdf', 'doc', 'docx'];
  return validExtensions.includes(ext) && file.size <= MAX_FILE_SIZE;
}

/**
 * Filters a list of files to only include valid ones.
 * @param {FileList|File[]} files 
 * @returns {File[]}
 */
export function getValidFiles(files) {
  return Array.from(files).filter(isValidFile);
}

/**
 * Processes new JD files while respecting the maximum limit.
 * @param {File[]} newFiles 
 * @param {File[]} currentFiles 
 * @returns {{ added: File[], alertMessage?: string }}
 */
export function processJDFiles(newFiles, currentFiles) {
  const validNewFiles = getValidFiles(newFiles);
  const availableSlots = MAX_JDS - currentFiles.length;
  const filesToAdd = validNewFiles.slice(0, availableSlots);

  let alertMessage = null;
  if (validNewFiles.length > availableSlots) {
    alertMessage = `Only ${availableSlots} more JD files can be added (maximum ${MAX_JDS})`;
  }

  return {
    added: filesToAdd,
    alertMessage
  };
}

/**
 * Processes new Resume files.
 * @param {File[]} newFiles 
 * @returns {File[]}
 */
export function processResumeFiles(newFiles) {
  return getValidFiles(newFiles);
}

/**
 * Formats a message for activity logging.
 * @param {string} message 
 * @param {string} type 
 * @returns {{ message: string, type: string, timestamp: string }}
 */
export function formatActivity(message, type = 'default') {
  return {
    message,
    type,
    timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  };
}

/**
 * Prepares FormData for file uploads.
 * @param {File[]} files 
 * @returns {FormData}
 */
export function prepareUploadData(files) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  return formData;
}
