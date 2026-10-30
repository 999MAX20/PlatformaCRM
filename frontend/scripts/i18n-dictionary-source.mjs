import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

// Inspect literal dictionaries and their domain imports without executing application code.
export function dictionaryBlock(name, directory = path.resolve("src/lib/i18n")) {
  const active = new Set();
  function read(file, exportedName) {
    const key = `${file}:${exportedName}`;
    if (active.has(key)) throw new Error(`Circular dictionary import: ${key}`);
    active.add(key);
    const source = fs.readFileSync(file, "utf8");
    const ast = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true);
    const imports = new Map();
    for (const node of ast.statements) {
      if (!ts.isImportDeclaration(node)) continue;
      const bindings = node.importClause?.namedBindings;
      if (!bindings || !ts.isNamedImports(bindings)) throw new Error(`Unsupported dictionary import: ${file}`);
      for (const binding of bindings.elements) imports.set(binding.name.text, {
        file: path.resolve(path.dirname(file), `${node.moduleSpecifier.text}.ts`),
        name: binding.propertyName?.text ?? binding.name.text,
      });
    }
    const declaration = ast.statements.filter(ts.isVariableStatement)
      .flatMap(node => node.declarationList.declarations)
      .find(node => ts.isIdentifier(node.name) && node.name.text === exportedName);
    if (!declaration?.initializer || !ts.isObjectLiteralExpression(declaration.initializer)) throw new Error(`Dictionary ${exportedName} not found in ${file}`);
    const entries = [];
    for (const node of declaration.initializer.properties) {
      if (ts.isPropertyAssignment(node) && ts.isStringLiteral(node.name) && ts.isStringLiteral(node.initializer)) {
        entries.push(`${JSON.stringify(node.name.text)}: ${JSON.stringify(node.initializer.text)},`);
      } else if (ts.isSpreadAssignment(node) && ts.isIdentifier(node.expression)) {
        const imported = imports.get(node.expression.text);
        if (!imported) throw new Error(`Unknown dictionary spread in ${file}`);
        // Preserve the existing explicit-translation parity check: Russian fallback
        // cannot make a missing KK/EN translation pass.
        if (imported.name === "ru" && path.basename(imported.file) === "ru.ts") entries.push("...ru,");
        else entries.push(read(imported.file, imported.name));
      } else throw new Error(`Nonliteral dictionary entry in ${file}`);
    }
    active.delete(key);
    return entries.join("\n");
  }
  return read(path.join(directory, `${name}.ts`), name);
}
