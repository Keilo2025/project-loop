'use strict';

// Install, uninstall and status. All filesystem work happens here.
//
// Two rules this module will not break:
//   1. Never overwrite a file the user wrote by hand. Adapter files (AGENTS.md,
//      cursor rules) are placed only when absent, and reported when skipped.
//   2. Never touch a /loop-project directory. That is project state and part of the
//      audit trail, not an installed artifact.

const fs = require('fs');
const path = require('path');
const { out, paint, colors } = require('./prompts');
const { resolveDestinations, SKILL_NAME } = require('./targets');

// Repository root: cli/ sits directly beneath it.
const PKG_ROOT = path.resolve(__dirname, '..');
const SKILL_SRC = path.join(PKG_ROOT, 'plugins', 'project-loop', 'skills', SKILL_NAME);
const AGENTS_SRC = path.join(PKG_ROOT, 'plugins', 'project-loop', 'agents');

function assertPayload() {
  const skillFile = path.join(SKILL_SRC, 'SKILL.md');
  if (!fs.existsSync(skillFile)) {
    throw new Error(
      'skill payload missing at ' + skillFile + '\n' +
      '  This means the package was published without its files, or you are running\n' +
      '  the CLI from outside the repository. Reinstall with: npm i -g project-loop'
    );
  }
}

function copyDir(src, dest, dry) {
  if (dry) return;
  fs.cpSync(src, dest, { recursive: true, force: true, dereference: true });
}

function rmDir(target, dry) {
  if (dry) return;
  fs.rmSync(target, { recursive: true, force: true });
}

function chmodLoopPy(skillDest, dry) {
  if (dry) return;
  const loopPy = path.join(skillDest, 'scripts', 'loop.py');
  try {
    fs.chmodSync(loopPy, 0o755);
  } catch (_) {
    // Non-fatal. loop.py is invoked as `python3 loop.py`, so the exec bit is a
    // convenience rather than a requirement.
  }
}

function installSkill(skillsDir, skillDest, label, dry) {
  if (dry) {
    out.step('would install skill -> ' + skillDest);
    return { action: 'would-install', path: skillDest };
  }
  fs.mkdirSync(skillsDir, { recursive: true });
  const replacing = fs.existsSync(skillDest);
  rmDir(skillDest, false);
  copyDir(SKILL_SRC, skillDest, false);
  chmodLoopPy(skillDest, false);
  out.ok((replacing ? 'updated' : 'installed') + ' skill ' + paint(colors.grey, '-> ' + skillDest));
  return { action: replacing ? 'updated' : 'installed', path: skillDest };
}

function installAgents(agentsDir, dry) {
  const files = fs.readdirSync(AGENTS_SRC).filter((f) => f.endsWith('.md'));
  if (dry) {
    out.step('would install ' + files.length + ' subagents -> ' + agentsDir);
    return { count: files.length, path: agentsDir };
  }
  fs.mkdirSync(agentsDir, { recursive: true });
  for (const f of files) {
    fs.copyFileSync(path.join(AGENTS_SRC, f), path.join(agentsDir, f));
  }
  out.ok(files.length + ' subagents ' + paint(colors.grey, '-> ' + agentsDir));
  return { count: files.length, path: agentsDir };
}

function placeAdapter(adapter, dry) {
  const src = path.join(PKG_ROOT, adapter.from);
  if (!fs.existsSync(src)) {
    out.warn('adapter source missing: ' + adapter.from);
    return { action: 'missing' };
  }
  if (fs.existsSync(adapter.to)) {
    out.warn(adapter.label + ' already exists at ' + adapter.to + ' — not overwriting');
    out.dim('        merge by hand from: ' + adapter.from);
    return { action: 'skipped-exists' };
  }
  if (dry) {
    out.step('would place ' + adapter.label + ' -> ' + adapter.to);
    return { action: 'would-place' };
  }
  fs.mkdirSync(path.dirname(adapter.to), { recursive: true });
  fs.copyFileSync(src, adapter.to);
  out.ok(adapter.label + ' ' + paint(colors.grey, '-> ' + adapter.to));
  return { action: 'placed' };
}

function uninstallOne(dest, targetLabel, dry) {
  const d = resolveDestinations(dest.target, dest.scope, dest.projectRoot, dest.customPath);
  out.title(targetLabel);
  if (!fs.existsSync(d.skillDest)) {
    out.info('nothing installed at ' + d.skillDest);
    return { removed: false };
  }
  if (dry) {
    out.step('would remove ' + d.skillDest);
    return { removed: false, dry: true };
  }
  rmDir(d.skillDest, false);
  out.ok('removed ' + paint(colors.grey, d.skillDest));

  // Subagents are named files, so they can be removed precisely without
  // touching anything else the user keeps in that directory.
  if (d.agentsDir && fs.existsSync(d.agentsDir)) {
    const ours = fs.readdirSync(AGENTS_SRC).filter((f) => f.endsWith('.md'));
    let n = 0;
    for (const f of ours) {
      const p = path.join(d.agentsDir, f);
      if (fs.existsSync(p)) {
        fs.unlinkSync(p);
        n++;
      }
    }
    if (n) out.ok('removed ' + n + ' subagents ' + paint(colors.grey, '-> ' + d.agentsDir));
  }
  out.info('adapter files and /loop-project directories were left alone');
  return { removed: true };
}

// ---------------------------------------------------------------- public

function runInstall(plan) {
  assertPayload();
  const { targets, scope, projectRoot, customPath, dry } = plan;
  const results = [];

  for (const targetId of targets) {
    const d = resolveDestinations(targetId, scope, projectRoot, customPath);
    out.title(d.target.label + paint(colors.grey, '  (' + scope + ' scope)'));

    const skill = installSkill(d.skillsDir, d.skillDest, d.target.label, dry);
    let agents = null;
    if (d.agentsDir) agents = installAgents(d.agentsDir, dry);

    const adapters = d.adapters.map((a) => placeAdapter(a, dry));

    const notes = d.target.notes || {};
    const note = notes[scope] || notes.both;
    if (note) out.info(note);

    results.push({ target: targetId, scope, skill, agents, adapters });
  }
  return results;
}

function runUninstall(plan) {
  const { targets, scope, projectRoot, customPath, dry } = plan;
  const results = [];
  for (const targetId of targets) {
    const d = resolveDestinations(targetId, scope, projectRoot, customPath);
    results.push(
      uninstallOne({ target: targetId, scope, projectRoot, customPath }, d.target.label, dry)
    );
  }
  return results;
}

// Where is it installed, across every target and both scopes?
function scanInstalls(projectRoot, customPath) {
  const { ALL_TARGET_IDS } = require('./targets');
  const found = [];
  for (const targetId of ALL_TARGET_IDS) {
    // The generic target has no known path of its own. Scanning it without an
    // explicit --path would just re-report whatever the fallback happens to be
    // (Codex's directory), inventing an install that does not exist.
    const { TARGETS } = require('./targets');
    if (TARGETS[targetId].needsCustomPath && !customPath) continue;

    for (const scope of ['user', 'project']) {
      let d;
      try {
        d = resolveDestinations(targetId, scope, projectRoot, customPath);
      } catch (_) {
        continue;
      }
      if (!d.skillDest) continue;
      // Two targets can legitimately resolve to the same directory. Report once.
      if (found.some((f) => f.path === d.skillDest)) continue;
      const skillMd = path.join(d.skillDest, 'SKILL.md');
      if (fs.existsSync(skillMd)) {
        let agentCount = 0;
        if (d.agentsDir && fs.existsSync(d.agentsDir)) {
          const ours = fs.readdirSync(AGENTS_SRC).filter((f) => f.endsWith('.md'));
          agentCount = ours.filter((f) => fs.existsSync(path.join(d.agentsDir, f))).length;
        }
        found.push({
          target: targetId,
          label: d.target.label,
          scope,
          path: d.skillDest,
          agents: agentCount,
          mtime: fs.statSync(skillMd).mtime,
        });
      }
    }
  }
  return found;
}

module.exports = { runInstall, runUninstall, scanInstalls, PKG_ROOT, SKILL_SRC, AGENTS_SRC, assertPayload };
