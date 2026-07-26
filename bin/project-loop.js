#!/usr/bin/env node
'use strict';

const MIN_MAJOR = 18;
const major = Number(process.versions.node.split('.')[0]);
if (Number.isFinite(major) && major < MIN_MAJOR) {
  process.stderr.write(
    'project-loop needs Node ' + MIN_MAJOR + ' or later (found ' + process.versions.node + ').\n'
  );
  process.exit(2);
}

const { main } = require('../cli/index.js');
const { closePrompts } = require('../cli/prompts.js');

main(process.argv.slice(2))
  .then((code) => {
    closePrompts();
    process.exit(typeof code === 'number' ? code : 0);
  })
  .catch((err) => {
    closePrompts();
    if (err && err.message === 'cancelled') {
      process.stderr.write('  cancelled\n');
      process.exit(130);
    }
    process.stderr.write('\n  error  ' + (err && err.message ? err.message : String(err)) + '\n');
    if (process.env.PROJECT_LOOP_DEBUG && err && err.stack) {
      process.stderr.write(err.stack + '\n');
    }
    process.exit(1);
  });
