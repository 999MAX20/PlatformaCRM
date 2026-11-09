import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

import { routeActionRegistry } from "../e2e/certification/route-action-registry.mjs";
import { expectedActionOutcome } from "../e2e/certification/action-outcome-contracts.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, "..");

const requiredFields = [
  "id",
  "route",
  "aliases",
  "routerPaths",
  "page",
  "group",
  "guard",
  "roles",
  "capabilities",
  "pageReadyMarker",
  "primaryActions",
  "secondaryActions",
  "controls",
  "apiEndpoints",
  "entities",
  "viewports",
  "fixtures",
  "automatedTests",
  "status",
];

const allowedStatuses = new Set(["NOT_RUN", "PASS", "FAIL", "BLOCKED", "EXCLUDED"]);

function counts(values) {
  const result = new Map();
  for (const value of values) result.set(value, (result.get(value) || 0) + 1);
  return result;
}

function countDiff(expected, actual) {
  const keys = new Set([...expected.keys(), ...actual.keys()]);
  return [...keys]
    .sort()
    .filter((key) => expected.get(key) !== actual.get(key))
    .map((key) => `${key}: registry=${expected.get(key) || 0}, router=${actual.get(key) || 0}`);
}

export function declaredRoutePaths(routerPath) {
  const visited = new Set();
  const paths = [];
  function visitFile(file) {
    if (visited.has(file)) return;
    visited.add(file);
    const source = fs.readFileSync(file, "utf8");
    const ast = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    let metadata;
    function metadataSegment(key) {
      if (!metadata) {
        const location = path.join(path.dirname(file), "routeMetadata.ts");
        const metadataAst = ts.createSourceFile(location, fs.readFileSync(location, "utf8"), ts.ScriptTarget.Latest, true);
        const declaration = metadataAst.statements.filter(ts.isVariableStatement)
          .flatMap(statement => [...statement.declarationList.declarations])
          .find(item => item.name.getText(metadataAst) === "routeMetadata");
        let object = declaration?.initializer;
        while (object && (ts.isSatisfiesExpression(object) || ts.isAsExpression(object))) object = object.expression;
        if (!object || !ts.isObjectLiteralExpression(object)) throw new Error("Route metadata must be a static object");
        metadata = new Map(object.properties.filter(ts.isPropertyAssignment).map(item => {
          const segment = ts.isObjectLiteralExpression(item.initializer)
            ? item.initializer.properties.find(property => ts.isPropertyAssignment(property) && property.name.getText(metadataAst) === "segment") : null;
          return [item.name.getText(metadataAst), segment && ts.isStringLiteral(segment.initializer) ? segment.initializer.text : undefined];
        }));
      }
      const value = metadata.get(key);
      if (!value) throw new Error(`Unresolved route metadata segment: ${key}`);
      return value;
    }
    function visit(node) {
      if (ts.isPropertyAssignment(node) && node.name.getText(ast) === "path") {
        if (ts.isStringLiteral(node.initializer)) paths.push(node.initializer.text);
        else {
          const expression = node.initializer.getText(ast);
          const match = /^routeMetadata\.(\w+)\.segment$/.exec(expression);
          if (match) paths.push(metadataSegment(match[1]));
          else if (expression !== "route.path") throw new Error(`Unresolved router path: ${expression}`);
        }
      }
      ts.forEachChild(node, visit);
    }
    visit(ast);
    for (const statement of ast.statements) {
      if (!ts.isImportDeclaration(statement) || !ts.isStringLiteral(statement.moduleSpecifier)) continue;
      const bindings = statement.importClause?.namedBindings;
      if (!bindings || !ts.isNamedImports(bindings) || !bindings.elements.some(item => /Routes$/.test((item.propertyName || item.name).text))) continue;
      const relative = statement.moduleSpecifier.text;
      if (!relative.startsWith(".")) throw new Error(`Route module must be local: ${relative}`);
      const base = path.resolve(path.dirname(file), relative);
      const target = [base, `${base}.tsx`, `${base}.ts`].find(candidate => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
      if (!target) throw new Error(`Route module not found: ${relative}`);
      visitFile(target);
    }
  }
  visitFile(routerPath);
  return paths;
}

export function verifyFunctionalCertificationRegistry({ rootDir = frontendDir } = {}) {
  const errors = [];
  const routerPaths = declaredRoutePaths(path.join(rootDir, "src", "app", "router.tsx"));

  const ids = new Set();
  for (const [index, entry] of routeActionRegistry.entries()) {
    for (const field of requiredFields) {
      if (!(field in entry)) errors.push(`entry ${index} (${entry.id || "unknown"}) is missing ${field}`);
    }
    if (ids.has(entry.id)) errors.push(`duplicate registry id: ${entry.id}`);
    ids.add(entry.id);
    if (!Array.isArray(entry.routerPaths) || entry.routerPaths.length === 0) {
      errors.push(`${entry.id} has no routerPaths`);
    }
    if (!Array.isArray(entry.roles) || entry.roles.length === 0) {
      errors.push(`${entry.id} has no supported roles`);
    }
    if (!Array.isArray(entry.viewports) || entry.viewports.length === 0) {
      errors.push(`${entry.id} has no viewport classes`);
    }
    if (!allowedStatuses.has(entry.status)) {
      errors.push(`${entry.id} has invalid status ${entry.status}`);
    }
    for (const action of [...entry.primaryActions, ...entry.secondaryActions]) {
      if (!expectedActionOutcome(action)) errors.push(`${entry.id}/${action} has no expected-result contract`);
    }
    for (const testLocation of entry.automatedTests || []) {
      if (!fs.existsSync(path.join(rootDir, testLocation))) {
        errors.push(`${entry.id} references missing test ${testLocation}`);
      }
    }
  }

  const registeredPaths = routeActionRegistry.flatMap((entry) => entry.routerPaths);
  errors.push(...countDiff(counts(registeredPaths), counts(routerPaths)));

  if (errors.length) {
    throw new Error(`Functional certification registry is invalid:\n- ${errors.join("\n- ")}`);
  }

  return {
    registryEntries: routeActionRegistry.length,
    routerPathDeclarations: routerPaths.length,
    uniqueRouterPaths: new Set(routerPaths).size,
  };
}

const invokedPath = process.argv[1] ? pathToFileURL(path.resolve(process.argv[1])).href : "";
if (invokedPath === import.meta.url) {
  const result = verifyFunctionalCertificationRegistry();
  console.log(
    `Functional certification registry OK: ${result.registryEntries} entries cover ` +
      `${result.routerPathDeclarations} router path declarations (${result.uniqueRouterPaths} unique).`,
  );
}
