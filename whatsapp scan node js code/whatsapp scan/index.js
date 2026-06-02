require('dotenv').config();

const fs = require('fs');
const os = require('os');
const path = require('path');
const express = require('express');
const cors = require('cors');
const qrcode = require('qrcode');
const pino = require('pino');
const {
  default: makeWASocket,
  DisconnectReason,
  Browsers,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} = require('@whiskeysockets/baileys');

const app = express();
app.use(cors());
app.use(express.json({ limit: '1mb' }));

const PORT = Number(process.env.PORT || 3001);
const API_KEY = process.env.WHATSAPP_SCAN_API_KEY || '';
const DEFAULT_COUNTRY_CODE = process.env.DEFAULT_COUNTRY_CODE || '91';
const SESSION_NAME = process.env.SESSION_NAME || 'autoans-session';
const SESSION_BASE_DIR =
  process.env.SESSION_BASE_DIR || path.join(__dirname, '.baileys_auth');
const SESSION_DIR = path.join(SESSION_BASE_DIR, SESSION_NAME);
const INSTANCE_LOCK_FILE = path.join(SESSION_BASE_DIR, `${SESSION_NAME}.lock.json`);
const LOGGED_OUT_GRACE_RETRIES = Math.max(0, Number(process.env.LOGGED_OUT_GRACE_RETRIES || 2));
const STUCK_RESTART_AFTER_MS = Math.max(60000, Number(process.env.STUCK_RESTART_AFTER_MS || 180000));
const WATCHDOG_INTERVAL_MS = Math.max(10000, Number(process.env.WATCHDOG_INTERVAL_MS || 30000));
const INSTANCE_LOCK_STALE_MS = Math.max(
  30000,
  Number(process.env.INSTANCE_LOCK_STALE_MS || 120000)
);
const INSTANCE_LOCK_REFRESH_MS = Math.max(
  10000,
  Number(process.env.INSTANCE_LOCK_REFRESH_MS || 15000)
);
const CONFLICT_RECONNECT_DELAY_MS = Math.max(
  3000,
  Number(process.env.CONFLICT_RECONNECT_DELAY_MS || 15000)
);
const NORMAL_RECONNECT_DELAY_MS = Math.max(
  2000,
  Number(process.env.NORMAL_RECONNECT_DELAY_MS || 5000)
);
const STARTUP_RECONNECT_DELAY_MS = Math.max(
  2000,
  Number(process.env.STARTUP_RECONNECT_DELAY_MS || 7000)
);
const PRESERVE_SESSION_ON_CONFLICT = String(
  process.env.PRESERVE_SESSION_ON_CONFLICT || 'true'
).toLowerCase() !== 'false';
const PRESERVE_SESSION_ON_LOGGED_OUT = String(
  process.env.PRESERVE_SESSION_ON_LOGGED_OUT || 'true'
).toLowerCase() !== 'false';

let sock = null;
let latestQr = null;
let latestQrAt = null;
let clientInfo = null;
let currentState = 'starting';
let isReady = false;
let lastError = null;
let bootDiagnostics = null;
let startPromise = null;
let reconnectTimer = null;
let fatalErrorWindowStartedAt = 0;
let fatalErrorCount = 0;
let manualInterventionRequired = false;
let reconnectAttempt = 0;
let activeSocketGeneration = 0;
let loggedOutRetryCount = 0;
let explicitLogoutRequested = false;
let lastDisconnectCode = null;
let lastDisconnectReason = null;
let lastDisconnectAt = null;
let autoRecoveryRestartCount = 0;
let lastReadyAt = null;
let queuedForceRestart = false;
let queuedRestartReason = null;
let ownsInstanceLock = false;
let lockRefreshTimer = null;
let lastStartReason = 'startup';

function collectBootDiagnostics() {
  return {
    nodeEnv: process.env.NODE_ENV || null,
    platform: process.platform,
    arch: process.arch,
    nodeVersion: process.version,
    sessionDir: SESSION_DIR,
    sessionDirExists: fs.existsSync(SESSION_DIR),
    sessionBaseDir: SESSION_BASE_DIR,
    sessionBaseDirExists: fs.existsSync(SESSION_BASE_DIR),
    instanceLockFile: INSTANCE_LOCK_FILE,
    instanceLockExists: fs.existsSync(INSTANCE_LOCK_FILE),
    apiKeyConfigured: Boolean(API_KEY),
    apiKeyLength: API_KEY ? API_KEY.length : 0,
    engine: 'baileys',
    preserveSessionOnConflict: PRESERVE_SESSION_ON_CONFLICT,
    preserveSessionOnLoggedOut: PRESERVE_SESSION_ON_LOGGED_OUT,
  };
}

function logBootDiagnostics() {
  bootDiagnostics = collectBootDiagnostics();
  console.log('=== WhatsApp Scan Boot Diagnostics ===');
  console.log(JSON.stringify(bootDiagnostics));
  console.log('=====================================');
}

function authMiddleware(req, res, next) {
  if (!API_KEY) {
    return res.status(500).json({
      success: false,
      message: 'Server API key is not configured',
    });
  }

  if (req.headers['x-api-key'] !== API_KEY) {
    return res.status(401).json({
      success: false,
      message: 'Unauthorized',
    });
  }

  next();
}

function normalizePhoneToJid(phone) {
  let value = String(phone || '').trim();
  if (!value) {
    throw new Error('Phone is required');
  }

  if (value.endsWith('@s.whatsapp.net')) {
    return value;
  }

  value = value.replace(/[^\d]/g, '');
  if (!value) {
    throw new Error('Invalid phone number');
  }

  if (!value.startsWith(DEFAULT_COUNTRY_CODE)) {
    value = `${DEFAULT_COUNTRY_CODE}${value}`;
  }

  return `${value}@s.whatsapp.net`;
}

function extractDisconnectCode(lastDisconnect) {
  return (
    lastDisconnect?.error?.output?.statusCode ||
    lastDisconnect?.error?.data?.statusCode ||
    lastDisconnect?.error?.statusCode ||
    null
  );
}

async function clearSessionFiles() {
  try {
    fs.rmSync(SESSION_DIR, { recursive: true, force: true });
  } catch (err) {
    console.error('Failed to clear session files:', err?.stack || err);
  }
}

function ensureSessionDirExists() {
  try {
    fs.mkdirSync(SESSION_BASE_DIR, { recursive: true });
    fs.mkdirSync(SESSION_DIR, { recursive: true });
  } catch (err) {
    console.error('Failed to create session directory:', err?.stack || err);
  }
}

function buildInstanceLockPayload() {
  return JSON.stringify(
    {
      pid: process.pid,
      hostname: os.hostname(),
      updatedAt: Date.now(),
      sessionName: SESSION_NAME,
    },
    null,
    2
  );
}

function readInstanceLockFile() {
  try {
    if (!fs.existsSync(INSTANCE_LOCK_FILE)) {
      return null;
    }

    const raw = fs.readFileSync(INSTANCE_LOCK_FILE, 'utf8');
    if (!raw.trim()) {
      return null;
    }

    return JSON.parse(raw);
  } catch (err) {
    console.warn('Failed to read instance lock file:', err?.message || err);
    return null;
  }
}

function isPidAlive(pid) {
  if (!pid || typeof pid !== 'number') {
    return false;
  }

  if (pid === process.pid) {
    return true;
  }

  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err?.code === 'EPERM';
  }
}

function stopLockRefreshTimer() {
  if (lockRefreshTimer) {
    clearInterval(lockRefreshTimer);
    lockRefreshTimer = null;
  }
}

function refreshInstanceLock() {
  if (!ownsInstanceLock) {
    return;
  }

  try {
    fs.writeFileSync(INSTANCE_LOCK_FILE, buildInstanceLockPayload(), 'utf8');
  } catch (err) {
    console.error('Failed to refresh instance lock:', err?.stack || err);
  }
}

function startLockRefreshTimer() {
  stopLockRefreshTimer();
  lockRefreshTimer = setInterval(() => {
    refreshInstanceLock();
  }, INSTANCE_LOCK_REFRESH_MS);
}

function releaseInstanceLock() {
  if (!ownsInstanceLock) {
    return;
  }

  stopLockRefreshTimer();

  try {
    const currentLock = readInstanceLockFile();
    if (!currentLock || currentLock.pid === process.pid) {
      fs.rmSync(INSTANCE_LOCK_FILE, { force: true });
    }
  } catch (err) {
    console.warn('Failed to release instance lock:', err?.message || err);
  } finally {
    ownsInstanceLock = false;
  }
}

function tryCreateInstanceLock() {
  const fileHandle = fs.openSync(INSTANCE_LOCK_FILE, 'wx');
  fs.writeFileSync(fileHandle, buildInstanceLockPayload(), 'utf8');
  fs.closeSync(fileHandle);
}

function acquireInstanceLock() {
  ensureSessionDirExists();

  if (ownsInstanceLock) {
    refreshInstanceLock();
    return true;
  }

  try {
    tryCreateInstanceLock();
    ownsInstanceLock = true;
    startLockRefreshTimer();
    return true;
  } catch (err) {
    if (err?.code !== 'EEXIST') {
      console.error('Failed to create instance lock:', err?.stack || err);
      return false;
    }
  }

  const existingLock = readInstanceLockFile();
  const lockUpdatedAt = existingLock?.updatedAt || 0;
  const isStale = !lockUpdatedAt || Date.now() - lockUpdatedAt > INSTANCE_LOCK_STALE_MS;
  const ownerAlive = isPidAlive(existingLock?.pid);

  if (!existingLock || isStale || !ownerAlive) {
    try {
      fs.rmSync(INSTANCE_LOCK_FILE, { force: true });
      tryCreateInstanceLock();
      ownsInstanceLock = true;
      startLockRefreshTimer();
      return true;
    } catch (retryErr) {
      console.error('Failed to recover stale instance lock:', retryErr?.stack || retryErr);
      return false;
    }
  }

  return false;
}

function clearReconnectTimer() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function isActiveSocketGeneration(generation) {
  return generation === activeSocketGeneration;
}

function resetFatalErrorWindowIfNeeded() {
  const now = Date.now();
  const windowMs = 5 * 60 * 1000;

  if (!fatalErrorWindowStartedAt || now - fatalErrorWindowStartedAt > windowMs) {
    fatalErrorWindowStartedAt = now;
    fatalErrorCount = 0;
  }
}

function clearFatalErrorState() {
  fatalErrorWindowStartedAt = 0;
  fatalErrorCount = 0;
  manualInterventionRequired = false;
}

function registerFatalSessionIssue(reason) {
  resetFatalErrorWindowIfNeeded();
  fatalErrorCount += 1;

  if (fatalErrorCount >= 3) {
    manualInterventionRequired = true;
    currentState = 'manual_fix_required';
    clientInfo = null;
    lastError =
      'Repeated WhatsApp session conflicts detected. Service will keep retrying automatically. If this persists, remove old linked devices and scan again.';
    console.error(
      `[${new Date().toISOString()}] Manual intervention required after repeated fatal session errors: ${reason}`
    );
  }

  return true;
}

function scheduleReconnect(delayMs = 3000) {
  clearReconnectTimer();
  reconnectAttempt += 1;
  const resolvedDelayMs =
    delayMs ||
    Math.min(30000, reconnectAttempt <= 1 ? 3000 : reconnectAttempt <= 3 ? 7000 : 15000);

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    startSocket(true, 'scheduled_reconnect').catch((err) => {
      console.error('Reconnect failed:', err?.stack || err);
    });
  }, resolvedDelayMs);
}

async function closeCurrentSocket(reason = 'restart') {
  if (!sock) {
    return;
  }

  const socketToClose = sock;
  sock = null;

  try {
    socketToClose.ev?.removeAllListeners?.('connection.update');
    socketToClose.ev?.removeAllListeners?.('creds.update');
    socketToClose.ev?.removeAllListeners?.('messages.upsert');
  } catch (err) {
    console.warn('Failed removing socket listeners:', err?.message || err);
  }

  try {
    socketToClose.ws?.close?.();
  } catch (err) {
    console.warn(`Failed closing websocket during ${reason}:`, err?.message || err);
  }

  try {
    await Promise.race([
      Promise.resolve(socketToClose.end?.(undefined)),
      new Promise((resolve) => setTimeout(resolve, 1500)),
    ]);
  } catch (err) {
    console.warn(`Failed ending socket during ${reason}:`, err?.message || err);
  }

  await new Promise((resolve) => setTimeout(resolve, 1200));
}

async function startSocket(forceRestart = false, reason = 'unspecified') {
  if (startPromise) {
    if (forceRestart) {
      queuedForceRestart = true;
      queuedRestartReason = reason;
    }

    return startPromise;
  }

  lastStartReason = reason;
  startPromise = (async () => {
    const generation = ++activeSocketGeneration;

    if (currentState !== 'reconnecting') {
      currentState = 'starting';
    }
    isReady = false;
    lastError = null;
    latestQr = null;
    latestQrAt = null;
    clearReconnectTimer();

    if (!acquireInstanceLock()) {
      currentState = 'standby';
      clientInfo = null;
      lastError =
        'Another AutoAns scanner process is active for this session. Waiting for primary instance.';
      lastDisconnectReason = lastError;
      lastDisconnectAt = Date.now();
      scheduleReconnect(Math.max(CONFLICT_RECONNECT_DELAY_MS, 20000));
      return;
    }

    if (forceRestart && sock) {
      await closeCurrentSocket(reason);
    }

    ensureSessionDirExists();
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
    let version;

    try {
      const versionInfo = await fetchLatestBaileysVersion();
      version = versionInfo.version;
    } catch (err) {
      console.warn('Failed to fetch latest Baileys version, using built-in default:', err?.message || err);
    }

    sock = makeWASocket({
      auth: state,
      version,
      browser: Browsers.ubuntu('Chrome'),
      logger: pino({ level: 'silent' }),
      printQRInTerminal: false,
      markOnlineOnConnect: false,
      syncFullHistory: false,
      connectTimeoutMs: 60000,
      defaultQueryTimeoutMs: 60000,
      keepAliveIntervalMs: 30000,
      retryRequestDelayMs: 250,
    });

    sock.ev.on('creds.update', (...args) => {
      if (!isActiveSocketGeneration(generation)) {
        return;
      }

      Promise.resolve(saveCreds(...args)).catch((err) => {
        console.error('Failed to save credentials:', err?.stack || err);
      });
    });

    sock.ev.on('connection.update', async (update) => {
      if (!isActiveSocketGeneration(generation)) {
        return;
      }

      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        latestQr = qr;
        latestQrAt = new Date().toISOString();
        currentState = 'qr';
        isReady = false;
        lastError = null;
        console.log(`[${new Date().toISOString()}] QR generated`);
      }

      if (connection === 'connecting') {
        if (currentState !== 'reconnecting') {
          currentState = 'starting';
        }
      }

      if (connection === 'open') {
        clearReconnectTimer();
        clearFatalErrorState();
        reconnectAttempt = 0;
        loggedOutRetryCount = 0;
        explicitLogoutRequested = false;
        isReady = true;
        currentState = 'ready';
        latestQr = null;
        latestQrAt = null;
        lastError = null;
        lastDisconnectCode = null;
        lastDisconnectReason = null;
        lastDisconnectAt = null;
        lastReadyAt = Date.now();
        clientInfo = {
          number: sock?.user?.id ? String(sock.user.id).split(':')[0].split('@')[0] : null,
        };
        console.log(`[${new Date().toISOString()}] WhatsApp is ready`);
      }

      if (connection === 'close') {
        const disconnectCode = extractDisconnectCode(lastDisconnect);
        const disconnectMessage = lastDisconnect?.error?.message || 'Disconnected';
        const hadStableConnection = isReady || currentState === 'ready';
        const wasExplicitLogout = explicitLogoutRequested;

        explicitLogoutRequested = false;

        isReady = false;
        latestQr = null;
        latestQrAt = null;
        lastDisconnectCode = disconnectCode;
        lastDisconnectReason = disconnectMessage;
        lastDisconnectAt = Date.now();

        if (disconnectCode === DisconnectReason.loggedOut) {
          clientInfo = null;

          if (!wasExplicitLogout && loggedOutRetryCount < LOGGED_OUT_GRACE_RETRIES) {
            loggedOutRetryCount += 1;
            currentState = 'reconnecting';
            lastError = `Session dropped (${disconnectMessage}). Recovering automatically (${loggedOutRetryCount}/${LOGGED_OUT_GRACE_RETRIES}).`;
            console.warn(
              `[${new Date().toISOString()}] Logged out event received, trying graceful recover (${loggedOutRetryCount}/${LOGGED_OUT_GRACE_RETRIES})`
            );
            scheduleReconnect(STARTUP_RECONNECT_DELAY_MS);
            return;
          }

          loggedOutRetryCount = 0;
          currentState = PRESERVE_SESSION_ON_LOGGED_OUT ? 'reconnecting' : 'logged_out';
          lastError = PRESERVE_SESSION_ON_LOGGED_OUT
            ? `Logged out event received (${disconnectMessage}). Keeping saved session and retrying.`
            : 'WhatsApp session logged out. Scan again.';
          console.warn(
            `[${new Date().toISOString()}] Logged out detected${PRESERVE_SESSION_ON_LOGGED_OUT ? ', preserving session and retrying' : ', clearing saved session'}`
          );
          if (!PRESERVE_SESSION_ON_LOGGED_OUT) {
            await clearSessionFiles();
          }
          registerFatalSessionIssue(`logged out: ${disconnectMessage}`);
          scheduleReconnect(CONFLICT_RECONNECT_DELAY_MS);
          return;
        }

        if (/conflict/i.test(disconnectMessage)) {
          loggedOutRetryCount = 0;
          currentState = 'conflict';
          clientInfo = null;
          lastError = PRESERVE_SESSION_ON_CONFLICT
            ? 'WhatsApp session conflict detected. Keeping saved session and retrying automatically.'
            : 'WhatsApp session conflict detected. Stop any other scanner or linked session using this number, then scan again.';
          console.warn(
            `[${new Date().toISOString()}] Conflict detected${PRESERVE_SESSION_ON_CONFLICT ? ', preserving saved session' : ', clearing saved session'}`
          );
          if (!PRESERVE_SESSION_ON_CONFLICT) {
            await clearSessionFiles();
          }
          registerFatalSessionIssue(`conflict: ${disconnectMessage}`);
          scheduleReconnect(CONFLICT_RECONNECT_DELAY_MS);
          return;
        }

        loggedOutRetryCount = 0;

        if (hadStableConnection) {
          currentState = 'reconnecting';
          lastError = `Temporary connection drop: ${disconnectMessage}`;
          console.warn(`[${new Date().toISOString()}] Reconnecting: ${disconnectMessage}`);
        } else {
          currentState = 'disconnected';
          lastError = disconnectMessage;
          clientInfo = null;
          console.warn(`[${new Date().toISOString()}] Disconnected: ${disconnectMessage}`);
        }

        scheduleReconnect(hadStableConnection ? NORMAL_RECONNECT_DELAY_MS : STARTUP_RECONNECT_DELAY_MS);
      }
    });
  })()
    .catch((err) => {
      currentState = 'init_error';
      isReady = false;
      lastError = err?.message || String(err);
      lastDisconnectReason = err?.message || String(err);
      lastDisconnectAt = Date.now();
      console.error('Client initialization error:', err?.stack || err);
    })
    .finally(() => {
      startPromise = null;

      if (queuedForceRestart) {
        const nextReason = queuedRestartReason || 'queued_restart';
        queuedForceRestart = false;
        queuedRestartReason = null;
        startSocket(true, nextReason).catch((err) => {
          console.error('Queued restart failed:', err?.stack || err);
        });
      }
    });

  return startPromise;
}

process.on('uncaughtException', (err) => {
  console.error('UNCAUGHT_EXCEPTION:', err?.stack || err);
});

process.on('unhandledRejection', (reason) => {
  console.error('UNHANDLED_REJECTION:', reason);
});

process.on('exit', () => {
  releaseInstanceLock();
});

process.on('SIGINT', () => {
  releaseInstanceLock();
  process.exit(0);
});

process.on('SIGTERM', () => {
  releaseInstanceLock();
  process.exit(0);
});

setInterval(() => {
  if (isReady || startPromise || reconnectTimer) {
    return;
  }

  if (!lastDisconnectAt) {
    return;
  }

  const offlineForMs = Date.now() - lastDisconnectAt;
  if (offlineForMs < STUCK_RESTART_AFTER_MS) {
    return;
  }

  autoRecoveryRestartCount += 1;
  console.warn(
    `[${new Date().toISOString()}] Watchdog restart #${autoRecoveryRestartCount}; state=${currentState}; offlineForMs=${offlineForMs}`
  );

  startSocket(true, 'watchdog_restart').catch((err) => {
    console.error('Watchdog restart failed:', err?.stack || err);
  });
}, WATCHDOG_INTERVAL_MS);

logBootDiagnostics();
ensureSessionDirExists();
startSocket(false, 'initial_start').catch((err) => {
  console.error('Initial socket start failed:', err?.stack || err);
});

app.get('/health', (req, res) => {
  res.json({
    success: true,
    service: 'autoans-whatsapp-scan',
    state: currentState,
    connected: isReady,
    engine: 'baileys',
    lastReadyAt: lastReadyAt ? new Date(lastReadyAt).toISOString() : null,
  });
});

app.get('/heartbeat', (req, res) => {
  res.json({
    success: true,
    state: currentState,
    connected: isReady,
    timestamp: new Date().toISOString(),
  });
});

app.get('/', (req, res) => {
  res.status(200).json({
    success: true,
    message: 'AutoAns WhatsApp scan server is running',
    engine: 'baileys',
    endpoints: {
      health: '/health',
      status: '/status (requires x-api-key)',
      qr: '/qr (requires x-api-key)',
      restart: '/restart (requires x-api-key)',
    },
  });
});

app.get('/status', authMiddleware, (req, res) => {
  res.json({
    success: true,
    connected: isReady,
    state: currentState,
    number: clientInfo?.number || null,
    platform: null,
    lastError,
    lastDisconnect: {
      code: lastDisconnectCode,
      reason: lastDisconnectReason,
      at: lastDisconnectAt ? new Date(lastDisconnectAt).toISOString() : null,
    },
    reconnectAttempt,
    fatalErrorCount,
    autoRecoveryRestartCount,
    ownsInstanceLock,
    lastStartReason,
    policy: {
      loggedOutGraceRetries: LOGGED_OUT_GRACE_RETRIES,
      stuckRestartAfterMs: STUCK_RESTART_AFTER_MS,
      watchdogIntervalMs: WATCHDOG_INTERVAL_MS,
      instanceLockStaleMs: INSTANCE_LOCK_STALE_MS,
      instanceLockRefreshMs: INSTANCE_LOCK_REFRESH_MS,
      conflictReconnectDelayMs: CONFLICT_RECONNECT_DELAY_MS,
      normalReconnectDelayMs: NORMAL_RECONNECT_DELAY_MS,
      startupReconnectDelayMs: STARTUP_RECONNECT_DELAY_MS,
      preserveSessionOnConflict: PRESERVE_SESSION_ON_CONFLICT,
      preserveSessionOnLoggedOut: PRESERVE_SESSION_ON_LOGGED_OUT,
    },
    diagnostics: bootDiagnostics,
  });
});

app.get('/qr', authMiddleware, async (req, res) => {
  if (isReady) {
    return res.json({
      success: true,
      connected: true,
      message: 'Already connected. QR is not required.',
      qrImageDataUrl: null,
    });
  }

  if (!latestQr) {
    return res.status(404).json({
      success: false,
      connected: false,
      state: currentState,
      lastError,
      message: 'QR not available yet. Please retry.',
      qrImageDataUrl: null,
    });
  }

  try {
    const qrImageDataUrl = await qrcode.toDataURL(latestQr, { margin: 2, width: 320 });
    return res.json({
      success: true,
      connected: false,
      state: currentState,
      generatedAt: latestQrAt,
      qrImageDataUrl,
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      message: `Failed to render QR: ${err.message}`,
    });
  }
});

app.post('/send', authMiddleware, async (req, res) => {
  const { phone, message } = req.body || {};

  if (!phone || !message) {
    return res.status(422).json({
      success: false,
      message: 'phone and message are required',
    });
  }

  if (!isReady || !sock) {
    return res.status(409).json({
      success: false,
      message: 'WhatsApp is not connected. Scan QR first.',
    });
  }

  try {
    const jid = normalizePhoneToJid(phone);
    await sock.sendMessage(jid, { text: String(message) });

    return res.json({
      success: true,
      message: 'Message sent',
      data: {
        to: jid,
      },
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      message: `Failed to send message: ${err.message}`,
    });
  }
});

app.post('/logout', authMiddleware, async (req, res) => {
  try {
    clearFatalErrorState();
    loggedOutRetryCount = 0;
    explicitLogoutRequested = true;

    if (sock) {
      await sock.logout();
    }

    await clearSessionFiles();
    await startSocket(true, 'manual_logout');

    return res.json({
      success: true,
      message: 'Logged out and reinitialized. Scan QR again.',
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      message: `Logout failed: ${err.message}`,
    });
  }
});

app.post('/restart', authMiddleware, async (req, res) => {
  try {
    clearFatalErrorState();
    loggedOutRetryCount = 0;
    explicitLogoutRequested = false;
    autoRecoveryRestartCount += 1;

    await startSocket(true, 'manual_restart');

    return res.json({
      success: true,
      message: 'Restart requested successfully.',
      state: currentState,
      connected: isReady,
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      message: `Restart failed: ${err.message}`,
    });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`WhatsApp scan service running on port ${PORT}`);
});
