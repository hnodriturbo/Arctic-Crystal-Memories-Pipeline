/** Purpose: Define the Workshop-owned R2 areas shared by browsing and imports. */
export const STORAGE_AREAS = [
  { prefix: 'Cockpit3D-Files/', label: 'Cockpit Reconstruct · scenes and models' },
  { prefix: 'jobs/', label: 'Meshy · generated assets' },
  { prefix: 'converter-jobs/', label: 'Converter · exported files' },
  { prefix: 'uploads/', label: 'Uploaded source files' },
  { prefix: 'Cockpit3D-Scene-History/', label: 'Cockpit · earlier source versions' },
  { prefix: 'archive/', label: 'Archive' },
];

export function allowedStorageKey(key) {
  return typeof key === 'string' && !key.includes('\\') && !key.split('/').some(part => part === '..' || part === '.') && STORAGE_AREAS.some(area => key.startsWith(area.prefix));
}
