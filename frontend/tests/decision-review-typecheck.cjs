// Check new TS modules only; full repo checks remain a separate VM gate.
const ts = require('typescript');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const parsed = ts.readConfigFile(path.join(root, 'tsconfig.json'), ts.sys.readFile);
if (parsed.error) throw Error('Cannot read TypeScript config');
const options = ts.convertCompilerOptionsFromJson(parsed.config.compilerOptions, root).options;
Object.assign(options, {
  incremental: false, noEmit: true, types: ['node'],
  typeRoots: [path.dirname(path.dirname(require.resolve('@types/node/package.json')))],
  paths: { '@/*': ['./src/*'], 'next/server': [path.join(path.dirname(require.resolve('next/package.json')), 'server.d.ts')] },
});
const files = ['src/lib/decision-review.ts', 'src/lib/retired-summary.ts', 'src/app/api/nexus/v1/decisions/route.ts', ...['copilot/draft','copilot/review','copilot/evidence','summary'].map(route => 'src/app/api/nexus/v1/' + route + '/route.ts')].map(file => path.join(root, file));
const program = ts.createProgram(files, options);
const diagnostics = ts.getPreEmitDiagnostics(program);
for (const diagnostic of diagnostics) console.error(ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n'));
if (diagnostics.length) process.exitCode = 1;
else console.log('NEW_DECISION_TYPESCRIPT_FILES_TYPECHECK=PASS; FULL_PROJECT_TYPECHECK_NOT_RUN');
