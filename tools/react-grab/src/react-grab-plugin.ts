/**
 * React Grab Plugin
 *
 * Cleo-inspired UI for selecting elements and sending AI-powered modification
 * requests to Catalyst/{{ORCHESTRATOR_NAME}}.
 *
 * Activation:
 * - Click the cursor button in the bottom-right corner (dark when inactive, orange when active)
 * - Click on any element to open the prompt panel
 * - Or use Cmd+Shift+Z (Mac) / Ctrl+Shift+Z (Windows/Linux) when hovering over an element
 *
 * Only activates in development mode.
 */

import { REACT_GRAB_STYLES } from './styles'

// Configuration interface
export interface ReactGrabConfig {
  /** API endpoint for submitting prompts (default: '/api/grab-prompt') */
  apiEndpoint?: string
  /** Enable debug logging (default: false) */
  debug?: boolean
}

// Element context for API submission
export interface ElementContext {
  filePath: string | null
  componentHierarchy: string[]
  htmlSnippet: string
  lineNumber?: number
  rect: {
    top: number
    left: number
    width: number
    height: number
  }
  // Enhanced identification fields
  textContent?: string
  siblingPosition?: {
    index: number
    total: number
    siblingTexts?: string[]
  }
  parentContext?: {
    tagName: string
    textContent?: string
    htmlSnippet?: string
  }
  uniqueIdentifiers?: {
    id?: string
    dataTestId?: string
    dataAttributes?: Record<string, string>
    className?: string
    key?: string
  }
}

// Panel mode type
type PanelMode = 'compact' | 'expanded'

// Default configuration
const defaultConfig: Required<ReactGrabConfig> = {
  apiEndpoint: '/api/grab-prompt',
  debug: false,
}

/**
 * Detect if the page is using React
 * Like Cleo.build, only show the toolbar if React is detected
 */
function isReactApp(): boolean {
  // Check for React DevTools hook
  if ((window as unknown as Record<string, unknown>).__REACT_DEVTOOLS_GLOBAL_HOOK__) {
    return true
  }

  // Check for React fiber on common root elements
  const rootCandidates = [
    document.getElementById('root'),
    document.getElementById('app'),
    document.getElementById('__next'),
    document.querySelector('[data-reactroot]'),
    document.querySelector('#__docusaurus'),
  ].filter(Boolean) as HTMLElement[]

  for (const root of rootCandidates) {
    const keys = Object.keys(root)
    if (keys.some(key => key.startsWith('__reactFiber') || key.startsWith('__reactContainer'))) {
      return true
    }
  }

  // Check body as fallback
  const bodyKeys = Object.keys(document.body)
  if (bodyKeys.some(key => key.startsWith('__reactFiber') || key.startsWith('__reactContainer'))) {
    return true
  }

  return false
}

// Current configuration
let config: Required<ReactGrabConfig> = { ...defaultConfig }

// State management
// Multiple panels support - Map from panel ID to container element
let overlayContainers: Map<string, HTMLDivElement> = new Map()
let expandedPanelContainer: HTMLDivElement | null = null
let toolbarContainer: HTMLDivElement | null = null
let toolbarButton: HTMLButtonElement | null = null
let currentElementContext: ElementContext | null = null
let currentTargetElement: HTMLElement | null = null
let isSubmitting = false
let keyboardListenerAttached = false
let isSelectionModeActive = false
let hoveredElement: HTMLElement | null = null
let panelMode: PanelMode = 'compact'
let conversationHistory: Array<{ role: 'user' | 'assistant'; content: string }> = []
let attachedScreenshots: Array<{ dataUrl: string; name: string }> = []
let currentSessionId: string | null = null
let isStreamingResponse = false
let currentStreamingContent = ''

// Panel tracking - Map from panel ID to element context
let panelContexts: Map<string, { context: ElementContext; element: HTMLElement }> = new Map()

/**
 * Generate a unique panel ID for an element
 */
function generatePanelId(element: HTMLElement): string {
  // Use a combination of tag name, class, and position for uniqueness
  const rect = element.getBoundingClientRect()
  const id = `panel-${element.tagName}-${Math.round(rect.top)}-${Math.round(rect.left)}-${Date.now()}`
  return id
}
let toolbarInjected = false

// React-grab-like features state
let selectedElements: HTMLElement[] = []
let componentLabel: HTMLDivElement | null = null
let isDragSelecting = false
let dragStartX = 0
let dragStartY = 0
let dragSelectionBox: HTMLDivElement | null = null
let currentTreePosition: HTMLElement | null = null
let hierarchyPathDisplay: HTMLDivElement | null = null

// Crosshair lines state
let crosshairVertical: HTMLDivElement | null = null
let crosshairHorizontal: HTMLDivElement | null = null

// Selection highlight element
let selectionHighlight: HTMLDivElement | null = null

// Multi-selection highlight elements storage
let multiSelectionHighlights: HTMLDivElement[] = []

// Selection count badge element
let selectionCountBadge: HTMLDivElement | null = null

// Scroll/resize handler reference for cleanup
let scrollResizeHandler: (() => void) | null = null

// Export panel element
let exportPanel: HTMLDivElement | null = null

// Debug logging helper
function log(...args: unknown[]) {
  if (config.debug) {
    console.log('[React Grab]', ...args)
  }
}

/**
 * Get the React component name for an element (immediate component, not full hierarchy)
 */
function getComponentName(element: HTMLElement): string | null {
  const fiberKey = Object.keys(element).find((key) => key.startsWith('__reactFiber$'))
  if (fiberKey) {
    const fiber = (element as unknown as Record<string, unknown>)[fiberKey] as {
      type?: { name?: string; displayName?: string } | string
      return?: unknown
    }
    if (fiber?.type) {
      const name =
        typeof fiber.type === 'string'
          ? fiber.type
          : fiber.type.displayName || fiber.type.name
      if (name) return name
    }
    // Try to get from parent fiber if this is a DOM element
    let current = fiber?.return as { type?: { name?: string; displayName?: string } | string; return?: unknown } | null
    while (current) {
      if (current.type && typeof current.type !== 'string') {
        const name = current.type.displayName || current.type.name
        if (name) return name
      }
      current = current.return as typeof current | null
    }
  }
  // Fallback to tag name
  return element.tagName.toLowerCase()
}

/**
 * Get full component tree path from root to element
 */
function getComponentTreePath(element: HTMLElement): Array<{ name: string; element: HTMLElement }> {
  const path: Array<{ name: string; element: HTMLElement }> = []
  let current: HTMLElement | null = element

  while (current && current !== document.body) {
    const name = getComponentName(current)
    if (name) {
      path.unshift({ name, element: current })
    }
    current = current.parentElement
  }

  return path
}

/**
 * Get parent React component element
 */
function getParentComponent(element: HTMLElement): HTMLElement | null {
  let current = element.parentElement
  while (current && current !== document.body) {
    const name = getComponentName(current)
    if (name && name !== element.tagName.toLowerCase()) {
      return current
    }
    current = current.parentElement
  }
  return null
}

/**
 * Get first child React component element
 */
function getFirstChildComponent(element: HTMLElement): HTMLElement | null {
  const children = Array.from(element.querySelectorAll('*')) as HTMLElement[]
  for (const child of children) {
    const name = getComponentName(child)
    if (name && name !== child.tagName.toLowerCase()) {
      return child
    }
  }
  // Fallback to first element child
  return element.firstElementChild as HTMLElement | null
}

/**
 * Extract component hierarchy from a DOM element
 */
function getComponentHierarchy(element: HTMLElement): string[] {
  const hierarchy: string[] = []
  let current: HTMLElement | null = element

  while (current && current !== document.body) {
    const fiberKey = Object.keys(current).find((key) => key.startsWith('__reactFiber$'))
    if (fiberKey) {
      const fiber = (current as unknown as Record<string, unknown>)[fiberKey] as {
        type?: { name?: string; displayName?: string } | string
        _debugSource?: { fileName: string }
      }
      if (fiber?.type) {
        const name =
          typeof fiber.type === 'string'
            ? fiber.type
            : fiber.type.displayName || fiber.type.name
        if (name && !hierarchy.includes(name)) {
          hierarchy.unshift(name)
        }
      }
    }
    current = current.parentElement
  }

  return hierarchy
}

/**
 * Get source file info from React fiber
 */
function getSourceInfo(element: HTMLElement): { filePath: string | null; lineNumber?: number } {
  let current: HTMLElement | null = element

  while (current && current !== document.body) {
    const fiberKey = Object.keys(current).find((key) => key.startsWith('__reactFiber$'))
    if (fiberKey) {
      const fiber = (current as unknown as Record<string, unknown>)[fiberKey] as {
        _debugSource?: {
          fileName: string
          lineNumber: number
          columnNumber: number
        }
      }
      if (fiber?._debugSource) {
        return {
          filePath: fiber._debugSource.fileName,
          lineNumber: fiber._debugSource.lineNumber,
        }
      }
    }
    current = current.parentElement
  }

  return { filePath: null }
}

/**
 * Get a clean HTML snippet of the element (limited depth)
 */
function getHtmlSnippet(element: HTMLElement, maxDepth: number = 2): string {
  const clone = element.cloneNode(true) as HTMLElement

  function trimDepth(el: Element, depth: number) {
    if (depth >= maxDepth) {
      while (el.firstChild) {
        el.removeChild(el.firstChild)
      }
      if (el.children.length === 0 && el.textContent) {
        el.textContent = '...'
      }
      return
    }
    Array.from(el.children).forEach((child) => trimDepth(child, depth + 1))
  }

  trimDepth(clone, 0)

  let html = clone.outerHTML
  if (html.length > 500) {
    html = html.substring(0, 500) + '...'
  }

  return html
}

/**
 * Get the direct text content of an element (not including children's text)
 */
function getDirectTextContent(element: HTMLElement): string {
  let text = ''
  for (const node of element.childNodes) {
    if (node.nodeType === Node.TEXT_NODE) {
      text += node.textContent || ''
    }
  }
  return text.trim()
}

/**
 * Get meaningful text content from an element (truncated)
 */
function getMeaningfulText(element: HTMLElement, maxLength: number = 100): string {
  const directText = getDirectTextContent(element)
  if (directText) {
    return directText.length > maxLength ? directText.slice(0, maxLength) + '...' : directText
  }
  // Fallback to full text content if no direct text
  const fullText = (element.textContent || '').trim()
  return fullText.length > maxLength ? fullText.slice(0, maxLength) + '...' : fullText
}

/**
 * Get sibling position information for disambiguation
 */
function getSiblingPosition(element: HTMLElement): { index: number; total: number; siblingTexts?: string[] } | undefined {
  const parent = element.parentElement
  if (!parent) return undefined

  // Get all siblings with the same tag name (likely same component type)
  const siblings = Array.from(parent.children).filter(
    child => child.tagName === element.tagName
  ) as HTMLElement[]

  if (siblings.length <= 1) return undefined

  const index = siblings.indexOf(element)

  // Get text hints from siblings to help Claude understand position
  const siblingTexts = siblings.map((sib, i) => {
    const text = getMeaningfulText(sib, 30)
    return i === index ? `[SELECTED: ${text || sib.tagName}]` : (text || sib.tagName.toLowerCase())
  })

  return {
    index: index + 1, // 1-based for human readability
    total: siblings.length,
    siblingTexts,
  }
}

/**
 * Get parent context for better element identification
 */
function getParentContext(element: HTMLElement): { tagName: string; textContent?: string; htmlSnippet?: string } | undefined {
  // Find a meaningful parent container (not just a wrapper div)
  let parent = element.parentElement
  let depth = 0
  const maxDepth = 5

  while (parent && depth < maxDepth) {
    const parentText = getMeaningfulText(parent, 150)
    // Look for a parent with meaningful text content that's different from just the element's text
    if (parentText && parentText !== getMeaningfulText(element, 150) && parentText.length > 5) {
      return {
        tagName: parent.tagName.toLowerCase(),
        textContent: parentText,
        htmlSnippet: getHtmlSnippet(parent, 1), // Shallow snippet
      }
    }
    parent = parent.parentElement
    depth++
  }

  // Fallback to immediate parent
  const immediateParent = element.parentElement
  if (immediateParent) {
    return {
      tagName: immediateParent.tagName.toLowerCase(),
      textContent: getMeaningfulText(immediateParent, 150),
    }
  }

  return undefined
}

/**
 * Extract unique identifiers from an element
 */
function getUniqueIdentifiers(element: HTMLElement): ElementContext['uniqueIdentifiers'] {
  const identifiers: ElementContext['uniqueIdentifiers'] = {}

  if (element.id) {
    identifiers.id = element.id
  }

  if (element.dataset.testid) {
    identifiers.dataTestId = element.dataset.testid
  }

  // Collect all data-* attributes
  const dataAttrs: Record<string, string> = {}
  for (const attr of element.attributes) {
    if (attr.name.startsWith('data-') && attr.name !== 'data-testid') {
      dataAttrs[attr.name] = attr.value
    }
  }
  if (Object.keys(dataAttrs).length > 0) {
    identifiers.dataAttributes = dataAttrs
  }

  if (element.className && typeof element.className === 'string') {
    identifiers.className = element.className
  }

  // Try to get React key from fiber
  const fiberKey = Object.keys(element).find((key) => key.startsWith('__reactFiber$'))
  if (fiberKey) {
    const fiber = (element as unknown as Record<string, unknown>)[fiberKey] as {
      key?: string | number
    }
    if (fiber?.key != null) {
      identifiers.key = String(fiber.key)
    }
  }

  return Object.keys(identifiers).length > 0 ? identifiers : undefined
}

/**
 * Extract element context from a DOM element
 */
function extractElementContext(element: HTMLElement): ElementContext {
  const rect = element.getBoundingClientRect()
  const sourceInfo = getSourceInfo(element)

  return {
    filePath: sourceInfo.filePath,
    componentHierarchy: getComponentHierarchy(element),
    htmlSnippet: getHtmlSnippet(element),
    lineNumber: sourceInfo.lineNumber,
    rect: {
      top: rect.top + window.scrollY,
      left: rect.left + window.scrollX,
      width: rect.width,
      height: rect.height,
    },
    // Enhanced identification
    textContent: getMeaningfulText(element),
    siblingPosition: getSiblingPosition(element),
    parentContext: getParentContext(element),
    uniqueIdentifiers: getUniqueIdentifiers(element),
  }
}

/**
 * Inject all styles for the Cleo-inspired UI
 */
function injectStyles() {
  const styleId = 'react-grab-styles'
  if (document.getElementById(styleId)) return

  const style = document.createElement('style')
  style.id = styleId
  style.textContent = REACT_GRAB_STYLES
  document.head.appendChild(style)
}

// Variables for hoisted functions (defined later in file)
let exitSelectionMode: () => void
let closeAllPanels: () => void
let clearAllSelections: () => void
let enterSelectionMode: () => void
let handleCrosshairMove: (event: MouseEvent) => void
let handleSelectionHover: (event: MouseEvent) => void
let handleSelectionHoverOut: (event: MouseEvent) => void
let handleSelectionClick: (event: MouseEvent) => void
let handleSelectionRightClick: (event: MouseEvent) => void
let handleDragSelectionStart: (event: MouseEvent) => void
let handleDragSelectionMove: (event: MouseEvent) => void
let handleDragSelectionEnd: (event: MouseEvent) => void
let handleExpandedSelectionHover: (event: MouseEvent) => void
let handleExpandedSelectionClick: (event: MouseEvent) => void
let handleExpandedSelectionRightClick: (event: MouseEvent) => void

/**
 * Create the toolbar button (single cursor icon button)
 */
function createToolbarButton(): HTMLButtonElement {
  const btn = document.createElement('button')
  btn.className = 'react-grab-toolbar-btn'
  btn.setAttribute('aria-label', 'React Grab - AI Element Editor')
  btn.setAttribute('title', 'React Grab - Select element for AI editing (Cmd+Shift+Z)')

  btn.innerHTML = `
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M4 4l16 8.5L12.5 14l-1.5 6.5L4 4z"/>
    </svg>
  `

  btn.addEventListener('click', toggleSelectionMode)
  return btn
}

/**
 * Create the toolbar (single button)
 */
function createToolbar(): HTMLDivElement {
  const toolbar = document.createElement('div')
  toolbar.className = 'react-grab-toolbar'
  toolbar.setAttribute('role', 'toolbar')
  toolbar.setAttribute('aria-label', 'React Grab element selection toolbar')

  toolbarButton = createToolbarButton()
  toolbar.appendChild(toolbarButton)

  document.body.appendChild(toolbar)
  return toolbar
}

/**
 * Initialize the toolbar (only if React is detected)
 */
function initializeToolbar() {
  if (toolbarInjected) return

  // Only show toolbar if React is detected
  if (!isReactApp()) {
    log('React not detected, toolbar will not be shown')
    return
  }

  toolbarContainer = createToolbar()
  toolbarInjected = true
  log('React detected, toolbar initialized')
}

/**
 * Create an overlay container for a prompt panel with a unique ID
 */
function createOverlayContainer(panelId: string): HTMLDivElement {
  const container = document.createElement('div')
  container.id = `react-grab-overlay-${panelId}`
  container.className = 'react-grab-overlay-container'
  container.dataset.panelId = panelId
  container.style.display = 'none'
  document.body.appendChild(container)
  return container
}

/**
 * Get or create an overlay container for a panel
 */
function getOrCreateOverlayContainer(panelId: string): HTMLDivElement {
  let container = overlayContainers.get(panelId)
  if (!container) {
    container = createOverlayContainer(panelId)
    overlayContainers.set(panelId, container)
  }
  return container
}

/**
 * Remove a specific panel by ID
 */
function removePanelById(panelId: string) {
  const container = overlayContainers.get(panelId)
  if (container) {
    container.remove()
    overlayContainers.delete(panelId)
    panelContexts.delete(panelId)
  }
}

/**
 * Toggle selection mode on/off
 */
function toggleSelectionMode() {
  if (isSelectionModeActive) {
    exitSelectionMode()
    closeAllPanels()
    clearAllSelections()
  } else {
    enterSelectionMode()
  }
}

/**
 * Create crosshair lines that follow the cursor
 */
function createCrosshairs() {
  if (!crosshairVertical) {
    crosshairVertical = document.createElement('div')
    crosshairVertical.className = 'react-grab-crosshair-v'
    document.body.appendChild(crosshairVertical)
  }

  if (!crosshairHorizontal) {
    crosshairHorizontal = document.createElement('div')
    crosshairHorizontal.className = 'react-grab-crosshair-h'
    document.body.appendChild(crosshairHorizontal)
  }
}

/**
 * Update crosshair position based on mouse coordinates
 */
function updateCrosshairPosition(x: number, y: number) {
  if (crosshairVertical) {
    crosshairVertical.style.left = `${x}px`
  }
  if (crosshairHorizontal) {
    crosshairHorizontal.style.top = `${y}px`
  }
}

/**
 * Remove/hide crosshair lines
 */
function removeCrosshairs() {
  if (crosshairVertical) {
    crosshairVertical.remove()
    crosshairVertical = null
  }
  if (crosshairHorizontal) {
    crosshairHorizontal.remove()
    crosshairHorizontal = null
  }
}

/**
 * Handle mouse movement for crosshair updates
 */
handleCrosshairMove = function(event: MouseEvent) {
  updateCrosshairPosition(event.clientX, event.clientY)
}

/**
 * Show a toast notification
 */
function showToast(message: string, duration: number = 3000, cursorPos?: { x: number; y: number }) {
  const existingToast = document.querySelector('.react-grab-toast')
  if (existingToast) {
    existingToast.remove()
  }

  const toast = document.createElement('div')
  toast.className = 'react-grab-toast'

  if (cursorPos) {
    toast.classList.add('cursor-toast')
    const offsetX = 10
    const offsetY = 15
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    const estimatedWidth = 120
    const estimatedHeight = 30

    let left = cursorPos.x + offsetX
    let top = cursorPos.y + offsetY

    if (left + estimatedWidth > viewportWidth - 10) {
      left = cursorPos.x - estimatedWidth - offsetX
    }
    if (top + estimatedHeight > viewportHeight - 10) {
      top = cursorPos.y - estimatedHeight - offsetY
    }

    left = Math.max(10, left)
    top = Math.max(10, top)

    toast.style.left = `${left}px`
    toast.style.top = `${top}px`
  }

  toast.innerHTML = message
  document.body.appendChild(toast)

  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transition = 'opacity 0.15s ease-out'
    setTimeout(() => toast.remove(), 150)
  }, duration)
}

/**
 * Enter selection mode
 */
enterSelectionMode = function() {
  isSelectionModeActive = true

  if (toolbarButton) {
    toolbarButton.classList.add('active')
  }

  document.documentElement.classList.add('react-grab-selection-active')

  createCrosshairs()
  document.addEventListener('mousemove', handleCrosshairMove, true)

  document.addEventListener('mouseover', handleSelectionHover, true)
  document.addEventListener('mouseout', handleSelectionHoverOut, true)
  document.addEventListener('click', handleSelectionClick, true)
  document.addEventListener('contextmenu', handleSelectionRightClick, true)

  document.addEventListener('mousedown', handleDragSelectionStart, true)
  document.addEventListener('mousemove', handleDragSelectionMove, true)
  document.addEventListener('mouseup', handleDragSelectionEnd, true)

  // Setup scroll/resize listeners to keep UI attached to elements
  setupScrollResizeListeners()

  showToast('Click to copy, right-click for AI prompt')
  log('Selection mode activated')
}

/**
 * Exit selection mode
 */
exitSelectionMode = function() {
  isSelectionModeActive = false

  if (toolbarButton) {
    toolbarButton.classList.remove('active')
  }

  const expandedBtn = document.getElementById('react-grab-expanded-select-mode')
  expandedBtn?.classList.remove('active')

  document.documentElement.classList.remove('react-grab-selection-active')

  removeCrosshairs()
  document.removeEventListener('mousemove', handleCrosshairMove, true)

  removeSelectionHighlight()
  hideComponentLabel()
  hideHierarchyPath()
  removeDragSelectionBox()

  document.removeEventListener('mouseover', handleSelectionHover, true)
  document.removeEventListener('mouseout', handleSelectionHoverOut, true)
  document.removeEventListener('click', handleSelectionClick, true)
  document.removeEventListener('contextmenu', handleSelectionRightClick, true)

  document.removeEventListener('mouseover', handleExpandedSelectionHover, true)
  document.removeEventListener('click', handleExpandedSelectionClick, true)
  document.removeEventListener('contextmenu', handleExpandedSelectionRightClick, true)

  document.removeEventListener('mousedown', handleDragSelectionStart, true)
  document.removeEventListener('mousemove', handleDragSelectionMove, true)
  document.removeEventListener('mouseup', handleDragSelectionEnd, true)

  // Remove scroll/resize listeners
  removeScrollResizeListeners()

  hoveredElement = null
  currentTreePosition = null
  isDragSelecting = false

  log('Selection mode deactivated')
}

function showSelectionHighlight(element: HTMLElement) {
  if (!selectionHighlight) {
    selectionHighlight = document.createElement('div')
    selectionHighlight.className = 'react-grab-selection-highlight'
    document.body.appendChild(selectionHighlight)
  }

  const rect = element.getBoundingClientRect()
  selectionHighlight.style.top = `${rect.top}px`
  selectionHighlight.style.left = `${rect.left}px`
  selectionHighlight.style.width = `${rect.width}px`
  selectionHighlight.style.height = `${rect.height}px`
  selectionHighlight.style.display = 'block'
}

function removeSelectionHighlight() {
  if (selectionHighlight) {
    selectionHighlight.style.display = 'none'
  }
}

/**
 * Update highlight position for an element (used during scroll/resize)
 */
function updateHighlightPosition(element: HTMLElement, highlightEl: HTMLDivElement) {
  const rect = element.getBoundingClientRect()
  highlightEl.style.top = `${rect.top}px`
  highlightEl.style.left = `${rect.left}px`
  highlightEl.style.width = `${rect.width}px`
  highlightEl.style.height = `${rect.height}px`
}

/**
 * Update all highlight positions on scroll/resize
 */
function updateAllHighlightPositions() {
  // Update main selection highlight
  if (selectionHighlight && selectionHighlight.style.display !== 'none') {
    const targetElement = currentTreePosition || hoveredElement || currentTargetElement
    if (targetElement) {
      updateHighlightPosition(targetElement, selectionHighlight)
    }
  }

  // Update multi-selection highlights
  if (multiSelectionHighlights.length > 0 && selectedElements.length === multiSelectionHighlights.length) {
    selectedElements.forEach((element, index) => {
      const highlight = multiSelectionHighlights[index]
      if (highlight) {
        updateHighlightPosition(element, highlight)
      }
    })
  }

  // Update component label position
  if (componentLabel && componentLabel.style.display !== 'none') {
    const targetElement = currentTreePosition || hoveredElement || currentTargetElement
    if (targetElement) {
      const rect = targetElement.getBoundingClientRect()
      componentLabel.style.left = `${rect.left}px`
      componentLabel.style.top = `${rect.top}px`
    }
  }
}

/**
 * Update a specific panel's position based on its attached element
 */
function updatePanelPosition(panelId: string) {
  const panelData = panelContexts.get(panelId)
  const container = overlayContainers.get(panelId)
  if (!panelData?.element || !container) return

  const rect = panelData.element.getBoundingClientRect()
  const viewportHeight = window.innerHeight
  const viewportWidth = window.innerWidth
  const overlayHeight = 180
  const overlayWidth = 380

  // Calculate new position
  let top = rect.bottom + 12
  let left = rect.left

  // If panel would go below viewport, position it above the element
  if (top + overlayHeight > viewportHeight) {
    top = rect.top - overlayHeight - 12
  }

  // Keep within horizontal bounds
  if (left + overlayWidth > viewportWidth) {
    left = viewportWidth - overlayWidth - 16
  }
  if (left < 16) {
    left = 16
  }
  if (top < 16) {
    top = 16
  }

  container.style.top = `${top}px`
  container.style.left = `${left}px`
}

/**
 * Update all panel positions on scroll/resize
 */
function updateAllPanelPositions() {
  overlayContainers.forEach((container, panelId) => {
    if (container.style.display !== 'none') {
      updatePanelPosition(panelId)
    }
  })
}

/**
 * Handle scroll and resize events to keep UI attached to elements
 */
function handleScrollResize() {
  updateAllHighlightPositions()
  updateAllPanelPositions()
}

/**
 * Setup scroll and resize listeners
 */
function setupScrollResizeListeners() {
  if (scrollResizeHandler) return // Already set up

  scrollResizeHandler = handleScrollResize

  // Use capture phase to catch scroll events on all scrollable containers
  window.addEventListener('scroll', scrollResizeHandler, true)
  window.addEventListener('resize', scrollResizeHandler)

  log('Scroll/resize listeners attached')
}

/**
 * Remove scroll and resize listeners
 */
function removeScrollResizeListeners() {
  if (scrollResizeHandler) {
    window.removeEventListener('scroll', scrollResizeHandler, true)
    window.removeEventListener('resize', scrollResizeHandler)
    scrollResizeHandler = null
    log('Scroll/resize listeners removed')
  }
}

function showComponentLabel(element: HTMLElement) {
  const componentName = getComponentName(element)
  if (!componentName) return

  if (!componentLabel) {
    componentLabel = document.createElement('div')
    componentLabel.className = 'react-grab-component-label'
    document.body.appendChild(componentLabel)
  }

  const rect = element.getBoundingClientRect()
  componentLabel.textContent = componentName
  componentLabel.style.left = `${rect.left}px`
  componentLabel.style.top = `${rect.top}px`
  componentLabel.style.display = 'block'
}

function hideComponentLabel() {
  if (componentLabel) {
    componentLabel.remove()
    componentLabel = null
  }
}

function showMultiSelectionHighlights() {
  multiSelectionHighlights.forEach(h => h.remove())
  multiSelectionHighlights = []

  selectedElements.forEach(element => {
    const highlight = document.createElement('div')
    highlight.className = 'react-grab-multi-selection-highlight'
    const rect = element.getBoundingClientRect()
    highlight.style.top = `${rect.top}px`
    highlight.style.left = `${rect.left}px`
    highlight.style.width = `${rect.width}px`
    highlight.style.height = `${rect.height}px`
    document.body.appendChild(highlight)
    multiSelectionHighlights.push(highlight)
  })

  updateSelectionCountBadge()
}

function removeMultiSelectionHighlights() {
  multiSelectionHighlights.forEach(h => h.remove())
  multiSelectionHighlights = []
  removeSelectionCountBadge()
}

function updateSelectionCountBadge() {
  if (selectedElements.length <= 1) {
    removeSelectionCountBadge()
    return
  }

  if (!selectionCountBadge) {
    selectionCountBadge = document.createElement('div')
    selectionCountBadge.className = 'react-grab-selection-count'
    document.body.appendChild(selectionCountBadge)
  }

  selectionCountBadge.textContent = `${selectedElements.length} selected`
  selectionCountBadge.style.display = 'block'
}

function removeSelectionCountBadge() {
  if (selectionCountBadge) {
    selectionCountBadge.style.display = 'none'
  }
}

function addToSelection(element: HTMLElement) {
  if (!selectedElements.includes(element)) {
    selectedElements.push(element)
    showMultiSelectionHighlights()
  }
}

function removeFromSelection(element: HTMLElement) {
  const index = selectedElements.indexOf(element)
  if (index > -1) {
    selectedElements.splice(index, 1)
    showMultiSelectionHighlights()
  }
}

function toggleSelection(element: HTMLElement) {
  if (selectedElements.includes(element)) {
    removeFromSelection(element)
  } else {
    addToSelection(element)
  }
}

clearAllSelections = function() {
  selectedElements = []
  removeMultiSelectionHighlights()
}

function removeDragSelectionBox() {
  if (dragSelectionBox) {
    dragSelectionBox.remove()
    dragSelectionBox = null
  }
}

function showHierarchyPath(element: HTMLElement) {
  const path = getComponentTreePath(element)

  if (!hierarchyPathDisplay) {
    hierarchyPathDisplay = document.createElement('div')
    hierarchyPathDisplay.className = 'react-grab-hierarchy-path'
    document.body.appendChild(hierarchyPathDisplay)
  }

  const displayPath = path.slice(-5)
  const pathHtml = displayPath.map((item, index) => {
    const isCurrent = item.element === element
    return `<span class="path-item ${isCurrent ? 'current' : ''}">${item.name}</span>${
      index < displayPath.length - 1 ? '<span class="path-separator">></span>' : ''
    }`
  }).join('')

  hierarchyPathDisplay.innerHTML = `${pathHtml}<span class="nav-hint">Arrow keys to navigate</span>`
  hierarchyPathDisplay.style.display = 'flex'
}

function hideHierarchyPath() {
  if (hierarchyPathDisplay) {
    hierarchyPathDisplay.style.display = 'none'
  }
}

function navigateToParent() {
  const currentElement = currentTreePosition || hoveredElement || currentTargetElement
  if (!currentElement) return

  const parent = getParentComponent(currentElement)
  if (parent) {
    currentTreePosition = parent
    showSelectionHighlight(parent)
    showComponentLabel(parent)
    showHierarchyPath(parent)
  } else {
    showToast('Already at root component')
  }
}

function navigateToChild() {
  const currentElement = currentTreePosition || hoveredElement || currentTargetElement
  if (!currentElement) return

  const child = getFirstChildComponent(currentElement)
  if (child) {
    currentTreePosition = child
    showSelectionHighlight(child)
    showComponentLabel(child)
    showHierarchyPath(child)
  } else {
    showToast('No child components')
  }
}

function navigateToNextSibling() {
  const currentElement = currentTreePosition || hoveredElement || currentTargetElement
  if (!currentElement || !currentElement.parentElement) return

  let sibling = currentElement.nextElementSibling as HTMLElement | null
  while (sibling) {
    const name = getComponentName(sibling)
    if (name && name !== sibling.tagName.toLowerCase()) {
      currentTreePosition = sibling
      showSelectionHighlight(sibling)
      showComponentLabel(sibling)
      showHierarchyPath(sibling)
      return
    }
    sibling = sibling.nextElementSibling as HTMLElement | null
  }

  if (currentElement.nextElementSibling) {
    currentTreePosition = currentElement.nextElementSibling as HTMLElement
    showSelectionHighlight(currentTreePosition)
    showComponentLabel(currentTreePosition)
    showHierarchyPath(currentTreePosition)
  } else {
    showToast('No next sibling')
  }
}

function navigateToPrevSibling() {
  const currentElement = currentTreePosition || hoveredElement || currentTargetElement
  if (!currentElement || !currentElement.parentElement) return

  let sibling = currentElement.previousElementSibling as HTMLElement | null
  while (sibling) {
    const name = getComponentName(sibling)
    if (name && name !== sibling.tagName.toLowerCase()) {
      currentTreePosition = sibling
      showSelectionHighlight(sibling)
      showComponentLabel(sibling)
      showHierarchyPath(sibling)
      return
    }
    sibling = sibling.previousElementSibling as HTMLElement | null
  }

  if (currentElement.previousElementSibling) {
    currentTreePosition = currentElement.previousElementSibling as HTMLElement
    showSelectionHighlight(currentTreePosition)
    showComponentLabel(currentTreePosition)
    showHierarchyPath(currentTreePosition)
  } else {
    showToast('No previous sibling')
  }
}

function selectTreePosition() {
  if (currentTreePosition) {
    clearAllSelections()
    selectElement(currentTreePosition)
    hideHierarchyPath()
    currentTreePosition = null
  }
}

function generateExportData(element: HTMLElement): object {
  const context = extractElementContext(element)
  const componentName = getComponentName(element)
  const treePath = getComponentTreePath(element)

  const fiberKey = Object.keys(element).find((key) => key.startsWith('__reactFiber$'))
  let props: Record<string, unknown> = {}

  if (fiberKey) {
    const fiber = (element as unknown as Record<string, unknown>)[fiberKey] as {
      memoizedProps?: Record<string, unknown>
      pendingProps?: Record<string, unknown>
    }

    if (fiber?.memoizedProps) {
      props = Object.entries(fiber.memoizedProps).reduce((acc, [key, value]) => {
        if (key !== 'children' && typeof value !== 'function') {
          acc[key] = value
        }
        return acc
      }, {} as Record<string, unknown>)
    }
  }

  return {
    componentName,
    componentPath: treePath.map(p => p.name),
    filePath: context.filePath,
    lineNumber: context.lineNumber,
    props,
    htmlSnippet: context.htmlSnippet,
    boundingRect: context.rect,
    tagName: element.tagName.toLowerCase(),
    className: element.className || null,
    id: element.id || null,
    exportedAt: new Date().toISOString()
  }
}

function generateMultiExportData(): object {
  const elements = selectedElements.length > 0 ? selectedElements : (currentTargetElement ? [currentTargetElement] : [])

  if (elements.length === 0) {
    return { error: 'No elements selected' }
  }

  if (elements.length === 1) {
    return generateExportData(elements[0])
  }

  return {
    elementCount: elements.length,
    elements: elements.map(el => generateExportData(el)),
    exportedAt: new Date().toISOString()
  }
}

async function copyExportToClipboard() {
  const data = generateMultiExportData()
  const jsonString = JSON.stringify(data, null, 2)

  try {
    await navigator.clipboard.writeText(jsonString)
    showToast('Copied to clipboard!')
    hideExportPanel()
  } catch (err) {
    console.error('[React Grab] Failed to copy:', err)
    showToast('Failed to copy to clipboard')
  }
}

function downloadExportAsJson() {
  const data = generateMultiExportData()
  const jsonString = JSON.stringify(data, null, 2)

  const blob = new Blob([jsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = `react-grab-export-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)

  showToast('Downloaded JSON file')
  hideExportPanel()
}

function showExportPanel() {
  const elements = selectedElements.length > 0 ? selectedElements : (currentTargetElement ? [currentTargetElement] : [])

  if (elements.length === 0) {
    showToast('Select an element first')
    return
  }

  if (!exportPanel) {
    exportPanel = document.createElement('div')
    exportPanel.className = 'react-grab-export-panel'
    document.body.appendChild(exportPanel)
  }

  const elementCount = elements.length
  const elementText = elementCount === 1 ? '1 element' : `${elementCount} elements`

  exportPanel.innerHTML = `
    <div class="react-grab-export-panel-header">
      <span class="react-grab-export-panel-title">Export ${elementText}</span>
      <button class="react-grab-export-close" id="react-grab-export-close">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
    <button class="react-grab-export-btn" id="react-grab-export-copy">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      Copy JSON to clipboard
    </button>
    <button class="react-grab-export-btn" id="react-grab-export-download">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      Download as JSON file
    </button>
  `

  exportPanel.style.display = 'block'

  document.getElementById('react-grab-export-close')?.addEventListener('click', hideExportPanel)
  document.getElementById('react-grab-export-copy')?.addEventListener('click', copyExportToClipboard)
  document.getElementById('react-grab-export-download')?.addEventListener('click', downloadExportAsJson)
}

function hideExportPanel() {
  if (exportPanel) {
    exportPanel.style.display = 'none'
  }
}

handleSelectionHover = function(event: MouseEvent) {
  if (!isSelectionModeActive) return

  const target = event.target as HTMLElement

  // Ignore all React Grab UI elements including open panels
  if (
    target.closest('#react-grab-overlay') ||
    target.closest('.react-grab-overlay-container') ||
    target.closest('.react-grab-prompt-overlay') ||
    target.closest('.react-grab-prompt') ||
    target.closest('.react-grab-toolbar') ||
    target.closest('.react-grab-toolbar-btn') ||
    target.closest('.react-grab-selection-highlight') ||
    target.closest('.react-grab-component-label') ||
    target.closest('.react-grab-multi-selection-highlight') ||
    target.closest('.react-grab-drag-selection-box') ||
    target.closest('.react-grab-hierarchy-path') ||
    target.closest('.react-grab-export-panel') ||
    target.closest('.react-grab-expanded')
  ) {
    return
  }

  hoveredElement = target
  showSelectionHighlight(target)
  showComponentLabel(target)
}

handleSelectionHoverOut = function(event: MouseEvent) {
  if (!isSelectionModeActive) return

  const relatedTarget = event.relatedTarget as HTMLElement | null
  if (
    relatedTarget &&
    (relatedTarget.closest('#react-grab-overlay') ||
      relatedTarget.closest('.react-grab-toolbar') ||
      relatedTarget.closest('.react-grab-toolbar-btn') ||
      relatedTarget.closest('.react-grab-component-label'))
  ) {
    return
  }

  hideComponentLabel()
}

async function copyElementToClipboard(element: HTMLElement, cursorPos?: { x: number; y: number }) {
  currentTargetElement = element
  currentElementContext = extractElementContext(element)

  const data = generateExportData(element)
  const jsonString = JSON.stringify(data, null, 2)

  try {
    await navigator.clipboard.writeText(jsonString)
    showToast('Copied to clipboard', 1500, cursorPos)
  } catch (err) {
    console.error('[React Grab] Failed to copy:', err)
    showToast('Failed to copy to clipboard', 3000, cursorPos)
  }
}

handleSelectionClick = function(event: MouseEvent) {
  if (!isSelectionModeActive) return

  const target = event.target as HTMLElement

  // Ignore all React Grab UI elements including open panels
  // Allow clicks on panels to work normally (for typing in text areas, clicking buttons)
  if (
    target.closest('#react-grab-overlay') ||
    target.closest('.react-grab-overlay-container') ||
    target.closest('.react-grab-prompt-overlay') ||
    target.closest('.react-grab-prompt') ||
    target.closest('.react-grab-toolbar') ||
    target.closest('.react-grab-toolbar-btn') ||
    target.closest('.react-grab-selection-highlight') ||
    target.closest('.react-grab-component-label') ||
    target.closest('.react-grab-multi-selection-highlight') ||
    target.closest('.react-grab-hierarchy-path') ||
    target.closest('.react-grab-export-panel') ||
    target.closest('.react-grab-expanded')
  ) {
    return
  }

  event.preventDefault()
  event.stopPropagation()

  if (event.shiftKey) {
    toggleSelection(target)
    if (selectedElements.length > 0) {
      currentTargetElement = selectedElements[selectedElements.length - 1]
      currentElementContext = extractElementContext(currentTargetElement)
    }
    return
  }

  copyElementToClipboard(target, { x: event.clientX, y: event.clientY })
}

handleSelectionRightClick = function(event: MouseEvent) {
  if (!isSelectionModeActive) return

  const target = event.target as HTMLElement

  // Allow right-click on panels to work normally (for context menus, etc.)
  // but don't trigger element selection
  if (
    target.closest('#react-grab-overlay') ||
    target.closest('.react-grab-overlay-container') ||
    target.closest('.react-grab-prompt-overlay') ||
    target.closest('.react-grab-prompt') ||
    target.closest('.react-grab-toolbar') ||
    target.closest('.react-grab-toolbar-btn') ||
    target.closest('.react-grab-selection-highlight') ||
    target.closest('.react-grab-component-label') ||
    target.closest('.react-grab-multi-selection-highlight') ||
    target.closest('.react-grab-hierarchy-path') ||
    target.closest('.react-grab-export-panel')
  ) {
    return
  }

  event.preventDefault()
  event.stopPropagation()

  // Keep selection mode active when opening panels
  // This allows multi-panel selection workflow:
  // - Right-click element 1 -> panel 1 opens, selection mode stays active
  // - Right-click element 2 -> panel 2 opens, selection mode stays active
  // - etc.

  if (selectedElements.length > 1) {
    currentTargetElement = selectedElements[selectedElements.length - 1]
    currentElementContext = extractElementContext(currentTargetElement)
    renderPromptOverlay(currentElementContext)
  } else if (selectedElements.length === 1) {
    selectElement(selectedElements[0])
  } else {
    selectElement(target)
  }
}

handleDragSelectionStart = function(event: MouseEvent) {
  if (!isSelectionModeActive) return

  const target = event.target as HTMLElement

  // Ignore all React Grab UI elements including open panels
  if (
    target.closest('#react-grab-overlay') ||
    target.closest('.react-grab-overlay-container') ||
    target.closest('.react-grab-prompt-overlay') ||
    target.closest('.react-grab-prompt') ||
    target.closest('.react-grab-toolbar') ||
    target.closest('.react-grab-expanded') ||
    target.closest('.react-grab-component-label') ||
    target.closest('.react-grab-export-panel')
  ) {
    return
  }

  if (!event.shiftKey && event.button === 0) {
    isDragSelecting = true
    dragStartX = event.clientX
    dragStartY = event.clientY

    if (!dragSelectionBox) {
      dragSelectionBox = document.createElement('div')
      dragSelectionBox.className = 'react-grab-drag-selection-box'
      document.body.appendChild(dragSelectionBox)
    }

    dragSelectionBox.style.left = `${dragStartX}px`
    dragSelectionBox.style.top = `${dragStartY}px`
    dragSelectionBox.style.width = '0px'
    dragSelectionBox.style.height = '0px'
    dragSelectionBox.style.display = 'none'
  }
}

handleDragSelectionMove = function(event: MouseEvent) {
  if (!isDragSelecting || !dragSelectionBox) return

  const currentX = event.clientX
  const currentY = event.clientY

  const left = Math.min(dragStartX, currentX)
  const top = Math.min(dragStartY, currentY)
  const width = Math.abs(currentX - dragStartX)
  const height = Math.abs(currentY - dragStartY)

  if (width > 10 || height > 10) {
    dragSelectionBox.style.display = 'block'
    dragSelectionBox.style.left = `${left}px`
    dragSelectionBox.style.top = `${top}px`
    dragSelectionBox.style.width = `${width}px`
    dragSelectionBox.style.height = `${height}px`

    removeSelectionHighlight()
    hideComponentLabel()
  }
}

handleDragSelectionEnd = function(event: MouseEvent) {
  if (!isDragSelecting) return

  isDragSelecting = false

  if (!dragSelectionBox) return

  const boxRect = dragSelectionBox.getBoundingClientRect()

  if (dragSelectionBox.style.display === 'block' && boxRect.width > 10 && boxRect.height > 10) {
    const allElements = document.querySelectorAll('*') as NodeListOf<HTMLElement>

    if (!event.shiftKey) {
      clearAllSelections()
    }

    allElements.forEach(element => {
      // Ignore all React Grab UI elements including open panels
      if (
        element.closest('#react-grab-overlay') ||
        element.closest('.react-grab-overlay-container') ||
        element.closest('.react-grab-prompt-overlay') ||
        element.closest('.react-grab-prompt') ||
        element.closest('.react-grab-toolbar') ||
        element.closest('.react-grab-expanded') ||
        element.closest('.react-grab-component-label') ||
        element.closest('.react-grab-selection-highlight') ||
        element.closest('.react-grab-multi-selection-highlight') ||
        element.closest('.react-grab-drag-selection-box') ||
        element.closest('.react-grab-hierarchy-path') ||
        element.closest('.react-grab-export-panel')
      ) {
        return
      }

      const elemRect = element.getBoundingClientRect()

      if (
        elemRect.left >= boxRect.left &&
        elemRect.right <= boxRect.right &&
        elemRect.top >= boxRect.top &&
        elemRect.bottom <= boxRect.bottom
      ) {
        if (elemRect.width > 5 && elemRect.height > 5 && !selectedElements.includes(element)) {
          addToSelection(element)
        }
      }
    })

    if (selectedElements.length > 0) {
      currentTargetElement = selectedElements[selectedElements.length - 1]
      currentElementContext = extractElementContext(currentTargetElement)
    }
  }

  dragSelectionBox.style.display = 'none'
}

function selectElement(element: HTMLElement) {
  currentTargetElement = element
  currentElementContext = extractElementContext(element)

  showSelectionHighlight(element)

  // Keep selection mode active - don't exit when opening a panel
  // User can continue selecting more elements while panels are open
  // Selection mode only exits via:
  // - Toolbar button click
  // - Cmd+Shift+Z toggle
  // - Escape key

  renderPromptOverlay(currentElementContext)
}

/**
 * Render a prompt overlay for a specific element (supports multiple panels)
 */
function renderPromptOverlay(context: ElementContext, element?: HTMLElement) {
  // Generate a unique panel ID for this element
  const targetElement = element || currentTargetElement
  if (!targetElement) return

  const panelId = generatePanelId(targetElement)
  const overlayContainer = getOrCreateOverlayContainer(panelId)

  // Store the context for this panel
  panelContexts.set(panelId, { context, element: targetElement })

  // Ensure scroll/resize listeners are active when panels are visible
  setupScrollResizeListeners()

  const viewportHeight = window.innerHeight
  const viewportWidth = window.innerWidth
  const overlayHeight = 180
  const overlayWidth = 380

  let top = context.rect.top + context.rect.height + 12 - window.scrollY
  let left = context.rect.left - window.scrollX

  if (top + overlayHeight > viewportHeight) {
    top = context.rect.top - window.scrollY - overlayHeight - 12
  }
  if (left + overlayWidth > viewportWidth) {
    left = viewportWidth - overlayWidth - 16
  }
  if (left < 16) {
    left = 16
  }
  if (top < 16) {
    top = 16
  }

  overlayContainer.style.position = 'fixed'
  overlayContainer.style.zIndex = '999999'
  overlayContainer.style.pointerEvents = 'auto'
  overlayContainer.style.fontFamily = 'Inter, system-ui, -apple-system, sans-serif'
  overlayContainer.style.top = `${top}px`
  overlayContainer.style.left = `${left}px`
  overlayContainer.style.display = 'block'

  const hierarchy = context.componentHierarchy.slice(-3)
  const breadcrumbPath = hierarchy.length > 0
    ? hierarchy.map((h, i) => i < hierarchy.length - 1 ? `${h} <span>›</span>` : h).join(' ')
    : context.filePath
      ? context.filePath.split('/').pop() || 'Element'
      : 'Element'

  overlayContainer.innerHTML = `
    <div class="react-grab-prompt">
      <div class="react-grab-prompt-header">
        <div class="react-grab-breadcrumb-chip">
          <svg class="react-grab-breadcrumb-icon" viewBox="-11.5 -10.23174 23 20.46348">
            <circle cx="0" cy="0" r="2.05" fill="#61dafb"/>
            <g stroke="#61dafb" stroke-width="1" fill="none">
              <ellipse rx="11" ry="4.2"/>
              <ellipse rx="11" ry="4.2" transform="rotate(60)"/>
              <ellipse rx="11" ry="4.2" transform="rotate(120)"/>
            </g>
          </svg>
          <span class="react-grab-breadcrumb-path">${breadcrumbPath}</span>
          <button class="react-grab-breadcrumb-deselect" data-panel-id="${panelId}" aria-label="Close panel" title="Close panel">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="react-grab-prompt-header-actions">
          <button class="react-grab-prompt-header-btn expand-btn" data-panel-id="${panelId}" aria-label="Expand to panel" title="Expand to panel">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
            </svg>
          </button>
          <button class="react-grab-prompt-header-btn close-btn" data-panel-id="${panelId}" aria-label="Close panel" title="Close panel">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <div class="react-grab-input-wrapper">
        <textarea
          class="react-grab-input"
          data-panel-id="${panelId}"
          placeholder="Describe what to build..."
        ></textarea>
        <button class="react-grab-submit-btn" data-panel-id="${panelId}" aria-label="Send">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        </button>
      </div>

      <div class="react-grab-feedback" data-panel-id="${panelId}"></div>
    </div>
  `

  const input = overlayContainer.querySelector('.react-grab-input') as HTMLTextAreaElement
  const submitBtn = overlayContainer.querySelector('.react-grab-submit-btn') as HTMLButtonElement
  const closeBtn = overlayContainer.querySelector('.close-btn') as HTMLButtonElement
  const expandBtn = overlayContainer.querySelector('.expand-btn') as HTMLButtonElement
  const deselectBtn = overlayContainer.querySelector('.react-grab-breadcrumb-deselect') as HTMLButtonElement

  setTimeout(() => input?.focus(), 50)

  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleCompactSubmitForPanel(panelId)
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      hidePanelById(panelId)
    }
  })

  submitBtn?.addEventListener('click', () => handleCompactSubmitForPanel(panelId))
  closeBtn?.addEventListener('click', () => hidePanelById(panelId))
  expandBtn?.addEventListener('click', () => switchToExpandedForPanel(panelId))
  deselectBtn?.addEventListener('click', () => hidePanelById(panelId))
}

/**
 * Hide a specific panel by ID (for multi-panel support)
 * Does NOT exit selection mode - user can keep selecting more elements
 */
function hidePanelById(panelId: string) {
  removePanelById(panelId)

  // If no panels remain and we're not in expanded mode, clean up highlights
  // but keep selection mode active so user can select more elements
  if (overlayContainers.size === 0 && panelMode !== 'expanded') {
    removeSelectionHighlight()
    hideComponentLabel()
    currentElementContext = null
    currentTargetElement = null
    // Note: Do NOT exit selection mode here - user can still select more elements
    // But do remove scroll listeners if not in selection mode
    if (!isSelectionModeActive) {
      removeScrollResizeListeners()
    }
  }
}

/**
 * Switch to expanded mode for a specific panel
 */
function switchToExpandedForPanel(panelId: string) {
  const panelData = panelContexts.get(panelId)
  if (panelData) {
    currentElementContext = panelData.context
    currentTargetElement = panelData.element
  }
  panelMode = 'expanded'
  hideCompactOverlay()
  renderExpandedPanel()
  log('Switched to expanded panel mode')
}

/**
 * Handle submit for a specific panel
 */
async function handleCompactSubmitForPanel(panelId: string) {
  const panelData = panelContexts.get(panelId)
  if (!panelData || isSubmitting) return

  const overlayContainer = overlayContainers.get(panelId)
  if (!overlayContainer) return

  const input = overlayContainer.querySelector('.react-grab-input') as HTMLTextAreaElement
  const submitBtn = overlayContainer.querySelector('.react-grab-submit-btn') as HTMLButtonElement
  const feedback = overlayContainer.querySelector('.react-grab-feedback') as HTMLDivElement

  const prompt = input?.value?.trim()
  if (!prompt) return

  isSubmitting = true

  if (submitBtn) {
    submitBtn.disabled = true
    submitBtn.innerHTML = `
      <svg class="react-grab-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
      </svg>
    `
  }

  const elementContextPayload = {
    filePath: panelData.context.filePath,
    componentHierarchy: panelData.context.componentHierarchy,
    htmlSnippet: panelData.context.htmlSnippet,
    lineNumber: panelData.context.lineNumber,
  }

  try {
    const response = await fetch(config.apiEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt,
        elementContext: elementContextPayload,
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()

    if (feedback) {
      feedback.className = 'react-grab-feedback success'
      feedback.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        ${data.message || 'Sent to {{ORCHESTRATOR_NAME}}!'}
      `
    }

    // Close only this panel after success
    setTimeout(() => {
      hidePanelById(panelId)
    }, 1200)
  } catch (error) {
    console.error('[React Grab] Submit error:', error)

    if (feedback) {
      feedback.className = 'react-grab-feedback error'
      feedback.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        Failed to send. Try again.
      `
    }

    if (submitBtn) {
      submitBtn.disabled = false
      submitBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="5" y1="12" x2="19" y2="12"></line>
          <polyline points="12 5 19 12 12 19"></polyline>
        </svg>
      `
    }
  } finally {
    isSubmitting = false
  }
}

function handleDeselectElement() {
  selectedElements = []
  currentElementContext = null
  currentTargetElement = null

  removeSelectionHighlight()
  hideComponentLabel()
  hideHierarchyPath()

  if (!isSelectionModeActive) {
    enterSelectionMode()
  }

  hideOverlay()

  showToast('Element deselected. Click to select a new element.')
}

async function handleCompactSubmit() {
  if (isSubmitting || !currentElementContext) return

  const input = document.getElementById('react-grab-input') as HTMLTextAreaElement
  const submitBtn = document.getElementById('react-grab-submit-btn') as HTMLButtonElement
  const feedback = document.getElementById('react-grab-feedback') as HTMLDivElement

  const prompt = input?.value?.trim()
  if (!prompt) return

  isSubmitting = true
  isStreamingResponse = true
  currentStreamingContent = ''

  if (submitBtn) {
    submitBtn.disabled = true
    submitBtn.innerHTML = `
      <svg class="react-grab-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
      </svg>
    `
  }

  // Show thinking state in feedback
  if (feedback) {
    feedback.className = 'react-grab-feedback streaming'
    feedback.innerHTML = `
      <svg class="react-grab-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
      </svg>
      <span class="react-grab-streaming-text">Thinking...</span>
    `
  }

  // Add user message to conversation history (unified with expanded panel)
  conversationHistory.push({ role: 'user', content: prompt })

  // Use streaming endpoint
  await streamChatResponse(
    prompt,
    currentElementContext,
    [], // No screenshots in compact mode
    // onDelta - update feedback with streaming preview
    (text, fullText) => {
      currentStreamingContent = fullText
      if (feedback) {
        // Truncate for compact view
        const preview = fullText.length > 100 ? fullText.slice(0, 100) + '...' : fullText
        feedback.className = 'react-grab-feedback streaming has-content'
        feedback.innerHTML = `
          <span class="react-grab-streaming-text">${escapeHtml(preview)}</span>
        `
      }
    },
    // onComplete
    (fullText, sessionId) => {
      isSubmitting = false
      isStreamingResponse = false

      if (sessionId) {
        currentSessionId = sessionId
      }

      const assistantMessage = fullText || 'Request processed.'
      conversationHistory.push({ role: 'assistant', content: assistantMessage })

      if (feedback) {
        const preview = assistantMessage.length > 150 ? assistantMessage.slice(0, 150) + '...' : assistantMessage
        feedback.className = 'react-grab-feedback success'
        feedback.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>${escapeHtml(preview)}</span>
          ${assistantMessage.length > 150 ? '<button class="react-grab-expand-response">Expand</button>' : ''}
        `

        // Add expand handler if response is long
        const expandBtn = feedback.querySelector('.react-grab-expand-response')
        if (expandBtn) {
          expandBtn.addEventListener('click', (e) => {
            e.stopPropagation()
            switchToExpanded()
          })
        }
      }

      if (submitBtn) {
        submitBtn.disabled = false
        submitBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        `
      }

      // Don't auto-close - let user see the response
    },
    // onError
    (error) => {
      console.error('[React Grab] Stream error:', error)
      isSubmitting = false
      isStreamingResponse = false

      conversationHistory.push({ role: 'assistant', content: `Error: ${error}` })

      if (feedback) {
        feedback.className = 'react-grab-feedback error'
        feedback.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          Failed to send. Try again.
        `
      }

      if (submitBtn) {
        submitBtn.disabled = false
        submitBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        `
      }
    }
  )
}

function switchToExpanded() {
  panelMode = 'expanded'
  hideCompactOverlay()
  renderExpandedPanel()
  log('Switched to expanded panel mode')
}

function switchToCompact() {
  panelMode = 'compact'
  hideExpandedPanel()
  if (currentElementContext) {
    renderPromptOverlay(currentElementContext)
  }
  log('Switched to compact dialog mode')
}

function hideCompactOverlay() {
  // Hide and remove all overlay containers
  overlayContainers.forEach((container, panelId) => {
    container.remove()
  })
  overlayContainers.clear()
  panelContexts.clear()
}

function hideExpandedPanel(animate: boolean = true) {
  if (expandedPanelContainer) {
    if (animate) {
      expandedPanelContainer.classList.add('closing')
      setTimeout(() => {
        if (expandedPanelContainer) {
          expandedPanelContainer.remove()
          expandedPanelContainer = null
        }
      }, 200)
    } else {
      expandedPanelContainer.remove()
      expandedPanelContainer = null
    }
  }
}

function buildBreadcrumbPath(context: ElementContext): string {
  const hierarchy = context.componentHierarchy.slice(-3)
  return hierarchy.length > 0
    ? hierarchy.map((h, i) => i < hierarchy.length - 1 ? `${h} <span>›</span>` : h).join(' ')
    : context.filePath
      ? context.filePath.split('/').pop() || 'Element'
      : 'Element'
}

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function renderExpandedPanel() {
  if (expandedPanelContainer) {
    expandedPanelContainer.remove()
  }

  expandedPanelContainer = document.createElement('div')
  expandedPanelContainer.className = 'react-grab-expanded'

  let breadcrumbPath: string
  if (selectedElements.length > 1) {
    breadcrumbPath = `${selectedElements.length} elements selected`
  } else if (currentElementContext) {
    breadcrumbPath = buildBreadcrumbPath(currentElementContext)
  } else {
    breadcrumbPath = 'No element selected'
  }

  expandedPanelContainer.innerHTML = `
    <div class="react-grab-expanded-header">
      <button class="react-grab-select-mode-btn ${isSelectionModeActive ? 'active' : ''}" id="react-grab-expanded-select-mode">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="22" y1="12" x2="18" y2="12"/>
          <line x1="6" y1="12" x2="2" y2="12"/>
          <line x1="12" y1="6" x2="12" y2="2"/>
          <line x1="12" y1="22" x2="12" y2="18"/>
        </svg>
        Select Mode
      </button>
      <div class="react-grab-header-actions">
        <button class="react-grab-header-btn" id="react-grab-expanded-close" title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="react-grab-back-to-dialog" id="react-grab-back-to-dialog">
      <span>Move back to dialog</span>
      <span class="arrow">→</span>
    </div>

    <button class="react-grab-new-conversation-btn" id="react-grab-new-conversation">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
      </svg>
      New conversation
    </button>

    <div class="react-grab-conversation-area" id="react-grab-conversation-area">
      ${conversationHistory.length > 0
        ? conversationHistory.map(msg => `<div class="react-grab-message ${msg.role}">${escapeHtml(msg.content)}</div>`).join('')
        : '<div class="react-grab-conversation-placeholder">Start a conversation...</div>'}
    </div>

    <div class="react-grab-expanded-input-section">
      <div class="react-grab-breadcrumb-chip">
        <svg class="react-grab-breadcrumb-icon" viewBox="-11.5 -10.23174 23 20.46348">
          <circle cx="0" cy="0" r="2.05" fill="#61dafb"/>
          <g stroke="#61dafb" stroke-width="1" fill="none">
            <ellipse rx="11" ry="4.2"/>
            <ellipse rx="11" ry="4.2" transform="rotate(60)"/>
            <ellipse rx="11" ry="4.2" transform="rotate(120)"/>
          </g>
        </svg>
        <span class="react-grab-breadcrumb-path">${breadcrumbPath}</span>
      </div>

      <div class="react-grab-screenshots-preview" id="react-grab-screenshots-preview"></div>

      <textarea
        class="react-grab-expanded-textarea"
        id="react-grab-expanded-input"
        placeholder="Describe what to build..."
        rows="6"
      ></textarea>

      <div class="react-grab-expanded-input-footer">
        <div class="react-grab-spacer"></div>
        <input type="file" id="react-grab-screenshot-input" accept="image/*" multiple style="display: none;" />
        <button class="react-grab-attachment-btn" id="react-grab-screenshot-btn" title="Attach screenshot">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
          </svg>
        </button>
        <button class="react-grab-submit-btn" id="react-grab-expanded-submit" aria-label="Send">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        </button>
      </div>
    </div>
  `

  document.body.appendChild(expandedPanelContainer)

  const closeBtn = document.getElementById('react-grab-expanded-close')
  const backToDialogBtn = document.getElementById('react-grab-back-to-dialog')
  const newConversationBtn = document.getElementById('react-grab-new-conversation')
  const selectModeBtn = document.getElementById('react-grab-expanded-select-mode')
  const submitBtn = document.getElementById('react-grab-expanded-submit')
  const textarea = document.getElementById('react-grab-expanded-input') as HTMLTextAreaElement
  const screenshotBtn = document.getElementById('react-grab-screenshot-btn')
  const screenshotInput = document.getElementById('react-grab-screenshot-input') as HTMLInputElement

  closeBtn?.addEventListener('click', closeAllPanels)
  backToDialogBtn?.addEventListener('click', switchToCompact)
  newConversationBtn?.addEventListener('click', startNewConversation)
  selectModeBtn?.addEventListener('click', handleExpandedSelectMode)
  submitBtn?.addEventListener('click', handleExpandedSubmit)
  screenshotBtn?.addEventListener('click', () => screenshotInput?.click())
  screenshotInput?.addEventListener('change', handleScreenshotAttachment)

  textarea?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleExpandedSubmit()
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      closeAllPanels()
    }
  })

  setTimeout(() => textarea?.focus(), 50)
}

function handleExpandedSelectMode() {
  if (isSelectionModeActive) {
    exitSelectionMode()
    removeSelectionHighlight()
    hideComponentLabel()
    hideHierarchyPath()
    hideExportPanel()
    clearAllSelections()
    removeDragSelectionBox()
    const btn = document.getElementById('react-grab-expanded-select-mode')
    btn?.classList.remove('active')
  } else {
    isSelectionModeActive = true
    const btn = document.getElementById('react-grab-expanded-select-mode')
    btn?.classList.add('active')

    document.addEventListener('mouseover', handleExpandedSelectionHover, true)
    document.addEventListener('click', handleExpandedSelectionClick, true)
    document.addEventListener('contextmenu', handleExpandedSelectionRightClick, true)

    showToast('Click to copy, right-click for AI prompt')
  }
}

handleExpandedSelectionHover = function(event: MouseEvent) {
  if (!isSelectionModeActive) return

  const target = event.target as HTMLElement

  if (
    target.closest('.react-grab-expanded') ||
    target.closest('.react-grab-activation-btn') ||
    target.closest('.react-grab-selection-highlight') ||
    target.closest('.react-grab-component-label') ||
    target.closest('.react-grab-multi-selection-highlight') ||
    target.closest('.react-grab-hierarchy-path') ||
    target.closest('.react-grab-export-panel')
  ) {
    return
  }

  hoveredElement = target
  showSelectionHighlight(target)
  showComponentLabel(target)
}

handleExpandedSelectionClick = function(event: MouseEvent) {
  if (!isSelectionModeActive) return

  const target = event.target as HTMLElement

  if (
    target.closest('.react-grab-expanded') ||
    target.closest('.react-grab-activation-btn') ||
    target.closest('.react-grab-selection-highlight') ||
    target.closest('.react-grab-component-label') ||
    target.closest('.react-grab-multi-selection-highlight') ||
    target.closest('.react-grab-hierarchy-path') ||
    target.closest('.react-grab-export-panel')
  ) {
    return
  }

  event.preventDefault()
  event.stopPropagation()

  if (event.shiftKey) {
    toggleSelection(target)
    if (selectedElements.length > 0) {
      currentTargetElement = selectedElements[selectedElements.length - 1]
      currentElementContext = extractElementContext(currentTargetElement)
    }
    renderExpandedPanel()
    return
  }

  copyElementToClipboard(target, { x: event.clientX, y: event.clientY })
}

handleExpandedSelectionRightClick = function(event: MouseEvent) {
  if (!isSelectionModeActive) return

  const target = event.target as HTMLElement

  if (
    target.closest('.react-grab-expanded') ||
    target.closest('.react-grab-activation-btn') ||
    target.closest('.react-grab-selection-highlight') ||
    target.closest('.react-grab-component-label') ||
    target.closest('.react-grab-multi-selection-highlight') ||
    target.closest('.react-grab-hierarchy-path') ||
    target.closest('.react-grab-export-panel')
  ) {
    return
  }

  event.preventDefault()
  event.stopPropagation()

  // Keep selection mode active when selecting elements in expanded mode
  // Selection mode only exits via explicit toggle (Select Mode button)

  if (selectedElements.length > 1) {
    currentTargetElement = selectedElements[selectedElements.length - 1]
    currentElementContext = extractElementContext(currentTargetElement)
  } else if (selectedElements.length === 1) {
    currentTargetElement = selectedElements[0]
    currentElementContext = extractElementContext(currentTargetElement)
  } else {
    currentTargetElement = target
    currentElementContext = extractElementContext(target)
    showSelectionHighlight(target)
  }

  // Don't exit selection mode - keep it active
  // hideComponentLabel() - keep showing the component label while in selection mode

  // Update the expanded panel to show the new selection
  renderExpandedPanel()
}

function handleScreenshotAttachment(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) return

  Array.from(files).forEach(file => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string
      attachedScreenshots.push({ dataUrl, name: file.name })
      renderScreenshotPreviews()
    }
    reader.readAsDataURL(file)
  })

  // Reset input so same file can be selected again
  input.value = ''
}

function renderScreenshotPreviews() {
  const previewContainer = document.getElementById('react-grab-screenshots-preview')
  if (!previewContainer) return

  if (attachedScreenshots.length === 0) {
    previewContainer.innerHTML = ''
    previewContainer.style.display = 'none'
    return
  }

  previewContainer.style.display = 'flex'
  previewContainer.innerHTML = attachedScreenshots.map((screenshot, index) => `
    <div class="react-grab-screenshot-thumb" data-index="${index}">
      <img src="${screenshot.dataUrl}" alt="${screenshot.name}" />
      <button class="react-grab-screenshot-remove" data-index="${index}" title="Remove">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
  `).join('')

  // Add remove handlers
  previewContainer.querySelectorAll('.react-grab-screenshot-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation()
      const index = parseInt((btn as HTMLElement).dataset.index || '0', 10)
      attachedScreenshots.splice(index, 1)
      renderScreenshotPreviews()
    })
  })
}

function clearScreenshots() {
  attachedScreenshots = []
  renderScreenshotPreviews()
}

function startNewConversation() {
  conversationHistory = []
  currentSessionId = null // Reset session for new conversation
  isStreamingResponse = false
  currentStreamingContent = ''
  clearScreenshots()

  const conversationArea = document.getElementById('react-grab-conversation-area')
  if (conversationArea) {
    conversationArea.innerHTML = '<div class="react-grab-conversation-placeholder">Start a conversation...</div>'
  }
  const textarea = document.getElementById('react-grab-expanded-input') as HTMLTextAreaElement
  if (textarea) {
    textarea.value = ''
    textarea.focus()
  }
}

/**
 * Stream a chat response from the server using SSE
 */
async function streamChatResponse(
  prompt: string,
  elementContext: ElementContext | null,
  screenshots: Array<{ dataUrl: string; name: string }>,
  onDelta: (text: string, fullText: string) => void,
  onComplete: (fullText: string, sessionId: string) => void,
  onError: (error: string) => void
): Promise<void> {
  const payload: Record<string, unknown> = {
    prompt,
    elementContext: elementContext ? {
      filePath: elementContext.filePath,
      componentHierarchy: elementContext.componentHierarchy,
      htmlSnippet: elementContext.htmlSnippet,
      lineNumber: elementContext.lineNumber,
      textContent: elementContext.textContent,
      siblingPosition: elementContext.siblingPosition,
      parentContext: elementContext.parentContext,
      uniqueIdentifiers: elementContext.uniqueIdentifiers,
    } : undefined,
    sessionId: currentSessionId,
  }

  if (screenshots.length > 0) {
    payload.screenshots = screenshots.map(s => ({
      dataUrl: s.dataUrl,
      name: s.name,
    }))
  }

  try {
    const response = await fetch('/api/grab-chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let fullText = ''
    let newSessionId = currentSessionId || ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })

      // Process complete SSE messages
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            continue
          }

          try {
            const parsed = JSON.parse(data)

            switch (parsed.type) {
              case 'session':
                newSessionId = parsed.sessionId
                break

              case 'delta':
              case 'text':
                fullText = parsed.fullText || fullText + (parsed.text || '')
                onDelta(parsed.text || '', fullText)
                break

              case 'message_stop':
              case 'done':
                if (parsed.sessionId) {
                  newSessionId = parsed.sessionId
                }
                if (parsed.fullText) {
                  fullText = parsed.fullText
                }
                break

              case 'error':
                onError(parsed.error || 'Unknown error')
                return
            }
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }

    onComplete(fullText, newSessionId)
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    onError(errorMessage)
  }
}

async function handleExpandedSubmit() {
  if (isSubmitting || !currentElementContext) return

  const textarea = document.getElementById('react-grab-expanded-input') as HTMLTextAreaElement
  const submitBtn = document.getElementById('react-grab-expanded-submit') as HTMLButtonElement
  const conversationArea = document.getElementById('react-grab-conversation-area')

  const prompt = textarea?.value?.trim()
  if (!prompt) return

  isSubmitting = true
  isStreamingResponse = true
  currentStreamingContent = ''

  // Add user message to conversation history and UI
  conversationHistory.push({ role: 'user', content: prompt })

  if (conversationArea) {
    const placeholder = conversationArea.querySelector('.react-grab-conversation-placeholder')
    if (placeholder) placeholder.remove()

    const userMsg = document.createElement('div')
    userMsg.className = 'react-grab-message user'
    userMsg.textContent = prompt
    conversationArea.appendChild(userMsg)
    conversationArea.scrollTop = conversationArea.scrollHeight
  }

  if (textarea) {
    textarea.value = ''
  }

  if (submitBtn) {
    submitBtn.disabled = true
    submitBtn.innerHTML = `
      <svg class="react-grab-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
      </svg>
    `
  }

  // Create streaming message element
  let streamingMsgEl: HTMLDivElement | null = null
  if (conversationArea) {
    streamingMsgEl = document.createElement('div')
    streamingMsgEl.className = 'react-grab-message assistant streaming'
    streamingMsgEl.innerHTML = '<span class="react-grab-thinking">Thinking...</span>'
    conversationArea.appendChild(streamingMsgEl)
    conversationArea.scrollTop = conversationArea.scrollHeight
  }

  // Save screenshots for the request
  const screenshotsToSend = [...attachedScreenshots]

  // Use streaming endpoint
  await streamChatResponse(
    prompt,
    currentElementContext,
    screenshotsToSend,
    // onDelta - called as response streams in
    (text, fullText) => {
      currentStreamingContent = fullText
      if (streamingMsgEl) {
        // Remove thinking indicator on first content
        const thinking = streamingMsgEl.querySelector('.react-grab-thinking')
        if (thinking) {
          thinking.remove()
        }
        // Update with streaming content
        streamingMsgEl.textContent = fullText
        streamingMsgEl.classList.add('has-content')
      }
      if (conversationArea) {
        conversationArea.scrollTop = conversationArea.scrollHeight
      }
    },
    // onComplete - called when response is finished
    (fullText, sessionId) => {
      isSubmitting = false
      isStreamingResponse = false

      // Update session ID
      if (sessionId) {
        currentSessionId = sessionId
      }

      // Finalize the streaming message
      const assistantMessage = fullText || 'Request processed.'
      conversationHistory.push({ role: 'assistant', content: assistantMessage })

      if (streamingMsgEl) {
        streamingMsgEl.classList.remove('streaming')
        streamingMsgEl.textContent = assistantMessage
      }

      // Clear screenshots after successful send
      clearScreenshots()

      // Re-enable submit button
      if (submitBtn) {
        submitBtn.disabled = false
        submitBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        `
      }
    },
    // onError - called on error
    (error) => {
      console.error('[React Grab] Stream error:', error)
      isSubmitting = false
      isStreamingResponse = false

      conversationHistory.push({ role: 'assistant', content: `Error: ${error}` })

      if (streamingMsgEl) {
        streamingMsgEl.classList.remove('streaming')
        streamingMsgEl.classList.add('error')
        streamingMsgEl.textContent = `Error: ${error}`
      }

      // Re-enable submit button
      if (submitBtn) {
        submitBtn.disabled = false
        submitBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        `
      }
    }
  )
}

closeAllPanels = function() {
  panelMode = 'compact'
  hideCompactOverlay()
  hideExpandedPanel()
  removeSelectionHighlight()
  hideComponentLabel()
  hideHierarchyPath()
  hideExportPanel()
  clearAllSelections()
  removeDragSelectionBox()

  if (isSelectionModeActive) {
    exitSelectionMode()
  } else {
    // Also remove scroll listeners if not in selection mode
    removeScrollResizeListeners()
  }

  currentElementContext = null
  currentTargetElement = null
  currentTreePosition = null
  isSubmitting = false
}

function hideOverlay() {
  if (panelMode === 'expanded') {
    closeAllPanels()
  } else {
    // Hide all compact overlay panels using the multi-panel system
    hideCompactOverlay()
    removeSelectionHighlight()
    hideComponentLabel()
    hideHierarchyPath()
    hideExportPanel()
    clearAllSelections()
    removeDragSelectionBox()
    if (isSelectionModeActive) {
      exitSelectionMode()
    } else {
      removeCrosshairs()
      document.documentElement.classList.remove('react-grab-selection-active')
    }
    currentElementContext = null
    currentTargetElement = null
    currentTreePosition = null
    isSubmitting = false
  }
}

function handleKeyboardShortcut(event: KeyboardEvent) {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const modifierKey = isMac ? event.metaKey : event.ctrlKey

  if (modifierKey && event.shiftKey && event.key.toLowerCase() === 'z') {
    event.preventDefault()
    event.stopPropagation()

    log('Cmd+Shift+Z pressed - toggling selection mode')

    // Pure toggle behavior: always toggle selection mode on/off
    if (isSelectionModeActive) {
      exitSelectionMode()
      closeAllPanels()
      clearAllSelections()
    } else {
      enterSelectionMode()
      showToast('Click an element to select it. Press <kbd>ESC</kbd> to cancel.')
    }
  }

  if (modifierKey && event.key.toLowerCase() === 'e') {
    event.preventDefault()
    event.stopPropagation()
    showExportPanel()
    return
  }

  if (isSelectionModeActive) {
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      event.stopPropagation()
      navigateToParent()
      return
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      event.stopPropagation()
      navigateToChild()
      return
    }

    if (event.key === 'ArrowRight') {
      event.preventDefault()
      event.stopPropagation()
      navigateToNextSibling()
      return
    }

    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      event.stopPropagation()
      navigateToPrevSibling()
      return
    }

    if (event.key === 'Enter' && currentTreePosition) {
      event.preventDefault()
      event.stopPropagation()
      selectTreePosition()
      return
    }
  }

  if (event.key === 'Escape') {
    event.preventDefault()
    closeAllPanels()
  }
}

function setupKeyboardListener() {
  if (keyboardListenerAttached) return

  document.addEventListener('keydown', handleKeyboardShortcut, true)
  keyboardListenerAttached = true
  log('Keyboard listener attached (Cmd+Shift+Z)')
}

/**
 * Cleanup sessions when browser window closes
 */
function setupCleanupHandler() {
  window.addEventListener('beforeunload', () => {
    // Notify server to cleanup temp files and session
    // Use sendBeacon for reliable delivery during page unload
    const cleanupEndpoint = config.apiEndpoint.replace('grab-prompt', 'grab-cleanup')
    navigator.sendBeacon(cleanupEndpoint, JSON.stringify({
      cleanup: true,
      sessionId: currentSessionId, // Include session ID for server cleanup
    }))

    // Reset client-side state (explicit, though it would be cleared anyway)
    conversationHistory = []
    currentSessionId = null
    isStreamingResponse = false
    currentStreamingContent = ''
  })

  log('Cleanup handler registered for browser close')
}

/**
 * Register the React Grab Plugin
 */
export function registerReactGrabPlugin(userConfig?: ReactGrabConfig) {
  // Merge user config with defaults
  config = { ...defaultConfig, ...userConfig }

  // Inject styles
  injectStyles()

  // Setup the keyboard shortcut listener
  setupKeyboardListener()

  // Setup cleanup handler for browser close
  setupCleanupHandler()

  // Overlay containers are now created on-demand via the Map-based multi-panel system
  // No need to pre-create a single container

  // Initialize toolbar
  initializeToolbar()

  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const shortcut = isMac ? 'Cmd+Shift+Z' : 'Ctrl+Shift+Z'
  log(`Plugin initialized - use toolbar button or ${shortcut}`)
}

// Auto-register when this module loads in dev mode
if (typeof window !== 'undefined') {
  setTimeout(registerReactGrabPlugin, 100)
}
