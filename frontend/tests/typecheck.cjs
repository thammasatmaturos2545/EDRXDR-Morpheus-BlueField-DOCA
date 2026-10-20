const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const dependencyRoot = path.dirname(require.resolve('typescript/package.json'));
const modules = path.dirname(dependencyRoot);
const options = { noEmit: true, strict: true, skipLibCheck: true,
  target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
  moduleResolution: ts.ModuleResolutionKind.Node10, esModuleInterop: true,
  baseUrl: root, typeRoots: [path.join(modules, '@types')], types: ['node'],
  paths: { '@/lib/history-auth': ['tests/fixtures/history-auth.ts'],
    '@/lib/*': ['src/lib/*'], 'next/server': [path.join(modules, 'next/server.d.ts')] } };
const program = ts.createProgram([
  path.join(root, 'src/lib/nexus-summary/core.ts'),
  path.join(root, 'src/app/api/nexus/v1/summary/route.ts'),
], options);
const errors = ts.getPreEmitDiagnostics(program);
if (errors.length) {
  console.error(ts.formatDiagnosticsWithColorAndContext(errors, {
    getCurrentDirectory: () => root, getCanonicalFileName: x => x, getNewLine: () => '\n',
  })); process.exitCode = 1;
} else console.log('PASS isolated strict typecheck; installed Next.js types and operator auth snapshot');
