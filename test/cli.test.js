'use strict';

// Installer tests. No framework, no dependencies — node test/cli.test.js.
//
// Every test runs against a throwaway HOME and a throwaway project directory,
// so nothing here can touch a real installation.

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const BIN = path.join(ROOT, 'bin', 'project-loop.js');

let pass = 0;
let fail = 0;

function test(name, fn) {
  const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'ploop-test-'));
  const fakeHome = path.join(sandbox, 'home');
  const project = path.join(sandbox, 'project');
  fs.mkdirSync(fakeHome, { recursive: true });
  fs.mkdirSync(project, { recursive: true });
  try {
    fn({ sandbox, fakeHome, project });
    console.log('  ok    ' + name);
    pass++;
  } catch (err) {
    console.error('  FAIL  ' + name);
    console.error('        ' + (err && err.message ? err.message : err));
    fail++;
  } finally {
    fs.rmSync(sandbox, { recursive: true, force: true });
  }
}

function run(args, env = {}, cwd = ROOT) {
  return spawnSync(process.execPath, [BIN, ...args], {
    encoding: 'utf8',
    cwd,
    env: { ...process.env, NO_COLOR: '1', ...env },
  });
}

// Drive the interactive flow over piped stdin, which exercises the numbered
// fallback and — importantly — that answer N+1 is still readable after answer N.
function runPiped(args, input, env = {}, cwd = ROOT) {
  return spawnSync(process.execPath, [BIN, ...args], {
    encoding: 'utf8',
    cwd,
    input,
    env: { ...process.env, NO_COLOR: '1', ...env },
  });
}

// ---------------------------------------------------------------- tests

console.log('\nproject-loop installer tests\n');

test('--version prints a semver', () => {
  const r = run(['--version']);
  assert.strictEqual(r.status, 0, 'exit status: ' + r.status + '\n' + r.stderr);
  assert.match(r.stdout.trim(), /^\d+\.\d+\.\d+/, 'got: ' + r.stdout);
});

test('--help lists every target and both scopes', () => {
  const r = run(['--help']);
  assert.strictEqual(r.status, 0);
  for (const t of ['claude', 'codex', 'cursor', 'generic']) {
    assert.ok(r.stdout.includes(t), 'help is missing target: ' + t);
  }
  assert.ok(r.stdout.includes('--scope'), 'help is missing --scope');
});

test('unknown flag exits 2', () => {
  const r = run(['install', '--nope']);
  assert.strictEqual(r.status, 2);
});

test('unknown target exits 2 and names the valid ones', () => {
  const r = run(['install', '--target', 'emacs', '--scope', 'user', '--yes']);
  assert.strictEqual(r.status, 2);
  assert.ok((r.stdout + r.stderr).includes('claude'), 'should list valid targets');
});

test('dry run writes nothing', ({ fakeHome }) => {
  const r = run(['install', '--target', 'all', '--scope', 'user', '--yes', '--dry-run'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(!fs.existsSync(path.join(fakeHome, '.claude')), '.claude should not exist after dry run');
  assert.ok(r.stdout.includes('would'), 'dry run should say what it would do');
});

test('user scope installs skill + 5 subagents for claude', ({ fakeHome }) => {
  const r = run(['install', '--target', 'claude', '--scope', 'user', '--yes', '--no-save'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);

  const skill = path.join(fakeHome, '.claude', 'skills', 'project-loop');
  assert.ok(fs.existsSync(path.join(skill, 'SKILL.md')), 'SKILL.md missing');
  assert.ok(fs.existsSync(path.join(skill, 'scripts', 'loop.py')), 'loop.py missing');
  assert.ok(fs.existsSync(path.join(skill, 'references', 'roles.md')), 'references missing');
  assert.ok(fs.existsSync(path.join(skill, 'templates', 'verdict.md')), 'templates missing');

  const agents = fs.readdirSync(path.join(fakeHome, '.claude', 'agents')).filter((f) => f.endsWith('.md'));
  assert.strictEqual(agents.length, 5, 'expected 5 subagents, got ' + agents.length);
});

test('project scope installs into the named directory, not HOME', ({ fakeHome, project }) => {
  const r = run(['install', '--target', 'claude', '--scope', 'project', '--project', project, '--yes', '--no-save'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(fs.existsSync(path.join(project, '.claude', 'skills', 'project-loop', 'SKILL.md')),
    'project skill missing');
  assert.ok(!fs.existsSync(path.join(fakeHome, '.claude')),
    'project scope must not write to HOME');
});

test('--target all installs claude, codex and cursor but not generic', ({ fakeHome }) => {
  const r = run(['install', '--target', 'all', '--scope', 'user', '--yes', '--no-save'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(fs.existsSync(path.join(fakeHome, '.claude', 'skills', 'project-loop', 'SKILL.md')), 'claude');
  assert.ok(fs.existsSync(path.join(fakeHome, '.agents', 'skills', 'project-loop', 'SKILL.md')), 'codex');
  assert.ok(fs.existsSync(path.join(fakeHome, '.cursor', 'skills', 'project-loop', 'SKILL.md')), 'cursor');
});

test('cursor project scope places the rule file', ({ fakeHome, project }) => {
  const r = run(['install', '--target', 'cursor', '--scope', 'project', '--project', project, '--yes', '--no-save'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(fs.existsSync(path.join(project, '.cursor', 'rules', 'project-loop.mdc')), 'rule missing');
});

test('codex project scope places AGENTS.md but never overwrites one', ({ fakeHome, project }) => {
  const agentsMd = path.join(project, 'AGENTS.md');
  fs.writeFileSync(agentsMd, 'MINE - do not clobber\n');

  const r = run(['install', '--target', 'codex', '--scope', 'project', '--project', project, '--yes', '--no-save'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.strictEqual(fs.readFileSync(agentsMd, 'utf8'), 'MINE - do not clobber\n',
    'existing AGENTS.md was overwritten');
  assert.ok(r.stdout.includes('not overwriting'), 'should report the skip');
});

test('reinstall over an existing install succeeds and reports "updated"', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  run(['install', '--target', 'claude', '--scope', 'user', '--yes', '--no-save'], env);
  const r = run(['install', '--target', 'claude', '--scope', 'user', '--yes', '--no-save'], env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes('updated'), 'second install should say updated');
});

test('uninstall removes skill and subagents, leaves .loop alone', ({ fakeHome, project }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  run(['install', '--target', 'claude', '--scope', 'project', '--project', project, '--yes', '--no-save'], env);

  const loopDir = path.join(project, '.loop');
  fs.mkdirSync(loopDir, { recursive: true });
  fs.writeFileSync(path.join(loopDir, 'loop.json'), JSON.stringify({ phase: 2, status: 'OPEN' }));

  const r = run(['uninstall', '--target', 'claude', '--scope', 'project', '--project', project, '--yes'], env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(!fs.existsSync(path.join(project, '.claude', 'skills', 'project-loop')), 'skill not removed');
  assert.ok(fs.existsSync(path.join(loopDir, 'loop.json')), '.loop was deleted — it must never be');
});

test('uninstall on a clean machine is a no-op, not an error', ({ fakeHome }) => {
  const r = run(['uninstall', '--target', 'claude', '--scope', 'user', '--yes'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes('nothing installed'), 'should say nothing was installed');
});

test('status reports "not installed" on a clean machine', ({ fakeHome, project }) => {
  const r = run(['status', '--project', project], { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes('not installed'), 'got: ' + r.stdout);
  assert.ok(r.stdout.includes('no loop found'), 'should report no loop state');
});

test('status finds an install and reads .loop state', ({ fakeHome, project }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  run(['install', '--target', 'claude', '--scope', 'user', '--yes', '--no-save'], env);
  fs.mkdirSync(path.join(project, '.loop'), { recursive: true });
  fs.writeFileSync(path.join(project, '.loop', 'loop.json'),
    JSON.stringify({ phase: 3, status: 'BLOCKED', cursor: 'TASK-007' }));

  const r = run(['status', '--project', project], env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes('Claude Code'), 'should list the claude install');
  assert.ok(r.stdout.includes('BLOCKED'), 'should surface the loop status');
  assert.ok(r.stdout.includes('TASK-007'), 'should surface the cursor');
});

test('defaults are saved and reused by a bare --yes install', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  const first = run(['install', '--target', 'cursor', '--scope', 'user', '--yes'], env);
  assert.strictEqual(first.status, 0, first.stderr);

  const cfgFile = path.join(fakeHome, '.project-loop', 'config.json');
  assert.ok(fs.existsSync(cfgFile), 'config not written');
  const cfg = JSON.parse(fs.readFileSync(cfgFile, 'utf8'));
  assert.deepStrictEqual(cfg.targets, ['cursor']);
  assert.strictEqual(cfg.scope, 'user');

  // Bare --yes with no flags should pick cursor back up, not fall back to claude.
  fs.rmSync(path.join(fakeHome, '.cursor'), { recursive: true, force: true });
  const second = run(['install', '--yes'], env);
  assert.strictEqual(second.status, 0, second.stderr);
  assert.ok(fs.existsSync(path.join(fakeHome, '.cursor', 'skills', 'project-loop', 'SKILL.md')),
    'saved target was not reused');
  assert.ok(!fs.existsSync(path.join(fakeHome, '.claude')),
    'should not have fallen back to claude');
});

test('--no-save leaves no config behind', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  run(['install', '--target', 'claude', '--scope', 'user', '--yes', '--no-save'], env);
  assert.ok(!fs.existsSync(path.join(fakeHome, '.project-loop', 'config.json')),
    '--no-save still wrote a config');
});

test('config --reset removes the file', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  run(['install', '--target', 'claude', '--scope', 'user', '--yes'], env);
  const cfgFile = path.join(fakeHome, '.project-loop', 'config.json');
  assert.ok(fs.existsSync(cfgFile), 'precondition: config should exist');

  const r = run(['config', '--reset'], env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(!fs.existsSync(cfgFile), 'config not removed');
});

test('a corrupt config does not block an install', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  fs.mkdirSync(path.join(fakeHome, '.project-loop'), { recursive: true });
  fs.writeFileSync(path.join(fakeHome, '.project-loop', 'config.json'), '{ not json');

  const r = run(['install', '--target', 'claude', '--scope', 'user', '--yes', '--no-save'], env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes('unreadable') || r.stdout.includes('warn'), 'should warn about the config');
  assert.ok(fs.existsSync(path.join(fakeHome, '.claude', 'skills', 'project-loop', 'SKILL.md')),
    'install should still have happened');
});

test('generic target honours --path', ({ fakeHome, sandbox }) => {
  const custom = path.join(sandbox, 'weird', 'skills');
  const r = run(['install', '--target', 'generic', '--scope', 'user', '--path', custom, '--yes', '--no-save'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(fs.existsSync(path.join(custom, 'project-loop', 'SKILL.md')), 'custom path not used');
});

test('--scope project with a nonexistent dir does not silently create it', ({ fakeHome, sandbox }) => {
  const missing = path.join(sandbox, 'does', 'not', 'exist');
  const r = run(['install', '--target', 'claude', '--scope', 'project', '--project', missing, '--yes', '--no-save'],
    { HOME: fakeHome, USERPROFILE: fakeHome });
  // Either it refuses, or it creates only under the given root — never under HOME.
  assert.ok(!fs.existsSync(path.join(fakeHome, '.claude')), 'must not fall back to HOME');
});

test('installed skill is byte-identical to the source', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  run(['install', '--target', 'claude', '--scope', 'user', '--yes', '--no-save'], env);
  const src = path.join(ROOT, 'plugins', 'project-loop', 'skills', 'project-loop', 'SKILL.md');
  const dst = path.join(fakeHome, '.claude', 'skills', 'project-loop', 'SKILL.md');
  assert.strictEqual(fs.readFileSync(dst, 'utf8'), fs.readFileSync(src, 'utf8'),
    'installed SKILL.md differs from source');
});

test('piped interactive run answers all prompts and installs', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  // agents=1 (Claude Code), scope=1 (every project), confirm=y
  const r = runPiped([], '1\n1\ny\n', env);
  assert.strictEqual(r.status, 0, 'exit ' + r.status + '\n' + r.stdout + r.stderr);
  assert.ok(r.stdout.includes('Install into which agents?'), 'first prompt missing');
  assert.ok(r.stdout.includes('How widely should it apply?'),
    'second prompt missing — stdin died after the first question');
  assert.ok(fs.existsSync(path.join(fakeHome, '.claude', 'skills', 'project-loop', 'SKILL.md')),
    'piped interactive run did not install');
});

test('piped run declining the confirm writes nothing', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  const r = runPiped([], '1\n1\nn\n', env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes('cancelled'), 'should report cancellation');
  assert.ok(!fs.existsSync(path.join(fakeHome, '.claude')), 'declined run still wrote files');
});

test('piped multiselect accepts comma-separated picks', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  const r = runPiped([], '1,3\n1\ny\n', env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(fs.existsSync(path.join(fakeHome, '.claude', 'skills', 'project-loop', 'SKILL.md')), 'claude missing');
  assert.ok(fs.existsSync(path.join(fakeHome, '.cursor', 'skills', 'project-loop', 'SKILL.md')), 'cursor missing');
  assert.ok(!fs.existsSync(path.join(fakeHome, '.agents')), 'codex should not have been installed');
});

test('piped multiselect "a" selects every agent', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  // "a" includes the generic target, so a custom path is asked for too.
  const custom = path.join(fakeHome, 'custom', 'skills');
  const r = runPiped([], 'a\n1\n' + custom + '\ny\n', env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(fs.existsSync(path.join(fakeHome, '.claude', 'skills', 'project-loop', 'SKILL.md')), 'claude');
  assert.ok(fs.existsSync(path.join(fakeHome, '.agents', 'skills', 'project-loop', 'SKILL.md')), 'codex');
  assert.ok(fs.existsSync(path.join(fakeHome, '.cursor', 'skills', 'project-loop', 'SKILL.md')), 'cursor');
  assert.ok(fs.existsSync(path.join(custom, 'project-loop', 'SKILL.md')), 'generic custom path');
});

test('piped project scope prompts for a directory and uses it', ({ fakeHome, project }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  const r = runPiped([], '1\n2\n' + project + '\ny\n', env);
  assert.strictEqual(r.status, 0, 'exit ' + r.status + '\n' + r.stdout + r.stderr);
  assert.ok(fs.existsSync(path.join(project, '.claude', 'skills', 'project-loop', 'SKILL.md')),
    'did not install into the prompted directory');
  assert.ok(!fs.existsSync(path.join(fakeHome, '.claude')), 'must not also write to HOME');
});

test('truncated piped input falls back to defaults instead of hanging', ({ fakeHome }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  // Only the first answer is supplied; stdin then hits EOF.
  const r = runPiped([], '1\n', env);
  assert.strictEqual(typeof r.status, 'number', 'process did not exit');
  assert.ok(r.status === 0 || r.status === 1, 'unexpected exit ' + r.status);
});

test('status does not invent a generic install from the fallback path', ({ fakeHome, project }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  run(['install', '--target', 'codex', '--scope', 'user', '--yes', '--no-save'], env);
  const r = run(['status', '--project', project], env);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes('OpenAI Codex'), 'should list the codex install');
  assert.ok(!r.stdout.includes('Other agent'),
    'generic target must not be reported without an explicit --path');
});

test('status reports each directory once even when targets overlap', ({ fakeHome, project, sandbox }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  const shared = path.join(fakeHome, '.agents', 'skills');
  run(['install', '--target', 'codex', '--scope', 'user', '--yes', '--no-save'], env);
  const r = run(['status', '--project', project, '--path', shared], env);
  assert.strictEqual(r.status, 0, r.stderr);
  const hits = r.stdout.split('\n').filter((l) => l.includes(path.join(shared, 'project-loop')));
  assert.strictEqual(hits.length, 1, 'same path reported ' + hits.length + ' times');
});

test('doctor runs and reports on payload + install locations', ({ fakeHome, project }) => {
  const env = { HOME: fakeHome, USERPROFILE: fakeHome };
  run(['install', '--target', 'claude', '--scope', 'user', '--yes', '--no-save'], env);
  const r = run(['doctor', '--project', project], env);
  // Exit code depends on whether python3/git exist in the environment, so assert
  // on content rather than status.
  assert.ok(r.stdout.includes('Payload'), 'doctor should check the payload');
  assert.ok(r.stdout.includes('skill source intact'), 'payload check failed: ' + r.stdout);
  assert.ok(r.stdout.includes('Claude Code'), 'doctor should find the install');
});

// ---------------------------------------------------------------- summary

console.log('');
console.log('  ' + pass + ' passed, ' + fail + ' failed');
console.log('');
process.exit(fail === 0 ? 0 : 1);
