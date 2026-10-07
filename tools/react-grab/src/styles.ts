/**
 * React Grab Plugin Styles
 *
 * Extracted from react-grab-plugin.ts for maintainability.
 * These styles are injected at runtime via the injectStyles() function.
 */

export const REACT_GRAB_STYLES = `
    /* ========== Toolbar Container (Bottom-Right) - Single Button ========== */
    .react-grab-toolbar {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 999997;
    }

    /* Single circular button */
    .react-grab-toolbar-btn {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      background: hsl(240 6% 20%);
      color: hsl(0 0% 70%);
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25), 0 2px 6px rgba(0, 0, 0, 0.15);
      transition: background 0.2s ease, color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
    }

    .react-grab-toolbar-btn:hover {
      background: hsl(240 6% 25%);
      color: hsl(0 0% 90%);
      transform: scale(1.05);
    }

    .react-grab-toolbar-btn:active {
      transform: scale(0.95);
    }

    /* Active state - orange background */
    .react-grab-toolbar-btn.active {
      background: hsl(24 95% 53%);
      color: hsl(0 0% 100%);
      box-shadow: 0 4px 20px rgba(249, 115, 22, 0.4), 0 2px 8px rgba(249, 115, 22, 0.25);
    }

    .react-grab-toolbar-btn.active:hover {
      background: hsl(24 95% 58%);
    }

    .react-grab-toolbar-btn svg {
      width: 20px;
      height: 20px;
      flex-shrink: 0;
    }

    @media (prefers-color-scheme: light) {
      .react-grab-toolbar-btn {
        background: hsl(240 6% 25%);
        color: hsl(0 0% 80%);
      }

      .react-grab-toolbar-btn:hover {
        background: hsl(240 6% 30%);
      }
    }

    /* ========== Selection Highlight (Orange Outline) ========== */
    .react-grab-selection-highlight {
      position: fixed;
      pointer-events: none;
      border: 2px solid hsl(24 95% 53%);
      border-radius: 4px;
      background: hsl(24 95% 53% / 0.08);
      z-index: 999994;
      transition: all 0.15s ease;
    }

    /* ========== Crosshair Lines (Follow Cursor) ========== */
    .react-grab-crosshair-v {
      position: fixed;
      top: 0;
      bottom: 0;
      width: 1px;
      background: hsl(24 95% 53% / 0.5);
      pointer-events: none;
      z-index: 999993;
    }

    .react-grab-crosshair-h {
      position: fixed;
      left: 0;
      right: 0;
      height: 1px;
      background: hsl(24 95% 53% / 0.5);
      pointer-events: none;
      z-index: 999993;
    }

    /* ========== Hide Cursor in Selection Mode ========== */
    .react-grab-selection-active {
      cursor: none !important;
    }

    .react-grab-selection-active * {
      cursor: none !important;
    }

    /* ========== Restore Cursor on Prompt Panels ========== */
    .react-grab-selection-active #react-grab-overlay,
    .react-grab-selection-active #react-grab-overlay *,
    .react-grab-selection-active .react-grab-prompt,
    .react-grab-selection-active .react-grab-prompt *,
    .react-grab-selection-active .react-grab-expanded,
    .react-grab-selection-active .react-grab-expanded * {
      cursor: auto !important;
    }

    .react-grab-selection-active #react-grab-overlay textarea,
    .react-grab-selection-active #react-grab-overlay input,
    .react-grab-selection-active .react-grab-expanded textarea,
    .react-grab-selection-active .react-grab-expanded input {
      cursor: text !important;
    }

    .react-grab-selection-active #react-grab-overlay button,
    .react-grab-selection-active .react-grab-expanded button,
    .react-grab-selection-active .react-grab-prompt-header-btn {
      cursor: pointer !important;
    }

    /* ========== Prompt Panel (Cleo-Inspired) ========== */
    #react-grab-overlay {
      position: fixed;
      z-index: 999999;
      pointer-events: auto;
      font-family: Inter, system-ui, -apple-system, sans-serif;
    }

    .react-grab-prompt {
      background: hsl(240 10% 6%);
      border: 1px solid hsl(240 3.7% 15.9%);
      border-radius: 12px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 0 1px hsl(240 3.7% 12%);
      padding: 12px;
      min-width: 340px;
      max-width: 420px;
      display: flex;
      flex-direction: column;
      animation: react-grab-panel-in 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    @keyframes react-grab-panel-in {
      from {
        opacity: 0;
        transform: translateY(-8px) scale(0.96);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    /* ========== Prompt Panel Header Row ========== */
    .react-grab-prompt-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }

    .react-grab-prompt-header-actions {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }

    .react-grab-prompt-header-btn {
      flex-shrink: 0;
      background: hsl(240 5.9% 12%);
      border: 1px solid hsl(240 3.7% 20%);
      color: hsl(240 5% 60%);
      cursor: pointer;
      padding: 8px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 0.15s, background 0.15s, border-color 0.15s, transform 0.1s;
    }

    .react-grab-prompt-header-btn:hover {
      color: hsl(0 0% 98%);
      background: hsl(240 5.9% 16%);
      border-color: hsl(240 3.7% 28%);
    }

    .react-grab-prompt-header-btn:active {
      transform: scale(0.95);
    }

    .react-grab-prompt-header-btn svg {
      width: 18px;
      height: 18px;
    }

    .react-grab-prompt-header-btn.expand-btn:hover {
      color: hsl(24 95% 60%);
      border-color: hsl(24 95% 45%);
      background: hsl(24 95% 53% / 0.1);
    }

    .react-grab-prompt-header-btn.close-btn:hover {
      color: hsl(0 70% 60%);
      border-color: hsl(0 70% 50%);
      background: hsl(0 70% 50% / 0.1);
    }

    /* ========== Component Breadcrumb Chip ========== */
    .react-grab-breadcrumb-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: hsl(240 5.9% 10%);
      border: 1px solid hsl(240 3.7% 18%);
      border-radius: 6px;
      padding: 5px 8px 5px 10px;
      font-size: 12px;
      color: hsl(240 5% 64.9%);
      max-width: 100%;
      min-width: 0;
      flex: 1;
    }

    .react-grab-breadcrumb-icon {
      flex-shrink: 0;
      width: 16px;
      height: 16px;
      color: #61dafb;
    }

    .react-grab-breadcrumb-path {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
    }

    .react-grab-breadcrumb-path span {
      color: hsl(240 5% 50%);
    }

    .react-grab-breadcrumb-deselect {
      flex-shrink: 0;
      background: transparent;
      border: none;
      color: hsl(240 5% 45%);
      cursor: pointer;
      padding: 2px;
      border-radius: 3px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 0.15s, background 0.15s;
      margin-left: 4px;
    }

    .react-grab-breadcrumb-deselect:hover {
      color: hsl(0 0% 90%);
      background: hsl(240 3.7% 18%);
    }

    /* ========== Text Input (Textarea) ========== */
    .react-grab-input-wrapper {
      position: relative;
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 120px;
    }

    .react-grab-input {
      width: 100%;
      flex: 1;
      min-height: 100%;
      background: hsl(240 10% 8%);
      border: 1px solid hsl(240 3.7% 20%);
      border-radius: 8px;
      padding: 12px;
      padding-bottom: 48px;
      font-size: 14px;
      line-height: 1.5;
      color: hsl(0 0% 98%);
      outline: none;
      resize: none;
      transition: border-color 0.2s ease;
      font-family: inherit;
    }

    .react-grab-input:focus {
      border-color: hsl(24 95% 53%);
    }

    .react-grab-input::placeholder {
      color: hsl(240 5% 40%);
    }

    /* ========== Bottom Row (Hidden - button now inside textarea) ========== */
    .react-grab-bottom-row {
      display: none;
    }

    .react-grab-spacer {
      flex: 1;
    }

    .react-grab-submit-btn {
      position: absolute;
      bottom: 8px;
      right: 8px;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: linear-gradient(135deg, hsl(24 95% 53%) 0%, hsl(32 95% 50%) 100%);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
      box-shadow: 0 2px 8px hsl(24 95% 53% / 0.3);
      z-index: 1;
    }

    .react-grab-submit-btn:hover:not(:disabled) {
      transform: scale(1.05);
      box-shadow: 0 4px 12px hsl(24 95% 53% / 0.4);
    }

    .react-grab-submit-btn:active:not(:disabled) {
      transform: scale(0.95);
    }

    .react-grab-submit-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .react-grab-submit-btn svg {
      width: 18px;
      height: 18px;
      color: white;
    }

    /* ========== Spinner ========== */
    .react-grab-spinner {
      animation: react-grab-spin 0.8s linear infinite;
    }

    @keyframes react-grab-spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    /* ========== Feedback Messages ========== */
    .react-grab-feedback {
      margin-top: 10px;
      padding: 8px 10px;
      border-radius: 6px;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
      animation: react-grab-fade-in 0.2s ease;
    }

    @keyframes react-grab-fade-in {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .react-grab-feedback.success {
      background: hsl(142.1 76.2% 36.3% / 0.15);
      color: hsl(142.1 70.6% 45.3%);
      border: 1px solid hsl(142.1 76.2% 36.3% / 0.3);
    }

    .react-grab-feedback.error {
      background: hsl(0 84.2% 60.2% / 0.15);
      color: hsl(0 84.2% 60.2%);
      border: 1px solid hsl(0 84.2% 60.2% / 0.3);
    }

    .react-grab-feedback svg {
      width: 14px;
      height: 14px;
      flex-shrink: 0;
    }

    /* ========== Toast Notification ========== */
    .react-grab-toast {
      position: fixed;
      bottom: 72px;
      right: 20px;
      width: fit-content;
      background: hsl(240 10% 8%);
      border: 1px solid hsl(240 3.7% 18%);
      border-radius: 8px;
      padding: 10px 14px;
      font-family: Inter, system-ui, -apple-system, sans-serif;
      font-size: 12px;
      color: hsl(240 5% 75%);
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
      z-index: 999998;
      animation: react-grab-toast-in 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .react-grab-toast.cursor-toast {
      bottom: auto;
      left: auto;
      width: fit-content;
      padding: 6px 10px;
      font-size: 11px;
      border-radius: 6px;
      pointer-events: none;
      animation: react-grab-cursor-toast-in 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .react-grab-toast kbd {
      background: hsl(240 5.9% 15%);
      border: 1px solid hsl(240 3.7% 25%);
      border-radius: 4px;
      padding: 2px 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      margin: 0 2px;
    }

    @keyframes react-grab-toast-in {
      from {
        opacity: 0;
        transform: translateY(10px) scale(0.95);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    @keyframes react-grab-cursor-toast-in {
      from {
        opacity: 0;
        transform: scale(0.9);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }

    /* ========== Expanded Panel (Full-Height Sidebar) ========== */
    .react-grab-expanded {
      position: fixed;
      top: 0;
      right: 0;
      width: 420px;
      height: 100vh;
      background: hsl(240 10% 6%);
      border-left: 1px solid hsl(240 3.7% 15.9%);
      display: flex;
      flex-direction: column;
      z-index: 999999;
      font-family: Inter, system-ui, -apple-system, sans-serif;
      animation: react-grab-slide-in-right 0.25s cubic-bezier(0.32, 0.72, 0, 1);
    }

    @keyframes react-grab-slide-in-right {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }

    @keyframes react-grab-slide-out-right {
      from { transform: translateX(0); }
      to { transform: translateX(100%); }
    }

    .react-grab-expanded.closing {
      animation: react-grab-slide-out-right 0.2s ease-out forwards;
    }

    /* ========== Expanded Panel Header ========== */
    .react-grab-expanded-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-bottom: 1px solid hsl(240 3.7% 15.9%);
    }

    .react-grab-select-mode-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: hsl(240 5.9% 10%);
      border: 1px solid hsl(240 3.7% 18%);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 11px;
      font-weight: 500;
      color: hsl(240 5% 64.9%);
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s, color 0.15s;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .react-grab-select-mode-btn:hover {
      border-color: hsl(24 95% 53%);
      color: hsl(24 95% 53%);
      background: hsl(24 95% 53% / 0.08);
    }

    .react-grab-select-mode-btn.active {
      border-color: hsl(24 95% 53%);
      color: hsl(24 95% 53%);
      background: hsl(24 95% 53% / 0.12);
    }

    .react-grab-select-mode-btn svg {
      width: 14px;
      height: 14px;
    }

    .react-grab-header-actions {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .react-grab-header-btn {
      background: transparent;
      border: none;
      color: hsl(240 5% 50%);
      cursor: pointer;
      padding: 6px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 0.15s, background 0.15s;
    }

    .react-grab-header-btn:hover {
      color: hsl(0 0% 98%);
      background: hsl(240 3.7% 18%);
    }

    .react-grab-header-btn svg {
      width: 16px;
      height: 16px;
    }

    /* ========== Back to Dialog Link ========== */
    .react-grab-back-to-dialog {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 16px;
      font-size: 12px;
      color: hsl(240 5% 64.9%);
      cursor: pointer;
      transition: color 0.15s, background 0.15s;
      border-bottom: 1px solid hsl(240 3.7% 12%);
    }

    .react-grab-back-to-dialog:hover {
      color: hsl(0 0% 98%);
      background: hsl(240 5.9% 8%);
    }

    .react-grab-back-to-dialog .arrow {
      color: hsl(240 5% 50%);
      transition: color 0.15s, transform 0.15s;
    }

    .react-grab-back-to-dialog:hover .arrow {
      color: hsl(0 0% 98%);
      transform: translateX(2px);
    }

    /* ========== New Conversation Button ========== */
    .react-grab-new-conversation-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin: 12px 16px;
      padding: 10px 16px;
      background: hsl(240 5.9% 10%);
      border: 1px dashed hsl(240 3.7% 25%);
      border-radius: 8px;
      font-size: 13px;
      color: hsl(240 5% 64.9%);
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s, color 0.15s;
    }

    .react-grab-new-conversation-btn:hover {
      border-color: hsl(24 95% 53%);
      color: hsl(24 95% 53%);
      background: hsl(24 95% 53% / 0.05);
      border-style: solid;
    }

    .react-grab-new-conversation-btn svg {
      width: 16px;
      height: 16px;
    }

    /* ========== Conversation Area ========== */
    .react-grab-conversation-area {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .react-grab-conversation-placeholder {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      color: hsl(240 5% 40%);
      font-size: 14px;
      text-align: center;
    }

    .react-grab-message {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.5;
      animation: react-grab-message-in 0.2s ease-out;
    }

    @keyframes react-grab-message-in {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .react-grab-message.user {
      align-self: flex-end;
      background: hsl(24 95% 53%);
      color: white;
      border-bottom-right-radius: 4px;
    }

    .react-grab-message.assistant {
      align-self: flex-start;
      background: hsl(240 5.9% 12%);
      color: hsl(0 0% 95%);
      border: 1px solid hsl(240 3.7% 18%);
      border-bottom-left-radius: 4px;
    }

    /* ========== Expanded Panel Input Section (Bottom) ========== */
    .react-grab-expanded-input-section {
      padding: 12px 16px 16px;
      border-top: 1px solid hsl(240 3.7% 15.9%);
      background: hsl(240 10% 5%);
    }

    .react-grab-expanded-input-section .react-grab-breadcrumb-chip {
      margin-bottom: 12px;
    }

    .react-grab-expanded-textarea {
      width: 100%;
      min-height: 150px;
      max-height: 300px;
      background: hsl(240 5.9% 10%);
      border: 1px solid hsl(240 3.7% 18%);
      border-radius: 8px;
      padding: 12px 14px;
      font-size: 14px;
      line-height: 1.5;
      color: hsl(0 0% 98%);
      outline: none;
      resize: vertical;
      transition: border-color 0.2s ease;
      font-family: inherit;
    }

    .react-grab-expanded-textarea:focus {
      border-color: hsl(24 95% 53%);
    }

    .react-grab-expanded-textarea::placeholder {
      color: hsl(240 5% 40%);
    }

    .react-grab-expanded-input-footer {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
    }

    /* ========== Screenshot Attachment ========== */
    .react-grab-screenshots-preview {
      display: none;
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px 0;
      margin-bottom: 8px;
    }

    .react-grab-screenshot-thumb {
      position: relative;
      width: 64px;
      height: 64px;
      border-radius: 6px;
      overflow: hidden;
      border: 1px solid hsl(240 3.7% 25%);
      background: hsl(240 10% 12%);
    }

    .react-grab-screenshot-thumb img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .react-grab-screenshot-remove {
      position: absolute;
      top: 2px;
      right: 2px;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      border: none;
      background: hsl(0 0% 0% / 0.7);
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      opacity: 0;
      transition: opacity 0.15s ease;
    }

    .react-grab-screenshot-thumb:hover .react-grab-screenshot-remove {
      opacity: 1;
    }

    .react-grab-screenshot-remove svg {
      width: 10px;
      height: 10px;
    }

    .react-grab-attachment-btn {
      width: 32px;
      height: 32px;
      border-radius: 6px;
      border: none;
      background: hsl(240 6% 18%);
      color: hsl(0 0% 65%);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      transition: background 0.15s ease, color 0.15s ease;
    }

    .react-grab-attachment-btn:hover {
      background: hsl(240 6% 22%);
      color: hsl(0 0% 85%);
    }

    .react-grab-attachment-btn svg {
      width: 16px;
      height: 16px;
    }

    /* ========== Component Label (React-Grab Style) ========== */
    .react-grab-component-label {
      position: fixed;
      background: hsl(24 95% 53%);
      color: white;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      z-index: 999995;
      pointer-events: none;
      white-space: nowrap;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      transform: translateY(-100%) translateY(-8px);
      animation: react-grab-label-in 0.15s ease-out;
    }

    @keyframes react-grab-label-in {
      from {
        opacity: 0;
        transform: translateY(-100%) translateY(-4px) scale(0.95);
      }
      to {
        opacity: 1;
        transform: translateY(-100%) translateY(-8px) scale(1);
      }
    }

    .react-grab-component-label::after {
      content: '';
      position: absolute;
      bottom: -4px;
      left: 12px;
      width: 0;
      height: 0;
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-top: 5px solid hsl(24 95% 53%);
    }

    /* ========== Multi-Selection Highlight ========== */
    .react-grab-multi-selection-highlight {
      position: fixed;
      pointer-events: none;
      border: 2px dashed hsl(24 95% 53%);
      border-radius: 4px;
      background: hsl(24 95% 53% / 0.12);
      z-index: 999993;
    }

    /* ========== Drag Selection Box ========== */
    .react-grab-drag-selection-box {
      position: fixed;
      border: 2px solid hsl(24 95% 53%);
      border-radius: 2px;
      background: hsl(24 95% 53% / 0.15);
      z-index: 999996;
      pointer-events: none;
    }

    /* ========== Tree Navigation Path ========== */
    .react-grab-hierarchy-path {
      position: fixed;
      bottom: 72px;
      right: 120px;
      background: hsl(240 10% 8%);
      border: 1px solid hsl(240 3.7% 18%);
      border-radius: 8px;
      padding: 8px 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      color: hsl(240 5% 75%);
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
      z-index: 999998;
      display: flex;
      align-items: center;
      gap: 6px;
      max-width: 400px;
      overflow: hidden;
    }

    .react-grab-hierarchy-path .path-item {
      color: hsl(240 5% 55%);
      white-space: nowrap;
    }

    .react-grab-hierarchy-path .path-item.current {
      color: hsl(24 95% 53%);
      font-weight: 600;
    }

    .react-grab-hierarchy-path .path-separator {
      color: hsl(240 5% 40%);
    }

    .react-grab-hierarchy-path .nav-hint {
      margin-left: 8px;
      color: hsl(240 5% 45%);
      font-size: 10px;
    }

    /* ========== Export Panel ========== */
    .react-grab-export-panel {
      position: fixed;
      bottom: 72px;
      right: 20px;
      background: hsl(240 10% 8%);
      border: 1px solid hsl(240 3.7% 18%);
      border-radius: 10px;
      padding: 12px;
      font-family: Inter, system-ui, -apple-system, sans-serif;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
      z-index: 999998;
      min-width: 280px;
      animation: react-grab-panel-in 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .react-grab-export-panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
    }

    .react-grab-export-panel-title {
      font-size: 12px;
      font-weight: 600;
      color: hsl(0 0% 95%);
    }

    .react-grab-export-close {
      background: transparent;
      border: none;
      color: hsl(240 5% 50%);
      cursor: pointer;
      padding: 4px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .react-grab-export-close:hover {
      color: hsl(0 0% 98%);
      background: hsl(240 3.7% 18%);
    }

    .react-grab-export-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 10px 12px;
      background: hsl(240 5.9% 10%);
      border: 1px solid hsl(240 3.7% 18%);
      border-radius: 6px;
      color: hsl(240 5% 75%);
      font-size: 12px;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s, color 0.15s;
      margin-bottom: 6px;
    }

    .react-grab-export-btn:last-child {
      margin-bottom: 0;
    }

    .react-grab-export-btn:hover {
      background: hsl(240 5.9% 14%);
      border-color: hsl(24 95% 53%);
      color: hsl(24 95% 53%);
    }

    .react-grab-export-btn svg {
      width: 14px;
      height: 14px;
      flex-shrink: 0;
    }

    /* ========== Selection Count Badge ========== */
    .react-grab-selection-count {
      position: fixed;
      bottom: 20px;
      right: 150px;
      background: hsl(24 95% 53%);
      color: white;
      font-family: Inter, system-ui, -apple-system, sans-serif;
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 12px;
      z-index: 999997;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }

    /* ========== Streaming Response Styles ========== */
    .react-grab-feedback.streaming {
      background: hsl(220 14.3% 95.9% / 0.1);
      color: hsl(220 8.9% 46.1%);
      border: 1px solid hsl(220 13% 91% / 0.2);
      display: flex;
      align-items: flex-start;
      gap: 8px;
    }

    .react-grab-feedback.streaming.has-content {
      background: hsl(240 5.9% 10%);
      border-color: hsl(240 3.7% 18%);
      color: hsl(0 0% 85%);
    }

    .react-grab-streaming-text {
      flex: 1;
      line-height: 1.4;
      word-break: break-word;
    }

    .react-grab-thinking {
      color: hsl(240 5% 55%);
      font-style: italic;
    }

    .react-grab-expand-response {
      background: transparent;
      border: none;
      color: hsl(24 95% 53%);
      font-size: 11px;
      cursor: pointer;
      padding: 2px 6px;
      margin-left: 8px;
      border-radius: 4px;
      transition: background 0.15s;
    }

    .react-grab-expand-response:hover {
      background: hsl(24 95% 53% / 0.1);
    }

    /* Streaming message in conversation area */
    .react-grab-message.streaming {
      background: hsl(240 5.9% 10%);
      border: 1px solid hsl(240 3.7% 18%);
      min-height: 40px;
    }

    .react-grab-message.streaming .react-grab-thinking {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .react-grab-message.streaming .react-grab-thinking::before {
      content: '';
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: hsl(24 95% 53%);
      animation: react-grab-pulse 1s ease-in-out infinite;
    }

    @keyframes react-grab-pulse {
      0%, 100% { opacity: 0.4; transform: scale(0.8); }
      50% { opacity: 1; transform: scale(1); }
    }

    .react-grab-message.streaming.has-content {
      background: hsl(240 5.9% 12%);
    }

    .react-grab-message.assistant.error {
      background: hsl(0 84.2% 60.2% / 0.15);
      border-color: hsl(0 84.2% 60.2% / 0.3);
      color: hsl(0 84.2% 60.2%);
    }

    /* ========== Session Indicator ========== */
    .react-grab-session-indicator {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      font-size: 10px;
      color: hsl(240 5% 55%);
      border-bottom: 1px solid hsl(240 3.7% 12%);
    }

    .react-grab-session-indicator::before {
      content: '';
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: hsl(142.1 76.2% 36.3%);
    }

    .react-grab-session-indicator.new-session::before {
      background: hsl(24 95% 53%);
    }
`
