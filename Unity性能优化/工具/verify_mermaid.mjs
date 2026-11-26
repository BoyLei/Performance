// Syntax parsing only; does not render or execute Obsidian plugins.
// npm install --prefix /tmp/vault-verify-tools mermaid@11.12.2 jsdom@26
// node /absolute/path/to/verify_mermaid.mjs /tmp/vault-verify-tools/node_modules
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
const modules = process.argv[2];
if (!modules) throw new Error('Pass the external node_modules directory as argument');
const {JSDOM} = await import(pathToFileURL(path.resolve(modules, 'jsdom/lib/api.js')));
const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const {default: mermaid} = await import(pathToFileURL(path.resolve(modules, 'mermaid/dist/mermaid.esm.mjs')));
mermaid.initialize({startOnLoad: false, securityLevel: 'strict'});
const vault = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let count = 0;
const errors = [];
for (const name of fs.readdirSync(vault).filter(name => name.endsWith('.md')).sort()) {
  const source = fs.readFileSync(path.join(vault, name), 'utf8');
  for (const [, code] of source.matchAll(/^```mermaid\s*\n([\s\S]*?)^```\s*$/gm)) {
    count++;
    try { await mermaid.parse(code); }
    catch (e) { errors.push({name, error: String(e)}); }
  }
}
console.log(JSON.stringify({mermaid: '11.12.2', blocks: count, errors, rendering: 'NOT TESTED'}, null, 2));
process.exitCode = errors.length ? 1 : 0;
