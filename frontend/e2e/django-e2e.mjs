import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();

const e2eDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(e2eDir, "../..");

const pythonPath = process.env.E2E_PYTHON || defaultPythonPath();
function defaultPythonPath() {
  const relativePath =
    process.platform === "win32"
      ? [".venv", "Scripts", "python.exe"]
      : [".venv", "bin", "python"];
  const candidate = path.join(rootDir, ...relativePath);
  return fs.existsSync(candidate) ? candidate : "python";
}

function runPython(args) {
  const result = spawnSync(pythonPath, args, {
    cwd: rootDir,
    env: process.env,
    stdio: "inherit",
    windowsHide: true,
  });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function prepare() {
  runPython([path.join(rootDir, "scripts", "browser_test_runtime.py"), "prepare"]);
}

const mode = process.argv[2] || "prepare";

if (mode === "prepare") {
  prepare();
} else if (mode === "serve") {
  prepare();
  runPython([path.join(e2eDir, "serve-isolated.py")]);
} else {
  console.error(`Unknown django-e2e mode: ${mode}`);
  process.exit(2);
}
