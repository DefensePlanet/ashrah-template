import path from 'node:path';
import os from 'node:os';
import fs from 'node:fs/promises';

console.log('ANTHROPIC_OAUTH_TOKEN set:', !!process.env.ANTHROPIC_OAUTH_TOKEN);
console.log('Token starts with:', process.env.ANTHROPIC_OAUTH_TOKEN?.substring(0, 20));

const AGENT_DIR = path.join(os.homedir(), '.claude');
const SESSIONS_DIR = path.join(os.homedir(), '.clawdbot', 'telegram-test-sessions');
const workingDir = '{{CATALYST_ROOT}}';

try {
  const { discoverAuthStorage, discoverModels, createAgentSession, SessionManager, SettingsManager } = await import('@mariozechner/pi-coding-agent');
  const { streamSimple } = await import('@mariozechner/pi-ai');

  console.log('\n1. Setting up auth and models...');
  const authStorage = discoverAuthStorage(AGENT_DIR);
  console.log('   Auth storage keys:', Object.keys(authStorage));

  const modelRegistry = discoverModels(authStorage, AGENT_DIR);
  const model = modelRegistry.find('anthropic', 'claude-sonnet-4-20250514');

  if (!model) throw new Error('Model not found');
  console.log('   Model:', model.provider + '/' + model.id);

  console.log('\n2. Creating session...');
  await fs.mkdir(SESSIONS_DIR, { recursive: true });
  const sessionFile = path.join(SESSIONS_DIR, 'test-' + Date.now() + '.jsonl');
  const sessionManager = SessionManager.open(sessionFile);
  const settingsManager = SettingsManager.create(workingDir, AGENT_DIR);

  const createSystemPromptOverride = (prompt) => () => prompt.trim();

  const startTime = Date.now();
  const { session } = await createAgentSession({
    cwd: workingDir,
    agentDir: AGENT_DIR,
    authStorage,
    modelRegistry,
    model,
    thinkingLevel: 'none',
    systemPrompt: createSystemPromptOverride('You are a helpful assistant. Respond very briefly.'),
    tools: [],
    customTools: [],
    sessionManager,
    settingsManager,
    skills: [],
    contextFiles: [],
  });

  session.agent.streamFn = streamSimple;
  console.log('   Session created in ' + (Date.now() - startTime) + 'ms');

  console.log('\n3. Sending test prompt...');
  const promptStart = Date.now();

  await session.prompt('What is 2+2? Reply with just the number.');

  console.log('   Response time:', (Date.now() - promptStart) + 'ms');

  const messages = session.messages;
  const lastAssistant = messages.slice().reverse().find(m => m.role === 'assistant');
  if (lastAssistant && lastAssistant.content) {
    let response = typeof lastAssistant.content === 'string'
      ? lastAssistant.content
      : lastAssistant.content.filter(c => c.type === 'text').map(c => c.text).join('');
    console.log('   Response:', response.trim());
  }

  session.dispose();
  await fs.unlink(sessionFile).catch(() => {});
  console.log('\nSUCCESS! Total time:', (Date.now() - startTime) + 'ms');

} catch (error) {
  console.error('\nERROR:', error.message);
}
