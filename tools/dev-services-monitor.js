#!/usr/bin/env node
/**
 * Catalyst Dev Services Idle Monitor
 *
 * Monitors activity for dev services and shuts them down after 30 minutes of inactivity.
 * Activity signals:
 * - HTTP requests to portal domains in Caddy logs (last 30 min)
 * - Active connections on dev service ports (5174, 4000, 3001)
 * - PM2 service restarts/errors
 *
 * Runs every 5 minutes. Self-terminates when dev services are stopped.
 */

const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

// Configuration
const CHECK_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
const IDLE_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const STATE_FILE = '/tmp/catalyst/dev-services-last-activity';
const CADDY_LOG = '{{CATALYST_ROOT}}/catalyst-design-system/caddy_access.log';
const DEV_SERVICES = ['plasmic-backend', 'plasmic-frontend', 'vite-portal'];
const DEV_PORTS = [5174, 3004, 3003]; // vite-portal, plasmic-backend, plasmic-frontend
const PM2_BIN = '{{HOME_DIR}}/.npm-global/bin/pm2'; // PM2 binary location

// Ensure state directory exists
function ensureStateDir() {
  const dir = path.dirname(STATE_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// Read last activity timestamp (in milliseconds)
function getLastActivity() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const timestamp = parseInt(fs.readFileSync(STATE_FILE, 'utf-8').trim());
      if (!isNaN(timestamp)) {
        // Convert from seconds to milliseconds if needed (timestamps < 10^11 are in seconds)
        // Current millisecond timestamps are 13 digits (e.g., 1762454376485)
        // Second timestamps are 10 digits (e.g., 1762454376)
        return timestamp < 100000000000 ? timestamp * 1000 : timestamp;
      }
    }
  } catch (err) {
    console.error(`Error reading state file: ${err.message}`);
  }
  return Date.now(); // Default to now if file doesn't exist
}

// Update last activity timestamp (in milliseconds)
function updateLastActivity() {
  try {
    ensureStateDir();
    fs.writeFileSync(STATE_FILE, Date.now().toString());
  } catch (err) {
    console.error(`Error writing state file: ${err.message}`);
  }
}

// Check if Caddy logs show recent activity
async function checkCaddyActivity() {
  try {
    if (!fs.existsSync(CADDY_LOG)) {
      console.log('Caddy log file not found');
      return false;
    }

    const thirtyMinAgo = Date.now() - IDLE_TIMEOUT_MS;
    const { stdout } = await execAsync(`tail -n 1000 "${CADDY_LOG}" | grep -E "studio\\.catalyst\\.local|portal\\.catalyst\\.local|catalyst\\.local" | tail -n 1`);

    if (!stdout.trim()) {
      console.log('No recent Caddy requests found');
      return false;
    }

    // Caddy logs typically start with timestamp like: 2025/01/06 15:30:45
    // Or ISO format depending on config
    const logLine = stdout.trim();
    console.log(`Found recent Caddy request: ${logLine.substring(0, 100)}...`);
    return true; // If we found ANY recent request in last 1000 lines, consider it active
  } catch (err) {
    // grep returns exit code 1 if no matches found, which throws in execAsync
    if (err.code === 1) {
      console.log('No matching Caddy requests found');
      return false;
    }
    console.error(`Error checking Caddy logs: ${err.message}`);
    return false;
  }
}

// Check if there are active connections on dev service ports
async function checkPortActivity() {
  try {
    for (const port of DEV_PORTS) {
      try {
        const { stdout } = await execAsync(`lsof -ti:${port} 2>/dev/null | wc -l`);
        const connectionCount = parseInt(stdout.trim());
        if (connectionCount > 1) { // More than just the listening socket
          console.log(`Active connections found on port ${port}`);
          return true;
        }
      } catch (err) {
        // Port not in use, continue checking others
      }
    }
    console.log('No active port connections detected');
    return false;
  } catch (err) {
    console.error(`Error checking port activity: ${err.message}`);
    return false;
  }
}

// Check PM2 status for dev services
async function getDevServicesStatus() {
  try {
    const { stdout } = await execAsync(`${PM2_BIN} jlist`);
    const processes = JSON.parse(stdout);

    const devProcesses = processes.filter(p => DEV_SERVICES.includes(p.name));

    if (devProcesses.length === 0) {
      console.log('No dev services running in PM2');
      return { running: false, statuses: [] };
    }

    const statuses = devProcesses.map(p => ({
      name: p.name,
      status: p.pm2_env.status,
      restarts: p.pm2_env.restart_time,
    }));

    const anyRunning = devProcesses.some(p =>
      p.pm2_env.status === 'online' ||
      p.pm2_env.status === 'launching' ||
      p.pm2_env.status === 'errored'
    );

    // If services are errored or restarting, consider them active (don't shut down failing services)
    const anyErrored = devProcesses.some(p => p.pm2_env.status === 'errored');

    return { running: anyRunning, statuses, anyErrored };
  } catch (err) {
    console.error(`Error checking PM2 status: ${err.message}`);
    return { running: false, statuses: [] };
  }
}

// Stop dev services via PM2
async function stopDevServices() {
  try {
    console.log('Stopping dev services due to inactivity...');
    await execAsync(`${PM2_BIN} stop ${DEV_SERVICES.join(' ')}`);
    console.log('✅ Dev services stopped');
    return true;
  } catch (err) {
    console.error(`❌ Error stopping dev services: ${err.message}`);
    return false;
  }
}

// Main monitoring loop
async function monitorActivity() {
  console.log('\n=== Dev Services Monitor Check ===');
  console.log(new Date().toISOString());

  // Check if dev services are still running
  const { running, statuses, anyErrored } = await getDevServicesStatus();

  if (!running) {
    console.log('Dev services are not running. Monitor will self-terminate.');
    process.exit(0);
  }

  console.log('Dev services status:', statuses);

  // If any services are errored, consider it active (don't shut down failing services)
  if (anyErrored) {
    console.log('⚠️  Some dev services are in error state - keeping them running for debugging');
    updateLastActivity();
    return;
  }

  // Check for activity signals
  const caddyActive = await checkCaddyActivity();
  const portActive = await checkPortActivity();

  if (caddyActive || portActive) {
    console.log('✅ Activity detected - updating timestamp');
    updateLastActivity();
    return;
  }

  // No activity - check if timeout exceeded
  const lastActivity = getLastActivity();
  const idleTime = Date.now() - lastActivity;
  const idleMinutes = Math.floor(idleTime / 60000);

  console.log(`No activity detected. Idle time: ${idleMinutes} minutes`);

  if (idleTime > IDLE_TIMEOUT_MS) {
    console.log(`⏰ Idle timeout exceeded (${idleMinutes} minutes) - shutting down dev services`);
    const stopped = await stopDevServices();
    if (stopped) {
      console.log('Monitor will self-terminate.');
      process.exit(0);
    }
  } else {
    const remainingMinutes = Math.floor((IDLE_TIMEOUT_MS - idleTime) / 60000);
    console.log(`⏳ Will shutdown in ${remainingMinutes} minutes if no activity`);
  }
}

// Initialize and start monitoring
async function main() {
  console.log('🔍 Catalyst Dev Services Monitor starting...');
  console.log(`Check interval: ${CHECK_INTERVAL_MS / 60000} minutes`);
  console.log(`Idle timeout: ${IDLE_TIMEOUT_MS / 60000} minutes`);
  console.log(`State file: ${STATE_FILE}`);

  ensureStateDir();

  // Run initial check
  await monitorActivity();

  // Schedule periodic checks
  setInterval(async () => {
    try {
      await monitorActivity();
    } catch (err) {
      console.error('Error in monitor loop:', err);
    }
  }, CHECK_INTERVAL_MS);

  console.log('✅ Monitor initialized and running');
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n👋 Monitor received SIGINT - shutting down');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n👋 Monitor received SIGTERM - shutting down');
  process.exit(0);
});

// Start the monitor
main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
