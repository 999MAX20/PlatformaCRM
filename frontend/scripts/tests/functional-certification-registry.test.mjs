import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { declaredRoutePaths, verifyFunctionalCertificationRegistry } from "../check-functional-certification.mjs";

test("every router path declaration has a complete functional certification entry", () => {
  const result = verifyFunctionalCertificationRegistry();

  assert.ok(result.registryEntries > 0);
  assert.ok(result.routerPathDeclarations > 0);
  assert.ok(result.uniqueRouterPaths > 0);
});

test("route inventory follows split modules and static metadata, ignoring commented paths", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "crm-route-inventory-"));
  try {
    const router = path.join(directory, "router.tsx");
    fs.writeFileSync(router, 'import { featureRoutes } from "./features"; const routes = [{path: "/app", children: featureRoutes}]; // path: "fake"');
    fs.writeFileSync(path.join(directory, "features.tsx"), 'import { routeMetadata } from "./routeMetadata"; export const featureRoutes = [{path: routeMetadata.records.segment}, {path: "records/:id"}];');
    fs.writeFileSync(path.join(directory, "routeMetadata.ts"), 'export const routeMetadata = {records: {path: "/app/records", segment: "records"}} as const;');
    assert.deepEqual(declaredRoutePaths(router), ["/app", "records", "records/:id"]);
    fs.appendFileSync(path.join(directory, "features.tsx"), '\nconst unsupported = {path: computePath()};');
    assert.throws(() => declaredRoutePaths(router), /Unresolved router path/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
