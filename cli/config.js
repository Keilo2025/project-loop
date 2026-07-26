'use strict';

// Persisted user defaults, so the second install does not re-ask the questions
// the first one already answered.
//
// This file holds preferences only. It is not loop state — loop state lives in
// each project's .loop/ directory and is deliberately never centralised.

const fs = require('fs');
const os = require('os');
const path = require('path');

const CONFIG_DIR = path.join(os.homedir(), '.project-loop');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

const DEFAULTS = {
  version: 1,
  targets: [],          // e.g. ["claude", "cursor"]
  scope: null,          // "user" | "project"
  customSkillPath: null, // for the generic target
  installs: [],         // audit trail: {at, targets, scope, root}
};

function read() {
  try {
    const raw = fs.readFileSync(CONFIG_FILE, 'utf8');
    const parsed = JSON.parse(raw);
    return { ...DEFAULTS, ...parsed };
  } catch (err) {
    if (err.code === 'ENOENT') return { ...DEFAULTS };
    // A corrupt config should never block an install. Warn and carry on with
    // defaults rather than making the user hand-edit JSON to recover.
    return { ...DEFAULTS, _corrupt: true, _error: err.message };
  }
}

function write(cfg) {
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  const { _corrupt, _error, ...clean } = cfg;
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(clean, null, 2) + '\n', 'utf8');
  return CONFIG_FILE;
}

function update(patch) {
  const cfg = read();
  const next = { ...cfg, ...patch };
  write(next);
  return next;
}

function recordInstall(entry) {
  const cfg = read();
  const installs = [entry, ...(cfg.installs || [])].slice(0, 20);
  return update({ ...cfg, installs });
}

function reset() {
  try {
    fs.unlinkSync(CONFIG_FILE);
    return true;
  } catch (err) {
    if (err.code === 'ENOENT') return false;
    throw err;
  }
}

function exists() {
  return fs.existsSync(CONFIG_FILE);
}

module.exports = { read, write, update, recordInstall, reset, exists, CONFIG_FILE, CONFIG_DIR, DEFAULTS };
