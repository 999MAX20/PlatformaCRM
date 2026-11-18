import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';

const require = createRequire(import.meta.url);
const picomatch = require('picomatch');

test('repeated wildcard extglobs finish within a bounded child process', () => {
  const result = spawnSync(process.execPath, ['-e', `
    const pm = require(${JSON.stringify(require.resolve('picomatch'))});
    const patterns = ['+(*)', '+(*a)', '*(*a)', '+(a*b)', '+(a*|b)', '+(@(*a))',
      '+({a*,b})', '+(!(a))', '+(**)', 'src/+(*a).js', '+([*]*a)', '+("*"*a)'];
    for (const pattern of patterns) {
      for (const options of [{}, { dot: true }, { capture: true }, { windows: true },
          { bash: true }, { unescape: true }, { posix: true }, { fastpaths: false },
          { maxExtglobRecursion: false }]) {
        const re = pm.makeRe(pattern, options);
        for (const input of ['a'.repeat(48) + '/', 'ab'.repeat(24) + '!', 'x'.repeat(48) + '/']) re.test(input);
      }
    }
  `], { timeout: 3000, encoding: 'utf8' });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
});

test('every build consumer resolves the reviewed package bytes', () => {
  const installed = dirname(require.resolve('picomatch'));
  for (const file of ['index.js', 'posix.js', 'package.json', 'LICENSE',
      'lib/constants.js', 'lib/parse.js', 'lib/picomatch.js', 'lib/scan.js', 'lib/utils.js']) {
    assert.equal(readFileSync(join(installed, file), 'utf8').replaceAll('\r\n', '\n'),
      readFileSync(new URL(`../../vendor/picomatch/${file}`, import.meta.url), 'utf8').replaceAll('\r\n', '\n'), file);
  }
  for (const consumer of ['vite', '@rollup/pluginutils', 'tinyglobby', 'rollup-plugin-visualizer']) {
    const fromConsumer = createRequire(import.meta.resolve(consumer));
    assert.equal(fromConsumer.resolve('picomatch'), require.resolve('picomatch'), consumer);
  }
  const lock = JSON.parse(readFileSync(new URL('../../package-lock.json', import.meta.url)));
  const copies = Object.entries(lock.packages).filter(([name]) => name.endsWith('/picomatch'));
  assert.equal(copies.length, 1);
  assert.equal(copies[0][1].name, '@platformacrm/picomatch');
  assert.equal(copies[0][1].resolved, 'file:vendor/platformacrm-picomatch-4.0.7+platforma.1.tgz');
});

test('ordinary build globs and fixed-text extglobs retain their meaning', () => {
  for (const [pattern, accepted, rejected] of [
    ['src/**/*.{ts,tsx}', 'src/components/Button.tsx', 'src/components/Button.css'],
    ['**/!(*.test).js', 'src/main.js', 'src/main.test.js'],
    ['+(foo|bar).js', 'foobarfoo.js', 'food.js'],
    ['*(f*(o)).js', 'fooofoo.js', 'bar.js'],
    ['+(\\*a)', '*a*a', 'aa'],
    ['+([*]a)', '*a*a', 'aa'],
  ]) {
    assert.equal(picomatch.isMatch(accepted, pattern), true, `${pattern}: ${accepted}`);
    assert.equal(picomatch.isMatch(rejected, pattern), false, `${pattern}: ${rejected}`);
  }
});

test('unsafe repetitions use the literal fallback through public matching APIs', () => {
  const posix = require('picomatch/posix');
  for (const pattern of ['+(*)', '+(*a)', '*(*a)', '+(a*|b)', '+(@(*a))', '+(!(a))']) {
    for (const matcher of [picomatch, posix]) {
      assert.equal(matcher.isMatch(pattern, pattern), true, pattern);
      assert.equal(matcher.isMatch('aaa', pattern), false, pattern);
      assert.equal(matcher.isMatch('aaa', pattern, { maxExtglobRecursion: false }), false, pattern);
    }
  }
});
