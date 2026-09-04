/**
 * File: local-workbench/vite.config.js
 * Purpose:
 *  - Configure the local-only Vinext and Tailwind development application.
 *  - Keep the research UI independent from Sites hosting, Cloudflare and R2.
 */

import tailwindcss from '@tailwindcss/postcss';
import vinext from 'vinext';
import { defineConfig } from 'vite';

export default defineConfig({
  css: { postcss: { plugins: [tailwindcss()] } },
  plugins: [vinext()],
});
