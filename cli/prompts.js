'use strict';

// Zero-dependency interactive prompts.
//
// Arrow-key navigation when stdin is a TTY; numbered fallback when it is not
// (CI, piped input, `| cat`). Every prompt honours --yes / non-interactive mode
// by returning its default, so the CLI is scriptable as well as interactive.

const readline = require('readline');

const ESC = '\u001b';
const c = {
  reset: '\u001b[0m',
  dim: '\u001b[2m',
  bold: '\u001b[1m',
  cyan: '\u001b[36m',
  green: '\u001b[32m',
  yellow: '\u001b[33m',
  red: '\u001b[31m',
  grey: '\u001b[90m',
};

const NO_COLOR = !!process.env.NO_COLOR || !process.stdout.isTTY;
function paint(color, s) {
  return NO_COLOR ? s : color + s + c.reset;
}

function isTTY() {
  return !!(process.stdin.isTTY && process.stdout.isTTY);
}

function write(s) {
  process.stdout.write(s);
}

// ---------------------------------------------------------------- output helpers

const out = {
  blank: () => write('\n'),
  title: (s) => write('\n' + paint(c.bold, s) + '\n'),
  line: (s = '') => write(s + '\n'),
  dim: (s) => write(paint(c.grey, s) + '\n'),
  ok: (s) => write('  ' + paint(c.green, 'ok') + '    ' + s + '\n'),
  info: (s) => write('  ' + paint(c.cyan, 'info') + '  ' + s + '\n'),
  warn: (s) => write('  ' + paint(c.yellow, 'warn') + '  ' + s + '\n'),
  err: (s) => process.stderr.write('  ' + paint(c.red, 'error') + ' ' + s + '\n'),
  step: (s) => write('  ' + paint(c.grey, '-') + '     ' + s + '\n'),
};

// ---------------------------------------------------------------- raw-mode core

function renderList(question, options, cursor, selected, multi) {
  const lines = [];
  lines.push(paint(c.bold, '? ') + question);
  options.forEach((opt, i) => {
    const active = i === cursor;
    let marker;
    if (multi) {
      marker = selected.has(i) ? paint(c.green, '[x]') : '[ ]';
    } else {
      marker = active ? paint(c.cyan, '>') : ' ';
    }
    const label = active ? paint(c.cyan, opt.label) : opt.label;
    let row = '  ' + marker + ' ' + label;
    if (opt.hint) row += ' ' + paint(c.grey, '- ' + opt.hint);
    lines.push(row);
  });
  const help = multi
    ? 'up/down move   space toggle   a all   enter confirm   ctrl-c cancel'
    : 'up/down move   enter select   ctrl-c cancel';
  lines.push('  ' + paint(c.grey, help));
  return lines;
}

function rawList(question, options, opts) {
  const multi = !!opts.multi;
  return new Promise((resolve, reject) => {
    let cursor = Math.max(0, opts.initialIndex || 0);
    const selected = new Set(opts.initialSelected || []);
    let painted = 0;

    const draw = () => {
      if (painted) {
        readline.moveCursor(process.stdout, 0, -painted);
        readline.clearScreenDown(process.stdout);
      }
      const lines = renderList(question, options, cursor, selected, multi);
      write(lines.join('\n') + '\n');
      painted = lines.length;
    };

    const cleanup = () => {
      process.stdin.setRawMode(false);
      process.stdin.pause();
      process.stdin.removeListener('data', onData);
    };

    const onData = (buf) => {
      const key = buf.toString();

      if (key === '\u0003') {
        // ctrl-c
        cleanup();
        write('\n');
        return reject(new Error('cancelled'));
      }
      if (key === ESC + '[A' || key === 'k') {
        cursor = (cursor - 1 + options.length) % options.length;
        return draw();
      }
      if (key === ESC + '[B' || key === 'j') {
        cursor = (cursor + 1) % options.length;
        return draw();
      }
      if (multi && key === ' ') {
        if (selected.has(cursor)) selected.delete(cursor);
        else selected.add(cursor);
        return draw();
      }
      if (multi && (key === 'a' || key === 'A')) {
        if (selected.size === options.length) selected.clear();
        else options.forEach((_, i) => selected.add(i));
        return draw();
      }
      if (key === '\r' || key === '\n') {
        if (multi && selected.size === 0) {
          // Enter with nothing ticked takes the highlighted row, which is what
          // people expect and saves a keystroke in the common single-pick case.
          selected.add(cursor);
        }
        cleanup();
        if (multi) {
          const picked = [...selected].sort((a, b) => a - b).map((i) => options[i].value);
          return resolve(picked);
        }
        return resolve(options[cursor].value);
      }
      // number shortcuts
      const n = parseInt(key, 10);
      if (!Number.isNaN(n) && n >= 1 && n <= options.length) {
        cursor = n - 1;
        if (multi) {
          if (selected.has(cursor)) selected.delete(cursor);
          else selected.add(cursor);
        }
        return draw();
      }
    };

    // The shared line reader and raw mode cannot both own stdin.
    detachLineReader();
    process.stdin.resume();
    process.stdin.setRawMode(true);
    process.stdin.on('data', onData);
    draw();
  });
}

// ---------------------------------------------------------------- line fallback

// One shared line reader, with a queue.
//
// Two things bite here, and only the queue fixes the second:
//
//   1. A fresh readline interface per question works on a TTY but breaks piped
//      stdin — closing the first interface ends the stream, so every later
//      question reads EOF and the run silently answers itself.
//
//   2. When stdin is a pipe, readline receives the whole input as one chunk and
//      emits every 'line' from it in a single tick. Answers 2 and 3 fire before
//      question 2 has been asked, so pausing between questions does not help:
//      the events are already gone. They have to be buffered as they arrive.
//
// terminal:false keeps readline out of the key-handling business — that is
// rawList's job.

let sharedRl = null;
let detaching = false;
let stdinEnded = false;
const lineQueue = [];
let lineWaiter = null;

function deliver(value) {
  if (lineWaiter) {
    const resolve = lineWaiter;
    lineWaiter = null;
    resolve(value);
    return true;
  }
  return false;
}

function lineReader() {
  if (sharedRl) return sharedRl;

  sharedRl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
  });

  sharedRl.on('line', (line) => {
    if (!deliver(line)) lineQueue.push(line);
  });

  sharedRl.on('close', () => {
    sharedRl = null;
    // A deliberate detach (raw mode is taking over) is not end-of-input.
    if (detaching) return;
    stdinEnded = true;
    deliver('');
  });

  return sharedRl;
}

// Raw mode and the line reader cannot both own stdin. Hand it over cleanly.
function detachLineReader() {
  if (!sharedRl) return;
  detaching = true;
  const rl = sharedRl;
  sharedRl = null;
  rl.close();
  detaching = false;
}

function closePrompts() {
  if (!sharedRl) return;
  detaching = true;
  const rl = sharedRl;
  sharedRl = null;
  rl.close();
  detaching = false;
}

function askLine(question) {
  lineReader();
  process.stdout.write(question);

  // Already buffered from an earlier chunk.
  if (lineQueue.length) return Promise.resolve(lineQueue.shift());

  // Piped input can run out mid-flow. Treat EOF as "take the default" rather
  // than hanging forever waiting for a line that will never arrive.
  if (stdinEnded) return Promise.resolve('');

  return new Promise((resolve) => {
    lineWaiter = resolve;
  });
}

async function numberedList(question, options, opts) {
  const multi = !!opts.multi;
  out.line('\n? ' + question);
  options.forEach((opt, i) => {
    out.line('  ' + (i + 1) + ') ' + opt.label + (opt.hint ? '  - ' + opt.hint : ''));
  });
  const hint = multi
    ? '  enter numbers separated by commas, or "a" for all: '
    : '  enter a number: ';
  const raw = (await askLine(hint)).trim();

  if (!raw) {
    const fallbackIndex = Math.max(0, opts.initialIndex || 0);
    return multi ? [options[fallbackIndex].value] : options[fallbackIndex].value;
  }
  if (multi && (raw === 'a' || raw === 'A')) return options.map((o) => o.value);

  const picks = raw
    .split(',')
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !Number.isNaN(n) && n >= 1 && n <= options.length)
    .map((n) => n - 1);

  if (picks.length === 0) {
    out.warn('did not understand that — try again');
    return numberedList(question, options, opts);
  }
  return multi ? picks.map((i) => options[i].value) : options[picks[0]].value;
}

// ---------------------------------------------------------------- public API

async function select(question, options, opts = {}) {
  if (opts.nonInteractive) return options[opts.initialIndex || 0].value;
  if (isTTY()) return rawList(question, options, { ...opts, multi: false });
  return numberedList(question, options, { ...opts, multi: false });
}

async function multiselect(question, options, opts = {}) {
  if (opts.nonInteractive) {
    const idx = opts.initialSelected && opts.initialSelected.length ? opts.initialSelected : [0];
    return idx.map((i) => options[i].value);
  }
  if (isTTY()) return rawList(question, options, { ...opts, multi: true });
  return numberedList(question, options, { ...opts, multi: true });
}

async function confirm(question, defaultYes = true, nonInteractive = false) {
  if (nonInteractive) return defaultYes;
  const suffix = defaultYes ? ' [Y/n] ' : ' [y/N] ';
  const answer = (await askLine('? ' + question + suffix)).trim().toLowerCase();
  if (!answer) return defaultYes;
  return answer === 'y' || answer === 'yes';
}

async function text(question, defaultValue = '', nonInteractive = false) {
  if (nonInteractive) return defaultValue;
  const suffix = defaultValue ? ' ' + paint(c.grey, '(' + defaultValue + ')') + ' ' : ' ';
  const answer = (await askLine('? ' + question + suffix)).trim();
  return answer || defaultValue;
}

module.exports = {
  select,
  multiselect,
  confirm,
  text,
  out,
  paint,
  colors: c,
  isTTY,
  closePrompts,
};
