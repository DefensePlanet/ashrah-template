#!/usr/bin/env node
/**
 * React Grab CLI
 *
 * Auto-detects React framework and configures the project.
 *
 * Usage: npx @catalyst/react-grab init
 */

import { existsSync, readFileSync, writeFileSync } from 'fs'
import { join, resolve, dirname } from 'path'
import { execSync } from 'child_process'

interface FrameworkDetection {
  name: 'vite' | 'nextjs' | 'cra' | 'unknown'
  configFile: string | null
  packageManager: 'npm' | 'yarn' | 'pnpm' | 'bun'
}

const VITE_CONFIG_FILES = ['vite.config.ts', 'vite.config.js', 'vite.config.mts', 'vite.config.mjs']
const NEXT_CONFIG_FILES = ['next.config.js', 'next.config.mjs', 'next.config.ts']

function log(message: string) {
  console.log(`\x1b[36m[react-grab]\x1b[0m ${message}`)
}

function success(message: string) {
  console.log(`\x1b[32m✓\x1b[0m ${message}`)
}

function error(message: string) {
  console.error(`\x1b[31m✗\x1b[0m ${message}`)
}

function detectPackageManager(cwd: string): 'npm' | 'yarn' | 'pnpm' | 'bun' {
  if (existsSync(join(cwd, 'bun.lockb'))) return 'bun'
  if (existsSync(join(cwd, 'pnpm-lock.yaml'))) return 'pnpm'
  if (existsSync(join(cwd, 'yarn.lock'))) return 'yarn'
  return 'npm'
}

function detectFramework(cwd: string): FrameworkDetection {
  const packageManager = detectPackageManager(cwd)

  // Check for Vite
  for (const configFile of VITE_CONFIG_FILES) {
    if (existsSync(join(cwd, configFile))) {
      return { name: 'vite', configFile, packageManager }
    }
  }

  // Check for Next.js
  for (const configFile of NEXT_CONFIG_FILES) {
    if (existsSync(join(cwd, configFile))) {
      return { name: 'nextjs', configFile, packageManager }
    }
  }

  // Check package.json for framework hints
  const pkgPath = join(cwd, 'package.json')
  if (existsSync(pkgPath)) {
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'))
    const deps = { ...pkg.dependencies, ...pkg.devDependencies }

    if (deps['vite']) {
      return { name: 'vite', configFile: null, packageManager }
    }
    if (deps['next']) {
      return { name: 'nextjs', configFile: null, packageManager }
    }
    if (deps['react-scripts']) {
      return { name: 'cra', configFile: null, packageManager }
    }
  }

  return { name: 'unknown', configFile: null, packageManager }
}

function isInsideCatalyst(cwd: string): { inside: boolean; toolsPath: string | null } {
  // Walk up the directory tree looking for Catalyst markers
  let current = cwd
  const root = resolve('/')

  while (current !== root) {
    // Check for Catalyst markers
    const hasToolsReactGrab = existsSync(join(current, 'tools', 'react-grab', 'package.json'))
    const hasClaudeDir = existsSync(join(current, '.claude'))
    const hasCatalystMarker = existsSync(join(current, 'CLAUDE.md'))

    if (hasToolsReactGrab && (hasClaudeDir || hasCatalystMarker)) {
      return {
        inside: true,
        toolsPath: join(current, 'tools', 'react-grab')
      }
    }

    current = dirname(current)
  }

  return { inside: false, toolsPath: null }
}

function getRelativePath(from: string, to: string): string {
  const fromParts = from.split('/').filter(Boolean)
  const toParts = to.split('/').filter(Boolean)

  // Find common prefix
  let commonLength = 0
  while (commonLength < fromParts.length &&
         commonLength < toParts.length &&
         fromParts[commonLength] === toParts[commonLength]) {
    commonLength++
  }

  // Build relative path
  const upCount = fromParts.length - commonLength
  const downPath = toParts.slice(commonLength).join('/')

  const relativeParts = []
  for (let i = 0; i < upCount; i++) {
    relativeParts.push('..')
  }
  if (downPath) {
    relativeParts.push(downPath)
  }

  return relativeParts.join('/') || '.'
}

function addDependency(cwd: string, packageManager: string, isLocal: boolean, localPath?: string) {
  const pkgPath = join(cwd, 'package.json')
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'))

  pkg.devDependencies = pkg.devDependencies || {}

  if (isLocal && localPath) {
    const relativePath = getRelativePath(cwd, localPath)
    pkg.devDependencies['@catalyst/react-grab'] = `file:${relativePath}`
    success(`Added local dependency: file:${relativePath}`)
  } else {
    pkg.devDependencies['@catalyst/react-grab'] = 'github:{{GITHUB_USER}}/react-grab'
    success('Added GitHub dependency: github:{{GITHUB_USER}}/react-grab')
  }

  writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n')

  // Install
  log(`Installing with ${packageManager}...`)
  const installCmd = packageManager === 'npm' ? 'npm install' : `${packageManager} install`
  execSync(installCmd, { cwd, stdio: 'inherit' })
}

function configureVite(cwd: string, configFile: string | null) {
  // If no config file exists, create one
  if (!configFile) {
    configFile = 'vite.config.ts'
    const template = `import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { reactGrabVitePlugin } from '@catalyst/react-grab/vite'

export default defineConfig({
  plugins: [
    react(),
    reactGrabVitePlugin({
      projectPath: __dirname,
      debug: false,
    }),
  ],
})
`
    writeFileSync(join(cwd, configFile), template)
    success(`Created ${configFile}`)
    return
  }

  // Modify existing config
  const configPath = join(cwd, configFile)
  let content = readFileSync(configPath, 'utf-8')

  // Check if already configured
  if (content.includes('reactGrabVitePlugin') || content.includes('react-grab')) {
    log('react-grab already configured in vite config')
    return
  }

  // Add import
  const importStatement = `import { reactGrabVitePlugin } from '@catalyst/react-grab/vite'\n`

  // Find the last import line
  const lines = content.split('\n')
  let lastImportIndex = -1
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith('import ') || lines[i].startsWith('import{')) {
      lastImportIndex = i
    }
  }

  if (lastImportIndex >= 0) {
    lines.splice(lastImportIndex + 1, 0, importStatement.trim())
  } else {
    lines.unshift(importStatement.trim())
  }
  content = lines.join('\n')

  // Add plugin to plugins array
  const pluginCode = `    reactGrabVitePlugin({
      projectPath: __dirname,
      debug: false,
    }),`

  // Find plugins: [ and add after it
  const pluginsMatch = content.match(/plugins\s*:\s*\[/)
  if (pluginsMatch) {
    const insertIndex = content.indexOf(pluginsMatch[0]) + pluginsMatch[0].length
    content = content.slice(0, insertIndex) + '\n' + pluginCode + content.slice(insertIndex)
  } else {
    error('Could not find plugins array in vite config. Please add manually.')
    console.log('\nAdd this to your vite.config.ts:')
    console.log('  import { reactGrabVitePlugin } from "@catalyst/react-grab/vite"')
    console.log('  // In plugins array:')
    console.log('  reactGrabVitePlugin({ projectPath: __dirname })')
    return
  }

  writeFileSync(configPath, content)
  success(`Updated ${configFile}`)
}

function configureNextJS(cwd: string) {
  error('Next.js support coming soon. For now, add manually.')
  console.log('\nFor Next.js, add to your app entry (e.g., _app.tsx or layout.tsx):')
  console.log('  import { registerReactGrabPlugin } from "@catalyst/react-grab"')
  console.log('  if (process.env.NODE_ENV === "development") {')
  console.log('    registerReactGrabPlugin()')
  console.log('  }')
}

async function main() {
  const args = process.argv.slice(2)
  const command = args[0]

  if (command !== 'init') {
    console.log('Usage: npx @catalyst/react-grab init')
    console.log('')
    console.log('Commands:')
    console.log('  init    Auto-detect framework and configure react-grab')
    process.exit(1)
  }

  const cwd = process.cwd()

  console.log('')
  log('Initializing react-grab...')
  console.log('')

  // Check for package.json
  if (!existsSync(join(cwd, 'package.json'))) {
    error('No package.json found. Run this from your project root.')
    process.exit(1)
  }

  // Detect framework
  const framework = detectFramework(cwd)
  success(`Detected framework: ${framework.name}`)
  success(`Package manager: ${framework.packageManager}`)

  // Check if inside Catalyst
  const catalyst = isInsideCatalyst(cwd)
  if (catalyst.inside) {
    success('Inside Catalyst - will use local file reference')
  } else {
    log('Outside Catalyst - will use GitHub reference')
  }

  console.log('')

  // Add dependency
  addDependency(cwd, framework.packageManager, catalyst.inside, catalyst.toolsPath || undefined)

  console.log('')

  // Configure based on framework
  switch (framework.name) {
    case 'vite':
      configureVite(cwd, framework.configFile)
      break
    case 'nextjs':
      configureNextJS(cwd)
      break
    case 'cra':
      error('Create React App support coming soon.')
      break
    default:
      error('Could not detect framework. Please configure manually.')
  }

  console.log('')
  success('react-grab initialized!')
  console.log('')
  console.log('Start your dev server and look for the cursor button in the bottom-right corner.')
  console.log('Or use Cmd+Shift+Z (Mac) / Ctrl+Shift+Z (Windows) while hovering over an element.')
  console.log('')
}

main().catch((err) => {
  error(err.message)
  process.exit(1)
})
