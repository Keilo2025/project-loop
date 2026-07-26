'use strict';

// project-loop CLI.
//
//   project-loop                    interactive install
//   project-loop install [flags]    install, promptless when fully flagged
//   project-loop uninstall [flags]
//   project-loop status             where is it installed
//   project-loop config             view / edit / reset saved defaults
//   project-loop doctor             environment checks
//   project-loop init               scaffold loop-project/ in the current directory
//
// Flags: --target <ids|all> --scope <user|project> --project <dir>
//        --path <dir> --yes --dry-run --no-save --help --version

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const { select, multiselect, confirm, text, out, paint, colors } = require('./prompts');
const { TARGETS, ALL_TARGET_IDS, SKILL_NAME, resolveDestinations } = require('./targets');
const cfgStore = require('./config');
const { runInstall, runUninstall, scanInstalls, PKG_ROOT, SKILL_SRC, assertPayload } = require('./install');

const pkg = require(path.join(PKG_ROOT, 'package.json'));

// ---------------------------------------------------------------- arg parsing

function parseArgs(argv) {
  const flags = {
    target: null,
    scope: null,
    project: null,
    path: null,
    yes: false,
    dryRun: false,
    save: true,
    help: false,
    version: false,
    reset: false,
    brownfield: false,
  };
  const positional = [];

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    switch (a) {
      case '--target': case '-t': flags.target = argv[++i]; break;
      case '--scope': case '-s': flags.scope = argv[++i]; break;
      case '--project': case '-p': flags.project = argv[++i]; break;
      case '--path': flags.path = argv[++i]; break;
      case '--yes': case '-y': flags.yes = true; break;
      case '--dry-run': case '-n': flags.dryRun = true; break;
      case '--no-save': flags.save = false; break;
      case '--reset': flags.reset = true; break;
      case '--brownfield': flags.brownfield = true; break;
      case '--help': case '-h': flags.help = true; break;
      case '--version': case '-v': flags.version = true; break;
      default:
        if (a.startsWith('-')) {
          out.err('unknown flag: ' + a);
          process.exit(2);
        }
        positional.push(a);
    }
  }
  return { command: positional[0] || null, rest: positional.slice(1), flags };
}

function expandTargets(spec) {
  if (!spec) return null;
  if (spec === 'all') return [...ALL_TARGET_IDS].filter((t) => t !== 'generic');
  const ids = spec.split(',').map((s) => s.trim()).filter(Boolean);
  for (const id of ids) {
    if (!TARGETS[id]) {
      out.err('unknown target "' + id + '". Known: ' + ALL_TARGET_IDS.join(', ') + ', all');
      process.exit(2);
    }
  }
  return ids;
}

// ---------------------------------------------------------------- help

function showHelp() {
  const b = (s) => paint(colors.bold, s);
  out.line('');
  out.line(b('project-loop') + ' ' + paint(colors.grey, 'v' + pkg.version));
  out.line('Closed-loop, evidence-gated build system for AI coding agents.');
  out.line('');
  out.line(b('Usage'));
  out.line('  project-loop                       interactive install');
  out.line('  project-loop install [flags]        install (promptless if fully flagged)');
  out.line('  project-loop uninstall [flags]      remove the skill and subagents');
  out.line('  project-loop status                 show every place it is installed');
  out.line('  project-loop config [--reset]       view or reset saved defaults');
  out.line('  project-loop doctor                 check python3, git, node, paths');
  out.line('  project-loop init [--brownfield]    scaffold loop-project/ here');
  out.line('');
  out.line(b('Flags'));
  out.line('  -t, --target <ids>    ' + ALL_TARGET_IDS.join(', ') + ', or all  (comma-separated)');
  out.line('  -s, --scope <scope>   user (every project) | project (one repo)');
  out.line('  -p, --project <dir>   project root for --scope project. default: cwd');
  out.line('      --path <dir>      skills dir for the "generic" target');
  out.line('  -y, --yes             accept defaults, ask nothing');
  out.line('  -n, --dry-run         print what would happen, write nothing');
  out.line('      --no-save         do not remember these answers');
  out.line('');
  out.line(b('Examples'));
  out.line(paint(colors.grey, '  # one IDE, every project on this machine'));
  out.line('  project-loop install --target claude --scope user');
  out.line(paint(colors.grey, '  # every IDE, every project'));
  out.line('  project-loop install --target all --scope user --yes');
  out.line(paint(colors.grey, '  # one specific repo, committed so the team gets it'));
  out.line('  project-loop install --target cursor --scope project --project ~/code/app');
  out.line('');
}

// ---------------------------------------------------------------- interactive plan

async function buildPlan(flags, { forUninstall = false } = {}) {
  const saved = cfgStore.read();
  if (saved._corrupt) {
    out.warn('config at ' + cfgStore.CONFIG_FILE + ' was unreadable — using defaults');
  }

  const nonInteractive = flags.yes;
  let targets = expandTargets(flags.target);
  let scope = flags.scope;
  let projectRoot = flags.project ? path.resolve(flags.project) : process.cwd();
  let customPath = flags.path || saved.customSkillPath || null;

  if (scope && !['user', 'project'].includes(scope)) {
    out.err('--scope must be user or project');
    process.exit(2);
  }

  // ---- Question 1: which agents?
  if (!targets) {
    if (nonInteractive) {
      targets = saved.targets.length ? saved.targets : ['claude'];
    } else {
      const options = ALL_TARGET_IDS.map((id) => ({
        label: TARGETS[id].label,
        hint: TARGETS[id].hint,
        value: id,
      }));
      const initialSelected = saved.targets
        .map((id) => ALL_TARGET_IDS.indexOf(id))
        .filter((i) => i >= 0);

      targets = await multiselect(
        forUninstall ? 'Remove Project Loop from which agents?' : 'Install into which agents?',
        options,
        { initialSelected: initialSelected.length ? initialSelected : [0] }
      );
    }
  }
  if (!targets.length) {
    out.warn('no agents selected — nothing to do');
    process.exit(0);
  }

  // ---- Question 2: how widely?
  if (!scope) {
    if (nonInteractive) {
      scope = saved.scope || 'user';
    } else {
      const cwdName = path.basename(projectRoot);
      scope = await select('How widely should it apply?', [
        {
          label: 'Every project on this machine',
          hint: 'user scope, installs under your home directory',
          value: 'user',
        },
        {
          label: 'Just one specific project',
          hint: 'project scope, commit it so your team gets it too',
          value: 'project',
        },
      ], { initialIndex: saved.scope === 'project' ? 1 : 0 });

      if (scope === 'project') {
        const answer = await text('Project directory?', projectRoot, false);
        projectRoot = path.resolve(answer.replace(/^~(?=$|\/)/, os.homedir()));
        if (!fs.existsSync(projectRoot)) {
          out.err('no such directory: ' + projectRoot);
          process.exit(2);
        }
        if (!fs.statSync(projectRoot).isDirectory()) {
          out.err('not a directory: ' + projectRoot);
          process.exit(2);
        }
      }
    }
  }

  // ---- Question 3: custom path, only if the generic target was picked
  if (targets.includes('generic') && !customPath) {
    const guess = scope === 'user'
      ? path.join(os.homedir(), '.agents', 'skills')
      : path.join(projectRoot, '.agents', 'skills');
    if (nonInteractive) {
      customPath = guess;
    } else {
      out.blank();
      out.dim('  The Agent Skills spec standardises the file format, not the install');
      out.dim('  location. Check your tool\'s docs for the directory it scans.');
      customPath = path.resolve(
        (await text('Skills directory for the other agent?', guess, false))
          .replace(/^~(?=$|\/)/, os.homedir())
      );
    }
  }

  return { targets, scope, projectRoot, customPath, dry: flags.dryRun, nonInteractive };
}

function printPlan(plan, verb) {
  out.title(verb + ' plan');
  out.line('  agents  ' + plan.targets.map((t) => TARGETS[t].label).join(', '));
  out.line('  scope   ' + (plan.scope === 'user'
    ? 'user — every project on this machine'
    : 'project — ' + plan.projectRoot));
  for (const t of plan.targets) {
    const d = resolveDestinations(t, plan.scope, plan.projectRoot, plan.customPath);
    out.line('  ' + paint(colors.grey, '· ' + d.skillDest));
    if (d.agentsDir) out.line('  ' + paint(colors.grey, '· ' + d.agentsDir + '  (5 subagents)'));
    for (const a of d.adapters) out.line('  ' + paint(colors.grey, '· ' + a.to));
  }
  if (plan.dry) out.info('dry run — nothing will be written');
}

// ---------------------------------------------------------------- commands

async function cmdInstall(flags) {
  assertPayload();
  out.line('');
  out.line(paint(colors.bold, 'Project Loop') + ' ' + paint(colors.grey, 'v' + pkg.version + ' — install'));

  const plan = await buildPlan(flags);
  printPlan(plan, 'Install');

  if (!plan.nonInteractive && !plan.dry) {
    const go = await confirm('Proceed?', true, false);
    if (!go) {
      out.info('cancelled — nothing written');
      return 0;
    }
  }

  runInstall(plan);

  if (flags.save && !plan.dry) {
    cfgStore.update({
      targets: plan.targets,
      scope: plan.scope,
      customSkillPath: plan.customPath,
    });
    cfgStore.recordInstall({
      at: new Date().toISOString(),
      targets: plan.targets,
      scope: plan.scope,
      root: plan.scope === 'project' ? plan.projectRoot : null,
    });
    out.blank();
    out.dim('  Defaults saved to ' + cfgStore.CONFIG_FILE);
    out.dim('  Next time: project-loop install --yes');
  }

  if (!plan.dry) {
    out.title('Next');
    out.line('  1. Verify it loaded  ' + paint(colors.grey, '— project-loop doctor'));
    out.line('  2. In a project      ' + paint(colors.grey, '— say "run the project loop" and describe what you want built'));
    out.line('  3. Or scaffold state ' + paint(colors.grey, '— project-loop init'));
    out.blank();
    out.dim('  Only a Judge verdict of PASS closes the loop. That is the whole point.');
    out.blank();
  }
  return 0;
}

async function cmdUninstall(flags) {
  out.line('');
  out.line(paint(colors.bold, 'Project Loop') + ' ' + paint(colors.grey, 'uninstall'));

  const plan = await buildPlan(flags, { forUninstall: true });
  printPlan(plan, 'Uninstall');

  if (!plan.nonInteractive && !plan.dry) {
    const go = await confirm('Remove these?', false, false);
    if (!go) {
      out.info('cancelled — nothing removed');
      return 0;
    }
  }

  runUninstall(plan);
  out.blank();
  out.dim('  loop-project/ directories were left alone. They are project state and part of');
  out.dim('  your audit trail, not installed files — delete them yourself if you want.');
  out.blank();
  return 0;
}

function cmdStatus(flags) {
  const projectRoot = flags.project ? path.resolve(flags.project) : process.cwd();
  const found = scanInstalls(projectRoot, flags.path);

  out.title('Installed');
  if (!found.length) {
    out.info('not installed anywhere I know to look');
    out.dim('        run: project-loop install');
  } else {
    // Pad to the widest label actually present rather than a guessed constant,
    // so a long target name cannot break the column.
    const w = Math.max(...found.map((f) => f.label.length)) + 2;
    for (const f of found) {
      out.ok(
        f.label.padEnd(w) + paint(colors.grey, f.scope.padEnd(9)) + f.path +
        (f.agents ? paint(colors.grey, '  (+' + f.agents + ' subagents)') : '')
      );
    }
  }

  // Loop state in the current directory, if any.
  out.title('Loop state here');
  const stateFile = path.join(projectRoot, 'loop-project', 'loop.json');
  if (!fs.existsSync(stateFile)) {
    out.info('no loop found in ' + projectRoot);
    out.dim('        that is the correct answer before you have started one');
  } else {
    try {
      const st = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      out.line('  phase   ' + (st.phase !== undefined ? st.phase : '?'));
      out.line('  status  ' + (st.status || '?'));
      if (st.cursor) out.line('  cursor  ' + st.cursor);
    } catch (err) {
      out.warn('loop-project/loop.json exists but could not be parsed: ' + err.message);
    }
  }

  const saved = cfgStore.read();
  if (cfgStore.exists()) {
    out.title('Saved defaults');
    out.line('  targets  ' + (saved.targets.length ? saved.targets.join(', ') : '(none)'));
    out.line('  scope    ' + (saved.scope || '(none)'));
    out.dim('  ' + cfgStore.CONFIG_FILE);
  }
  out.blank();
  return 0;
}

async function cmdConfig(flags, rest) {
  if (flags.reset || rest.includes('reset')) {
    const removed = cfgStore.reset();
    out.blank();
    if (removed) out.ok('removed ' + cfgStore.CONFIG_FILE);
    else out.info('no config file to remove');
    out.blank();
    return 0;
  }

  const saved = cfgStore.read();
  out.title('Saved defaults');
  if (!cfgStore.exists()) {
    out.info('no config yet — it is written after your first install');
  }
  out.line('  targets           ' + (saved.targets.length ? saved.targets.join(', ') : '(none)'));
  out.line('  scope             ' + (saved.scope || '(none)'));
  out.line('  customSkillPath   ' + (saved.customSkillPath || '(none)'));
  out.dim('  file: ' + cfgStore.CONFIG_FILE);

  if (saved.installs && saved.installs.length) {
    out.title('Recent installs');
    for (const i of saved.installs.slice(0, 5)) {
      out.line('  ' + i.at.slice(0, 19).replace('T', ' ') + '  ' +
        i.targets.join(',') + '  ' + i.scope + (i.root ? '  ' + i.root : ''));
    }
  }

  if (!flags.yes) {
    out.blank();
    const edit = await confirm('Change these now?', false, false);
    if (edit) {
      const plan = await buildPlan({ ...flags, target: null, scope: null });
      cfgStore.update({
        targets: plan.targets,
        scope: plan.scope,
        customSkillPath: plan.customPath,
      });
      out.blank();
      out.ok('saved to ' + cfgStore.CONFIG_FILE);
      out.dim('  nothing was installed — run: project-loop install --yes');
    }
  }
  out.blank();
  return 0;
}

function cmdDoctor(flags) {
  let problems = 0;
  const projectRoot = flags.project ? path.resolve(flags.project) : process.cwd();

  out.title('Environment');
  out.ok('node    ' + process.version + '  ' + paint(colors.grey, process.execPath));

  const py = spawnSync('python3', ['--version'], { encoding: 'utf8' });
  if (py.status === 0) {
    out.ok('python3 ' + (py.stdout || py.stderr).trim());
  } else {
    problems++;
    out.warn('python3 not found');
    out.dim('        loop.py drives the state machine and every deterministic check.');
    out.dim('        Without it the loop runs on model judgement alone — slower,');
    out.dim('        more expensive, less reliable. Install python3 3.8 or later.');
  }

  const git = spawnSync('git', ['--version'], { encoding: 'utf8' });
  if (git.status === 0) {
    out.ok('git     ' + git.stdout.trim());
  } else {
    problems++;
    out.warn('git not found — write-set enforcement needs it');
  }

  out.title('Payload');
  try {
    assertPayload();
    const refs = fs.readdirSync(path.join(SKILL_SRC, 'references')).length;
    const tpl = fs.readdirSync(path.join(SKILL_SRC, 'templates')).length;
    out.ok('skill source intact  ' + paint(colors.grey, refs + ' references, ' + tpl + ' templates'));
    out.dim('  ' + SKILL_SRC);
  } catch (err) {
    problems++;
    out.err(err.message);
  }

  out.title('Install locations');
  const found = scanInstalls(projectRoot, flags.path);
  if (!found.length) {
    problems++;
    out.warn('not installed anywhere — run: project-loop install');
  } else {
    for (const f of found) {
      out.ok(f.label + ' (' + f.scope + ')  ' + paint(colors.grey, f.path));
    }
  }

  out.title('Git in ' + projectRoot);
  const inRepo = spawnSync('git', ['rev-parse', '--is-inside-work-tree'], {
    cwd: projectRoot, encoding: 'utf8',
  });
  if (inRepo.status === 0 && inRepo.stdout.trim() === 'true') {
    out.ok('inside a git work tree — write-set enforcement available');
  } else {
    out.warn('not a git repository — you lose the cheapest check the loop has');
    out.dim('        run: git init');
  }

  out.blank();
  if (problems === 0) out.line('  ' + paint(colors.green, 'All clear.'));
  else out.line('  ' + paint(colors.yellow, problems + ' thing(s) worth fixing above.'));
  out.blank();
  return problems === 0 ? 0 : 1;
}

function cmdInit(flags, rest) {
  const found = scanInstalls(process.cwd(), flags.path);
  const loopPy = found.length
    ? path.join(found[0].path, 'scripts', 'loop.py')
    : path.join(SKILL_SRC, 'scripts', 'loop.py');

  if (!fs.existsSync(loopPy)) {
    out.err('could not find loop.py. Run: project-loop doctor');
    return 2;
  }
  const args = [loopPy, 'init'];
  if (flags.brownfield || rest.includes('brownfield')) args.push('--brownfield');

  out.blank();
  out.info('python3 ' + args.join(' '));
  const r = spawnSync('python3', args, { stdio: 'inherit' });
  if (r.error) {
    out.err('could not run python3: ' + r.error.message);
    return 2;
  }
  return r.status === null ? 1 : r.status;
}

// ---------------------------------------------------------------- entry

async function main(argv) {
  const { command, rest, flags } = parseArgs(argv);

  if (flags.version) {
    out.line(pkg.version);
    return 0;
  }
  if (flags.help || command === 'help') {
    showHelp();
    return 0;
  }

  switch (command) {
    case null:
    case 'install':
      return cmdInstall(flags);
    case 'uninstall':
    case 'remove':
      return cmdUninstall(flags);
    case 'status':
      return cmdStatus(flags);
    case 'config':
      return cmdConfig(flags, rest);
    case 'doctor':
      return cmdDoctor(flags);
    case 'init':
      return cmdInit(flags, rest);
    default:
      out.err('unknown command: ' + command);
      out.dim('  run: project-loop --help');
      return 2;
  }
}

module.exports = { main };
