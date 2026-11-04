import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import net from "node:net";

export async function requireAvailableAuditPorts(env = process.env) {
  requireIsolatedEnvironment(env);
  for (const port of [env.E2E_DJANGO_PORT, env.E2E_FRONTEND_PORT]) {
    await new Promise((resolve, reject) => {
      const server = net.createServer();
      server.once("error", () => reject(new Error(`Audit port ${port} is already occupied; no setup performed.`)));
      server.listen({ host: "127.0.0.1", port: Number(port), exclusive: true }, () => server.close(resolve));
    });
  }
}

export function requireIsolatedEnvironment(env = process.env) {
  const refuse = () => {
    throw new Error("This helper requires scripts.codex_verify.isolated_runtime: disposable gate.sqlite3 and dedicated loopback ports. No setup was performed.");
  };
  if (env.ZANI_QUALITY_GATE !== "1" || !env.DATABASE_URL?.startsWith("sqlite:///")) refuse();
  const database = env.DATABASE_URL.slice("sqlite:///".length);
  if (!path.isAbsolute(database) || path.basename(database) !== "gate.sqlite3") refuse();
  const directory = path.dirname(database);
  if (!path.basename(directory).startsWith("zani-quality-gate-")) refuse();
  try {
    const realDirectory = fs.realpathSync(directory);
    if (path.dirname(realDirectory) !== fs.realpathSync(os.tmpdir())) refuse();
    if (realDirectory !== path.resolve(directory)) refuse();
    if (fs.existsSync(database) && fs.realpathSync(database) !== path.resolve(database)) refuse();
  } catch {
    refuse();
  }
  const ports = [env.E2E_DJANGO_PORT, env.E2E_FRONTEND_PORT];
  if (ports.some((port) => !/^\d+$/.test(port ?? "") || Number(port) < 1024 || Number(port) > 65535 || [8000, 5173].includes(Number(port)))) refuse();
  if (Number(ports[0]) === Number(ports[1])) refuse();
  if (env.E2E_API_BASE_URL !== `http://127.0.0.1:${ports[0]}` || env.E2E_BASE_URL !== `http://127.0.0.1:${ports[1]}`) refuse();
}
