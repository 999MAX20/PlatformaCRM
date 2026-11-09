import fs from 'node:fs';
import { performance } from 'node:perf_hooks';

const [configPath, usersArg, secondsArg, thinkArg, output] = process.argv.slice(2);
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const base = new URL(config.base);
if (!config.disposable || !['crm_bench_small', 'crm_bench_large'].includes(config.database)
    || base.hostname !== '127.0.0.1' || ['8000', '5173', ''].includes(base.port)) {
  throw new Error('Only a dedicated disposable loopback benchmark is supported');
}
const users = Number(usersArg), seconds = Number(secondsArg), think = Number(thinkArg);
if (!(users >= 1 && users <= config.subjects.length && seconds >= 5 && think >= 0)) throw new Error('Invalid stage');
const samples = [];
const start = performance.now(), deadline = start + seconds * 1000;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function request(subject, iteration) {
  const business = subject.business;
  const list = [
    ['clients', `/api/clients/?business=${business}&page=1`],
    ['appointments', `/api/appointments/?business=${business}&start=2026-10-01&end=2026-12-01&page=1`],
    ['tasks', `/api/tasks/?business=${business}&page=1`],
    ['deals', `/api/deals/?business=${business}&page=1`],
    ['clients-search', `/api/clients/?business=${business}&search=Load%20client&page=1`],
    ['clients', `/api/clients/?business=${business}&page=1`],
    ['client-card', `/api/clients/${subject.client}/crm-card/`],
    ['dashboard', `/api/analytics/owner-dashboard/?business=${business}`],
    ['tasks', `/api/tasks/?business=${business}&page=1`],
    ['task-create', '/api/tasks/', { business, title: `Load ${subject.user} ${Date.now()} ${iteration}` }],
  ];
  return list[iteration % list.length];
}

await Promise.all(Array.from({ length: users }, async (_, user) => {
  const subject = config.subjects[user];
  let iteration = user;
  while (performance.now() < deadline) {
    const [endpoint, path, body] = request(subject, iteration++);
    const begin = performance.now();
    let status = 0, bytes = 0, error = '';
    try {
      const response = await fetch(new URL(path, base), {
        method: body ? 'POST' : 'GET', redirect: 'error', signal: AbortSignal.timeout(30000),
        headers: { Authorization: `Bearer ${subject.token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      status = response.status;
      bytes = (await response.arrayBuffer()).byteLength;
    } catch (exc) { error = exc.name; }
    const end = performance.now();
    samples.push({ endpoint, ms: end - begin, status, expected: body ? 201 : 200, bytes, error, inWindow: end <= deadline });
    if (think) await sleep(think * 1000);
  }
}));

function summarize(values) {
  const sorted = values.map(v => v.ms).sort((a, b) => a - b);
  const percentile = p => sorted.length ? sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * p) - 1)] : null;
  const errors = values.filter(v => v.status !== v.expected).length;
  return { requests: values.length, errors, errorPercent: values.length ? errors * 100 / values.length : 0,
    rps: values.filter(v => v.inWindow).length / seconds, p50: percentile(.5), p95: percentile(.95), p99: percentile(.99),
    statuses: Object.fromEntries([...new Set(values.map(v => v.status))].map(s => [s, values.filter(v => v.status === s).length])) };
}
const result = { database: config.database, users, seconds, thinkSeconds: think, elapsedSeconds: (performance.now() - start) / 1000,
  ...summarize(samples), endpoints: Object.fromEntries([...new Set(samples.map(v => v.endpoint))].map(name => [name, summarize(samples.filter(v => v.endpoint === name))])) };
result.pass = result.requests > 0 && result.errorPercent < 1 && result.p95 <= 1000;
fs.writeFileSync(output, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result));
