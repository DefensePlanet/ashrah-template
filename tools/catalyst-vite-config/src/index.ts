/**
 * Catalyst Vite Config
 *
 * Shared Vite configuration for all Catalyst React projects.
 * Automatically includes react-grab for AI-assisted development in dev mode.
 *
 * Usage:
 *   // vite.config.ts
 *   import { defineCatalystConfig } from '@catalyst/vite-config'
 *
 *   export default defineCatalystConfig({
 *     // your custom config here (optional)
 *   })
 *
 * Or with merging:
 *   import { defineCatalystConfig, mergeCatalystConfig } from '@catalyst/vite-config'
 *   import someOtherPlugin from 'some-plugin'
 *
 *   export default mergeCatalystConfig(
 *     { plugins: [someOtherPlugin()] },
 *     defineCatalystConfig()
 *   )
 */

import { defineConfig, mergeConfig, type UserConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { reactGrabVitePlugin, type ReactGrabVitePluginConfig } from '@catalyst/react-grab/vite'

export interface CatalystViteConfig {
  /**
   * React Grab configuration options
   * Set to false to disable react-grab entirely
   */
  reactGrab?: ReactGrabVitePluginConfig | false

  /**
   * Whether to include the default React plugin
   * Default: true
   */
  includeReactPlugin?: boolean
}

/**
 * Define a Catalyst Vite config with all the standard plugins and settings.
 *
 * @param userConfig - Custom Vite configuration to merge
 * @param catalystOptions - Catalyst-specific options
 * @returns Complete Vite configuration
 *
 * @example
 * // Basic usage - just works
 * export default defineCatalystConfig()
 *
 * @example
 * // With custom Vite config
 * export default defineCatalystConfig({
 *   server: { port: 3001 },
 *   build: { outDir: 'build' }
 * })
 *
 * @example
 * // With react-grab options
 * export default defineCatalystConfig(
 *   { server: { port: 3001 } },
 *   { reactGrab: { debug: true } }
 * )
 *
 * @example
 * // Disable react-grab
 * export default defineCatalystConfig(
 *   {},
 *   { reactGrab: false }
 * )
 */
export function defineCatalystConfig(
  userConfig: UserConfig = {},
  catalystOptions: CatalystViteConfig = {}
): UserConfig {
  const {
    reactGrab = {},
    includeReactPlugin = true,
  } = catalystOptions

  // Build the plugins array
  const plugins = []

  // Add React plugin if not disabled
  if (includeReactPlugin) {
    plugins.push(react())
  }

  // Add react-grab plugin in dev mode (unless disabled)
  if (reactGrab !== false) {
    plugins.push(reactGrabVitePlugin(reactGrab))
  }

  // Base Catalyst configuration
  const baseConfig = defineConfig({
    plugins,
    // Sensible defaults for Catalyst projects
    build: {
      // Generate source maps for debugging
      sourcemap: true,
    },
    server: {
      // Allow connections from all hosts (useful for testing)
      host: true,
    },
  })

  // Merge with user configuration (user config takes precedence)
  return mergeConfig(baseConfig, userConfig)
}

/**
 * Merge multiple Vite configurations with Catalyst defaults.
 * Later configs override earlier ones.
 *
 * @param configs - Array of Vite configurations to merge
 * @returns Merged configuration
 *
 * @example
 * export default mergeCatalystConfig(
 *   defineCatalystConfig(),
 *   { plugins: [myPlugin()] }
 * )
 */
export function mergeCatalystConfig(...configs: UserConfig[]): UserConfig {
  return configs.reduce((acc, config) => mergeConfig(acc, config), {})
}

// Legacy aliases for backward compatibility
/** @deprecated Use defineCatalystConfig instead */
export const defineBuilderOSConfig = defineCatalystConfig
/** @deprecated Use mergeCatalystConfig instead */
export const mergeBuilderOSConfig = mergeCatalystConfig
/** @deprecated Use CatalystViteConfig instead */
export type BuilderOSViteConfig = CatalystViteConfig

// Re-export useful types and utilities
export { mergeConfig, defineConfig } from 'vite'
export type { UserConfig } from 'vite'
export { reactGrabVitePlugin } from '@catalyst/react-grab/vite'
export type { ReactGrabVitePluginConfig } from '@catalyst/react-grab/vite'
