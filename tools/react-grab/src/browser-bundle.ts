/**
 * React Grab Browser Bundle
 *
 * This file is built as an IIFE for direct injection into HTML pages.
 * It wraps the browser plugin and auto-registers it.
 *
 * The Vite plugin reads the built version of this file and injects it
 * via transformIndexHtml, making react-grab work automatically without
 * requiring a Chrome extension or manual imports.
 *
 * Note: This runs inside an IIFE injected by the Vite plugin, which already
 * checks for localhost/dev mode before injecting. So we just initialize.
 */

import { registerReactGrabPlugin } from './react-grab-plugin'

// Only run in browser context
if (typeof window !== 'undefined') {
  // The Vite plugin already gates injection to dev mode, so we just initialize.
  // Wait for DOM to be ready, then initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(() => registerReactGrabPlugin(), 100)
    })
  } else {
    // DOM already loaded
    setTimeout(() => registerReactGrabPlugin(), 100)
  }
}
