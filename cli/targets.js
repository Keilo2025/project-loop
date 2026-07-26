'use strict';

// Where each agent looks for skills.
//
// The Agent Skills format is shared across these tools; the discovery paths are
// not, and they move as the tools evolve. That divergence is the only reason
// this file exists. Keep it boring and keep it accurate — a wrong path here
// produces a silent no-op, which is the worst failure mode an installer has.

const os = require('os');
const path = require('path');

const SKILL_NAME = 'project-loop';

function home() {
  return os.homedir();
}

const TARGETS = {
  claude: {
    id: 'claude',
    label: 'Claude Code',
    hint: 'skill + 5 subagents (strongest role isolation)',
    supportsAgents: true,
    user() {
      return {
        skills: path.join(home(), '.claude', 'skills'),
        agents: path.join(home(), '.claude', 'agents'),
      };
    },
    project(root) {
      return {
        skills: path.join(root, '.claude', 'skills'),
        agents: path.join(root, '.claude', 'agents'),
      };
    },
    adapters() {
      return [];
    },
    notes: {
      project: 'project scope loads only after you accept the workspace trust prompt',
      user: 'alternative route: /plugin marketplace add Keilo2025/project-loop',
    },
  },

  codex: {
    id: 'codex',
    label: 'OpenAI Codex',
    hint: 'skill only — no subagents, roles run sequentially',
    supportsAgents: false,
    user() {
      return { skills: path.join(home(), '.agents', 'skills') };
    },
    project(root) {
      return { skills: path.join(root, '.agents', 'skills') };
    },
    adapters(root, scope) {
      if (scope !== 'project') return [];
      return [{ from: path.join('adapters', 'codex', 'AGENTS.md'), to: path.join(root, 'AGENTS.md'), label: 'AGENTS.md' }];
    },
    notes: {
      both: 'no subagents — see references/portability.md for how to compensate',
    },
  },

  cursor: {
    id: 'cursor',
    label: 'Cursor',
    hint: 'skill + a short project rule that pulls it in on demand',
    supportsAgents: false,
    user() {
      return { skills: path.join(home(), '.cursor', 'skills') };
    },
    project(root) {
      return { skills: path.join(root, '.cursor', 'skills') };
    },
    adapters(root, scope) {
      if (scope !== 'project') return [];
      return [
        {
          from: path.join('adapters', 'cursor', 'project-loop.mdc'),
          to: path.join(root, '.cursor', 'rules', 'project-loop.mdc'),
          label: 'rule',
        },
      ];
    },
    notes: {
      user: 'Cursor rules are project-scoped — use project scope to get the rule file too',
    },
  },

  generic: {
    id: 'generic',
    label: 'Other agent (custom path)',
    hint: 'any tool that reads the Agent Skills format',
    supportsAgents: false,
    needsCustomPath: true,
    user(custom) {
      return { skills: custom };
    },
    project(root, custom) {
      return { skills: custom || path.join(root, '.agents', 'skills') };
    },
    adapters(root, scope) {
      if (scope !== 'project') return [];
      return [{ from: path.join('adapters', 'generic', 'AGENTS.md'), to: path.join(root, 'AGENTS.md'), label: 'AGENTS.md' }];
    },
    notes: {
      both: 'the Agent Skills spec standardises the file format, not the install location',
    },
  },
};

const ALL_TARGET_IDS = Object.keys(TARGETS);

function resolveTarget(id) {
  const t = TARGETS[id];
  if (!t) {
    throw new Error(
      'unknown target "' + id + '". Known targets: ' + ALL_TARGET_IDS.join(', ')
    );
  }
  return t;
}

// Resolve a target + scope into the concrete directories to write.
function resolveDestinations(targetId, scope, projectRoot, customPath) {
  const t = resolveTarget(targetId);
  const dirs = scope === 'user' ? t.user(customPath) : t.project(projectRoot, customPath);
  return {
    target: t,
    skillsDir: dirs.skills,
    skillDest: path.join(dirs.skills, SKILL_NAME),
    agentsDir: t.supportsAgents ? dirs.agents : null,
    adapters: t.adapters(projectRoot, scope),
  };
}

module.exports = { TARGETS, ALL_TARGET_IDS, SKILL_NAME, resolveTarget, resolveDestinations };
