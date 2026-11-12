/**
 * React Grab - AI-powered element selection and modification tool
 *
 * A customized tool merging features from:
 * - Original React Grab repository (https://github.com/user/react-grab)
 * - Cleo.build AI element selection tool
 *
 * Features:
 * - Element selection with crosshairs
 * - Component label display
 * - Multi-element selection (Shift+click, drag box)
 * - Tree navigation (arrow keys)
 * - AI prompt panel for modifications
 * - Copy element info to clipboard
 * - Export to JSON
 *
 * Activation:
 * - Click the cursor button in the bottom-right corner (dark when inactive, orange when active)
 * - Click on any element to open the prompt panel
 * - Or use Cmd+Shift+Z (Mac) / Ctrl+Shift+Z (Windows/Linux) when hovering over an element
 *
 * Only activates in development mode.
 */

export { registerReactGrabPlugin } from './react-grab-plugin'
export type { ReactGrabConfig, ElementContext } from './react-grab-plugin'
