/**
 * One frozen, offline repetition. This file is infrastructure only.
 * It never installs dependencies, fetches sources, creates a source variant,
 * edits original tests/configuration, or changes the frozen evaluation scope.
 *
 * The installed manifest uses paths relative to /opt/replay/seed:
 * {baseline_commit,entries:[{path,type:"file"|"symlink",bytes?,sha256?,target?}]}.
 * Evidence is exported even for ineligible runs; individual Jest exits remain
 * distinct from this infrastructure process's completion status.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { gzipSync } from 'node:zlib';

const ROOT = '/opt/replay';
const PROJECT = '/work/project';
const OUT = '/work/evidence';
const BASE = 'b86530c6c656b7a8f72d42145e9d46995c7ab53d';
const BASE_TREE = 'cae8a86926869f4d8708ae17f19f5bf4ef4a6526';
const CHANGED = 'shared/authentication/src/auth.definition.ts';
const GUARD_FILE = 'tests/unit/authentication/cookie-config.test.ts';
const GUARD = 'auth.definition.ts cookie configuration should not use sameSite: none (weakens CSRF protection)';
const GUARD_BLOB = '5c14cd837a04880807d3ef4f643da64cbdf6a552';
const EXPECTED_MANIFEST_HASHES = {
  baseline: '9d84f6dc000c7ac30f85006b81861f8663046f50aa9b0be05f2b14c1dcae2858',
  candidate: '4d85df064369799cb833391176798623c436d094ec0805fd467338c843995986',
};
const MAX_LOG_BYTES = 64 * 1024 * 1024;
const MAX_REPORT_BYTES = 128 * 1024 * 1024;
const evidence = {
  schema_version: 1,
  started_at: new Date().toISOString(),
  status: 'INITIALIZING',
  scope: 'All 471 unchanged upstream unit-test files; not the integration suite. One exact historical production-hunk reversion. Security source-policy guard, not runtime CSRF or fingerprint-mechanism evidence.',
  states: [], arms: {}, conditions: {}, qualifying_joint_witness: false,
  observation_limit: 'Jest case results do not expose independent hook/call phases. Pending/todo/skipped results are not executed calls. The designated security failure must bind to its unchanged expectation source line; setup/runtime errors do not qualify.',
};
let activeChild = null;
let interrupted = null;
let installedEntries = [];
let baselineRows = [];
let candidateRows = [];
let protocol;
const env = {
  PATH: '/usr/local/bin:/usr/bin:/bin', HOME: '/work/home',
  TMPDIR: '/work/tmp', XDG_CACHE_HOME: '/work/cache',
  LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', TZ: 'UTC',
  CI: 'true', NODE_ENV: 'test', EMAIL_ENABLED: 'false',
  NPM_TOKEN: '', NPM_CONFIG_CACHE: '/work/npm-cache',
  GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null',
  GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0',
};

class Ineligible extends Error {
  constructor(code, detail) { super(detail); this.code = code; }
}
function requireCondition(condition, code, detail) {
  if (!condition) throw new Ineligible(code, detail);
}
function sha(data, algorithm = 'sha256') {
  return crypto.createHash(algorithm).update(data).digest('hex');
}
function fileHash(filename) { return sha(fs.readFileSync(filename)); }
function blobHash(bytes) {
  return sha(Buffer.concat([Buffer.from('blob ' + bytes.length + '\0'), bytes]), 'sha1');
}
function loadJson(filename) { return JSON.parse(fs.readFileSync(filename, 'utf8')); }
function safeRelative(relative) {
  requireCondition(typeof relative === 'string' && relative.length > 0 &&
    !path.isAbsolute(relative) && !relative.includes('\\') &&
    !relative.split('/').some(x => x === '..' || x === ''),
  'INVALID_MANIFEST_PATH', String(relative));
  return path.join(PROJECT, relative);
}
function git(args) {
  const result = spawnSync('git', ['--no-pager', '-c', 'core.fsmonitor=false',
    '-c', 'core.hooksPath=/dev/null', ...args],
  { cwd: PROJECT, env, encoding: 'utf8', timeout: 15000, maxBuffer: 16 * 1024 * 1024 });
  requireCondition(!result.error && result.status === 0, 'GIT_METADATA_ERROR',
    JSON.stringify({args, status: result.status, error: String(result.error || ''), stderr: result.stderr}));
  return result.stdout;
}
function gitState() {
  return {
    head: git(['rev-parse', 'HEAD']).trim(),
    tree: git(['rev-parse', 'HEAD^{tree}']).trim(),
    origin_main: git(['rev-parse', 'refs/remotes/origin/main']).trim(),
    status_porcelain_z: git(['status', '--porcelain=v1', '-z', '--untracked-files=normal']),
    changed_from_base: git(['diff', '--no-ext-diff', '--name-only', '-z', BASE]).split('\0').filter(Boolean),
    index_sha256: fileHash(path.join(PROJECT, '.git/index')),
  };
}
function dependencyInventory() {
  const entries = [];
  const pending = [{absolute: PROJECT, relative: '', inside: false}];
  while (pending.length) {
    const current = pending.pop();
    for (const item of fs.readdirSync(current.absolute, {withFileTypes: true})) {
      if (!current.relative && item.name === '.git') continue;
      const relative = current.relative ? current.relative + '/' + item.name : item.name;
      const absolute = path.join(current.absolute, item.name);
      const inside = current.inside || item.name === 'node_modules';
      if (item.isSymbolicLink()) {
        if (inside) entries.push({path: relative, type: 'symlink'});
      } else if (item.isDirectory()) {
        pending.push({absolute, relative, inside});
      } else if (inside) {
        entries.push({path: relative, type: item.isFile() ? 'file' : 'unsupported'});
      }
    }
  }
  return entries.sort((a, b) => a.path.localeCompare(b.path));
}
function artifactInventory(directory) {
  if (!fs.existsSync(directory)) return {directory, entries: [], sha256: sha('[]')};
  const entries = [];
  const pending = [directory];
  while (pending.length) {
    const current = pending.pop();
    for (const item of fs.readdirSync(current, {withFileTypes: true})) {
      const filename = path.join(current, item.name);
      const relative = path.relative(directory, filename).split(path.sep).join('/');
      if (item.isSymbolicLink()) entries.push({path: relative, type: 'symlink', target: fs.readlinkSync(filename)});
      else if (item.isDirectory()) pending.push(filename);
      else if (item.isFile()) entries.push({path: relative, type: 'file', bytes: fs.statSync(filename).size, sha256: fileHash(filename)});
      else entries.push({path: relative, type: 'unsupported'});
    }
  }
  entries.sort((a, b) => a.path.localeCompare(b.path));
  return {directory, entries, sha256: sha(JSON.stringify(entries)),
    content_export: 'File/hash inventory only; raw Jest JSON/stdout/stderr are embedded separately.'};
}
function verifyInstalled() {
  const mismatch = [];
  const actual = [];
  const expectedTypes = new Map(installedEntries.map(entry => [entry.path, entry.type]));
  const inventory = dependencyInventory();
  const actualTypes = new Map(inventory.map(entry => [entry.path, entry.type]));
  for (const [filename, type] of expectedTypes) {
    if (actualTypes.get(filename) !== type) mismatch.push({path: filename, error: 'Missing dependency entry or changed type', expected_type: type, actual_type: actualTypes.get(filename)});
  }
  for (const [filename, type] of actualTypes) {
    if (!expectedTypes.has(filename)) mismatch.push({path: filename, type, error: 'Additional unmanifested dependency entry'});
  }
  for (const entry of installedEntries) {
    const filename = safeRelative(entry.path);
    let row;
    try {
      const st = fs.lstatSync(filename);
      if (entry.type === 'symlink') {
        const target = fs.readlinkSync(filename);
        row = {path: entry.path, type: 'symlink', target};
        if (!st.isSymbolicLink() || target !== entry.target) mismatch.push(row);
        const resolved = fs.realpathSync(filename);
        if (!resolved.startsWith(PROJECT + '/')) mismatch.push({path: entry.path, error: 'Installed link resolves outside copied checkout', resolved});
      } else if (entry.type === 'file') {
        row = {path: entry.path, type: 'file', bytes: st.size, sha256: fileHash(filename)};
        if (!st.isFile() || row.sha256 !== entry.sha256 ||
            (entry.bytes !== undefined && row.bytes !== entry.bytes)) mismatch.push(row);
      } else {
        mismatch.push({path: entry.path, error: 'Unsupported installed-manifest entry type'});
      }
      if (row) actual.push(row);
    } catch (error) { mismatch.push({path: entry.path, error: String(error)}); }
  }
  return {checked_entries: installedEntries.length, matches: mismatch.length === 0,
    actual_dependency_entry_count: inventory.length, actual_path_type_inventory_sha256: sha(JSON.stringify(inventory)),
    actual_entries_sha256: sha(JSON.stringify(actual)), mismatches: mismatch};
}
function checkState(label, rows, expectCandidate) {
  const files = {};
  const mismatch = [];
  for (const row of rows) {
    try {
      const filename = safeRelative(row.path);
      const st = fs.lstatSync(filename);
      const bytes = fs.readFileSync(filename);
      const observed = {sha256: sha(bytes), git_blob: blobHash(bytes), bytes: bytes.length,
        executable: (st.mode & 0o111) !== 0};
      files[row.path] = observed;
      if (!st.isFile() || observed.sha256 !== row.sha256 || observed.git_blob !== row.git_blob ||
          observed.bytes !== row.size || observed.executable !== (row.mode === '100755')) {
        mismatch.push({path: row.path, expected: row, observed});
      }
    } catch (error) { mismatch.push({path: row.path, error: String(error)}); }
  }
  const gs = gitState();
  const expectedStatus = expectCandidate ? ' M ' + CHANGED + '\0' : '';
  const installed = verifyInstalled();
  const state = {label, recorded_at: new Date().toISOString(), files,
    tracked_tree_sha256: sha(JSON.stringify(files)), source_mismatches: mismatch,
    tests_and_configuration_unchanged: mismatch.every(x => x.path === CHANGED),
    git: gs, installed_identity: installed};
  evidence.states.push(state);
  requireCondition(mismatch.length === 0, 'SOURCE_IDENTITY_FAILURE', label + ': original tracked input mismatch');
  requireCondition(gs.head === BASE && gs.tree === BASE_TREE && gs.origin_main === BASE,
    'GIT_BASE_IDENTITY_FAILURE', label + ': Git baseline/reference changed');
  requireCondition(gs.status_porcelain_z === expectedStatus &&
    JSON.stringify(gs.changed_from_base) === JSON.stringify(expectCandidate ? [CHANGED] : []),
  'WORKTREE_IDENTITY_FAILURE', label + ': unexpected tracked/untracked working-tree changes');
  requireCondition(installed.matches, 'INSTALLED_IDENTITY_FAILURE', label + ': installed dependency identity changed');
  return state;
}
function readSmallMetadata() {
  const names = ['INPUT_IDENTITY.json', 'PROTOCOL_PREDECLARATION.json',
    'FROZEN_PROTOCOL.json', 'PROTOCOL.md', 'seed-installed-manifest.json'];
  const result = {};
  for (const name of names) {
    const filename = path.join(ROOT, name);
    if (fs.existsSync(filename)) {
      const bytes = fs.readFileSync(filename);
      result[name] = {bytes: bytes.length, sha256: sha(bytes)};
      if (name !== 'seed-installed-manifest.json') result[name].text = bytes.toString('utf8');
    }
  }
  return result;
}
function killGroup(signal) {
  if (!activeChild?.pid) return;
  try { process.kill(-activeChild.pid, signal); }
  catch { try { activeChild.kill(signal); } catch {} }
}
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => { interrupted = signal; killGroup('SIGTERM'); });
}
function assertionIdentity(assertion) {
  return assertion.file + '\0' + assertion.full_name;
}
function multiset(values) {
  const map = {};
  for (const value of values) map[value] = (map[value] || 0) + 1;
  return Object.fromEntries(Object.entries(map).sort(([a], [b]) => a.localeCompare(b)));
}
function summarizeJest(report, processResult, guardLine) {
  const assertions = [];
  const suiteErrors = [];
  const suites = [];
  for (const suite of report.testResults || []) {
    const filename = typeof suite.name === 'string' ? path.relative(PROJECT, suite.name).split(path.sep).join('/') : null;
    suites.push({file: filename, status: suite.status, message: suite.message || '',
      assertion_count: (suite.assertionResults || []).length, test_exec_error: suite.testExecError || null});
    if (!filename || filename.startsWith('../') || suite.testExecError ||
        (suite.status === 'failed' && !(suite.assertionResults || []).length)) {
      suiteErrors.push({file: filename, message: suite.message || '', test_exec_error: suite.testExecError || null});
    }
    for (const item of suite.assertionResults || []) {
      assertions.push({file: filename, full_name: item.fullName, title: item.title,
        ancestor_titles: item.ancestorTitles, status: item.status, duration: item.duration,
        failure_messages: item.failureMessages || [], failure_details: item.failureDetails || []});
    }
  }
  const counts = {passed: 0, failed: 0, pending: 0, todo: 0, skipped: 0, other: 0};
  for (const item of assertions) {
    if (Object.hasOwn(counts, item.status)) counts[item.status]++;
    else counts.other++;
  }
  const guards = assertions.filter(x => x.file === GUARD_FILE && x.full_name === GUARD);
  const trace = new RegExp('cookie-config\\.test\\.ts:' + guardLine + ':\\d+');
  const guardAssertionFailure = guards.length === 1 && guards[0].status === 'failed' &&
    guards[0].failure_messages.some(message =>
      message.includes('not.toMatch') && message.includes('sameSite') && trace.test(message));
  const runtimeErrors = report.numRuntimeErrorTestSuites || 0;
  const infrastructureEligible = !processResult.timed_out && !processResult.output_limit_exceeded &&
    !processResult.signal && !processResult.spawn_error && [0, 1].includes(processResult.exit_code) &&
    !report.wasInterrupted && runtimeErrors === 0 && suiteErrors.length === 0 &&
    counts.other === 0 && Array.isArray(report.testResults);
  return {assertions, counts, suites, suite_errors: suiteErrors,
    reported_totals: Object.fromEntries(Object.entries(report).filter(([key]) => /^num/.test(key))),
    success: report.success, was_interrupted: !!report.wasInterrupted,
    infrastructure_eligible: infrastructureEligible,
    designated_guard_results: guards, designated_guard_assertion_failure: guardAssertionFailure,
    executed_case_results: counts.passed + counts.failed,
    completed_passing_calls: counts.passed,
    failed_case_phase_limit: 'A failed Jest case may originate in a hook. The designated guard needs an expectation-line-bound failure; failed-case counts alone are not phase proof.'};
}
async function runArm(name, selective, guardLine) {
  if (interrupted) throw new Ineligible('INTERRUPTED', interrupted);
  const armDir = path.join(OUT, name);
  fs.mkdirSync(armDir, {recursive: true});
  const cacheDir = path.join(OUT, selective || name === 'baseline' ? 'native-cache' : 'independent-cache');
  fs.mkdirSync(cacheDir, {recursive: true});
  const jsonPath = path.join(armDir, 'jest.json');
  const args = ['node_modules/jest/bin/jest.js', '--config', 'jest.unit.config.ts',
    '--coverage', '--runInBand', '--json', '--outputFile=' + jsonPath,
    '--coverageDirectory=' + path.join(armDir, 'coverage'), '--cacheDirectory=' + cacheDir];
  if (selective) args.push('--changedSince=origin/main', '--passWithNoTests');
  const arm = {command: [process.execPath, ...args], cwd: PROJECT, environment: {...env},
    cache_directory: cacheDir, cache_before: artifactInventory(cacheDir), started_at: new Date().toISOString()};
  evidence.arms[name] = arm;
  const stdoutPath = path.join(armDir, 'stdout.txt');
  const stderrPath = path.join(armDir, 'stderr.txt');
  const stdoutFd = fs.openSync(stdoutPath, 'w');
  const stderrFd = fs.openSync(stderrPath, 'w');
  let byteCounts = {stdout: 0, stderr: 0};
  const processResult = {exit_code: null, signal: null, timed_out: false,
    output_limit_exceeded: false, spawn_error: null};
  await new Promise(resolve => {
    let child;
    try {
      child = spawn(process.execPath, args, {cwd: PROJECT, env, detached: true,
        stdio: ['ignore', 'pipe', 'pipe']});
    } catch (error) { processResult.spawn_error = String(error); resolve(); return; }
    activeChild = child;
    let hardKill;
    const terminate = () => {
      killGroup('SIGTERM');
      hardKill ||= setTimeout(() => killGroup('SIGKILL'), 2000);
    };
    const timer = setTimeout(() => { processResult.timed_out = true; terminate(); },
      protocol.lab.jest_timeout_seconds * 1000);
    const capture = (stream, fd) => chunk => {
      byteCounts[stream] += chunk.length;
      if (byteCounts[stream] <= MAX_LOG_BYTES) {
        try { fs.writeSync(fd, chunk); }
        catch (error) { processResult.spawn_error = 'Evidence write failed: ' + String(error); terminate(); }
      } else {
        processResult.output_limit_exceeded = true;
        terminate();
      }
    };
    child.stdout.on('data', capture('stdout', stdoutFd));
    child.stderr.on('data', capture('stderr', stderrFd));
    child.on('error', error => { processResult.spawn_error = String(error); });
    child.on('close', (code, signal) => {
      clearTimeout(timer);
      if (hardKill) clearTimeout(hardKill);
      processResult.exit_code = code; processResult.signal = signal;
      activeChild = null; resolve();
    });
  });
  fs.closeSync(stdoutFd); fs.closeSync(stderrFd);
  arm.process = {...processResult, output_observed_bytes: byteCounts,
    inherited_interruption: interrupted};
  arm.stdout = fs.readFileSync(stdoutPath, 'utf8');
  arm.stderr = fs.readFileSync(stderrPath, 'utf8');
  arm.finished_at = new Date().toISOString();
  arm.cache_after = artifactInventory(cacheDir);
  arm.coverage_artifacts = artifactInventory(path.join(armDir, 'coverage'));
  if (fs.existsSync(jsonPath) && fs.statSync(jsonPath).size <= MAX_REPORT_BYTES) {
    arm.raw_jest_json = fs.readFileSync(jsonPath, 'utf8');
    arm.raw_jest_json_sha256 = sha(arm.raw_jest_json);
    try { arm.summary = summarizeJest(JSON.parse(arm.raw_jest_json), processResult, guardLine); }
    catch (error) { arm.report_error = String(error); }
  } else {
    arm.report_error = fs.existsSync(jsonPath) ? 'Jest report exceeded declared evidence limit' : 'No Jest JSON report';
  }
  if (interrupted) throw new Ineligible('INTERRUPTED', interrupted);
  return arm;
}
function verifyCompleteScope(arm, baselineSummary = null) {
  const expected = baselineRows.filter(row => /^tests\/unit\/.*\.test\.ts$/.test(row.path)).map(row => row.path).sort();
  const observed = (arm.summary?.suites || []).map(row => row.file).sort();
  requireCondition(JSON.stringify(expected) === JSON.stringify(observed),
    'COMPLETE_SCOPE_MISMATCH', 'Full configured unit execution did not report exactly the original 471 files');
  if (baselineSummary) {
    requireCondition(JSON.stringify(multiset(arm.summary.assertions.map(assertionIdentity))) ===
      JSON.stringify(multiset(baselineSummary.assertions.map(assertionIdentity))),
    'TEST_UNIVERSE_CHANGED', 'Independent candidate cases differ from baseline original case identities');
  }
}
async function main() {
  fs.mkdirSync(OUT, {recursive: true});
  for (const dir of ['/work/home', '/work/tmp', '/work/cache', '/work/npm-cache']) fs.mkdirSync(dir, {recursive: true});
  evidence.frozen_metadata = readSmallMetadata();
  const protocolPath = fs.existsSync(path.join(ROOT, 'FROZEN_PROTOCOL.json'))
    ? path.join(ROOT, 'FROZEN_PROTOCOL.json') : path.join(ROOT, 'PROTOCOL_PREDECLARATION.json');
  protocol = loadJson(protocolPath);
  evidence.protocol_file = {path: protocolPath, sha256: fileHash(protocolPath)};
  evidence.protocol = protocol;
  requireCondition(protocol.baseline === BASE && protocol.target === GUARD &&
    protocol.target_blob === GUARD_BLOB && protocol.git_base?.revision === BASE &&
    protocol.git_base?.reference === 'refs/remotes/origin/main' &&
    protocol.lab?.jest_timeout_seconds === 900 && protocol.fresh_container_and_baseline_each === true,
  'PROTOCOL_MISMATCH', 'Frozen protocol identity or timeout differs from implemented plan');
  evidence.input_identity = loadJson(path.join(ROOT, 'INPUT_IDENTITY.json'));
  const status = fs.readFileSync('/proc/self/status', 'utf8');
  const statusValue = name => status.match(new RegExp('^' + name + ':\\s*(.+)$', 'm'))?.[1].trim();
  const mounts = fs.readFileSync('/proc/self/mountinfo', 'utf8').split('\n').filter(Boolean);
  const mountRecord = mountpoint => {
    const line = mounts.find(x => x.split(' ')[4] === mountpoint);
    if (!line) return null;
    const [left, right] = line.split(' - ');
    return {options: left.split(' ')[5], filesystem: right.split(' ')[0]};
  };
  evidence.runtime = {uid: process.getuid(), gid: process.getgid(), node: process.version,
    capabilities: statusValue('CapEff'), no_new_privileges: statusValue('NoNewPrivs'),
    seccomp: statusValue('Seccomp'), interfaces: fs.readdirSync('/sys/class/net').sort(),
    root_mount: mountRecord('/'), work_mount: mountRecord('/work'), tmp_mount: mountRecord('/tmp'),
    docker_socket_present: fs.existsSync('/var/run/docker.sock')};
  requireCondition(evidence.runtime.uid === 10001 && evidence.runtime.gid === 10001 &&
    evidence.runtime.capabilities === '0000000000000000' &&
    evidence.runtime.no_new_privileges === '1' && evidence.runtime.seccomp === '2' &&
    JSON.stringify(evidence.runtime.interfaces) === '["lo"]' &&
    evidence.runtime.root_mount?.options.split(',').includes('ro') &&
    evidence.runtime.work_mount?.filesystem === 'tmpfs' &&
    !evidence.runtime.work_mount.options.split(',').includes('noexec') &&
    !evidence.runtime.docker_socket_present,
  'RUNTIME_BOUNDARY_MISMATCH', 'Offline/private writable execution boundary does not match protocol');
  const inputDir = path.join(ROOT, 'input');
  evidence.input_manifests = {};
  for (const [kind, expectedHash] of Object.entries(EXPECTED_MANIFEST_HASHES)) {
    const filename = path.join(inputDir, kind + '-source-manifest.json');
    const bytes = fs.readFileSync(filename);
    const parsed = JSON.parse(bytes);
    // prepare_inputs.py pins compact UTF-8 JSON with original property order
    // and a trailing newline; the on-disk pretty-printed receipt differs.
    const canonicalHash = sha(Buffer.from(JSON.stringify(parsed) + '\n'));
    evidence.input_manifests[kind] = {raw_sha256: sha(bytes), canonical_sha256: canonicalHash,
      canonicalization: 'compact JSON preserving array/property order, UTF-8, trailing newline', bytes: bytes.length};
    requireCondition(canonicalHash === expectedHash, 'INPUT_MANIFEST_MISMATCH', kind);
    if (kind === 'baseline') baselineRows = parsed;
    else candidateRows = parsed;
  }
  requireCondition(baselineRows.length === 1869 && candidateRows.length === 1869,
    'TRACKED_SCOPE_MISMATCH', 'Expected exactly 1869 original tracked paths');
  const baseMap = new Map(baselineRows.map(row => [row.path, row]));
  requireCondition(new Set(candidateRows.map(row => row.path)).size === 1869 &&
    candidateRows.every(row => baseMap.has(row.path) && row.mode === baseMap.get(row.path).mode),
  'CANDIDATE_MANIFEST_SHAPE_MISMATCH', 'Candidate path/mode set differs');
  const changes = candidateRows.filter(row => row.sha256 !== baseMap.get(row.path).sha256).map(row => row.path);
  requireCondition(JSON.stringify(changes) === JSON.stringify([CHANGED]),
    'FIXED_CANDIDATE_SCOPE_MISMATCH', 'More than the frozen production source differs');
  const unitRows = baselineRows.filter(row => /^tests\/unit\/.*\.test\.ts$/.test(row.path));
  requireCondition(unitRows.length === 471 && baseMap.get(GUARD_FILE)?.git_blob === GUARD_BLOB,
    'ORIGINAL_TEST_SCOPE_MISMATCH', 'Original unit universe or guard blob differs');
  const originalTestManifestPath = path.join(inputDir, 'original-unit-test-manifest.json');
  if (fs.existsSync(originalTestManifestPath)) {
    const originalRows = loadJson(originalTestManifestPath);
    requireCondition(JSON.stringify(originalRows) === JSON.stringify(unitRows),
      'ORIGINAL_TEST_MANIFEST_MISMATCH', 'Original unit manifest differs from frozen baseline rows');
    evidence.input_manifests.original_unit_tests = {sha256: fileHash(originalTestManifestPath), files: originalRows.length};
  }
  const installedPath = path.join(ROOT, 'seed-installed-manifest.json');
  const installedManifest = loadJson(installedPath);
  requireCondition(installedManifest.baseline_commit === BASE && Array.isArray(installedManifest.entries) &&
    installedManifest.entries.length > 0, 'INSTALLED_MANIFEST_INVALID', 'Missing frozen installed entries/baseline');
  installedEntries = installedManifest.entries;
  requireCondition(new Set(installedEntries.map(entry => entry.path)).size === installedEntries.length,
    'INSTALLED_MANIFEST_INVALID', 'Duplicate installed-manifest paths');
  evidence.seed_installed_manifest = {sha256: fileHash(installedPath), root: installedManifest.root,
    entries: installedEntries.length, summary: installedManifest.summary || null};
  requireCondition(!fs.existsSync(PROJECT), 'REPETITION_NOT_FRESH', 'Project already exists');
  fs.cpSync(path.join(ROOT, 'seed'), PROJECT, {recursive: true, verbatimSymlinks: true});
  requireCondition(fs.statSync(path.join(PROJECT, '.git')).isDirectory(),
    'GIT_SEED_INVALID', 'Seed must carry its own complete Git directory');
  const index = git(['ls-files', '--stage', '-z']).split('\0').filter(Boolean).map(record => {
    const [left, filename] = record.split('\t');
    const [mode, git_blob, stage] = left.split(' ');
    return {path: filename, mode, git_blob, stage};
  });
  requireCondition(index.length === baselineRows.length &&
    index.every(row => row.stage === '0' && baseMap.has(row.path) &&
      row.git_blob === baseMap.get(row.path).git_blob && row.mode === baseMap.get(row.path).mode),
  'GIT_INDEX_MISMATCH', 'Seed index is not the immutable original baseline');
  const readPackage = relative => loadJson(path.join(PROJECT, relative)).version;
  const npmPackage = path.resolve(path.dirname(process.execPath), '../lib/node_modules/npm/package.json');
  evidence.versions = {
    node: process.versions.node, npm: loadJson(npmPackage).version,
    jest: readPackage('node_modules/jest/package.json'),
    ts_jest: readPackage('node_modules/ts-jest/package.json'),
    typescript: readPackage('node_modules/typescript/package.json'),
    shared: readPackage('node_modules/@wxyc/shared/package.json'),
  };
  for (const name of ['node', 'npm', 'jest', 'ts_jest', 'typescript']) {
    requireCondition(evidence.versions[name] === protocol.runtime[name],
      'RUNTIME_VERSION_MISMATCH', name + ': installed version differs from frozen protocol');
  }
  const guardSource = fs.readFileSync(path.join(PROJECT, GUARD_FILE), 'utf8').split('\n');
  const guardLines = guardSource.flatMap((line, i) =>
    line.trim() === 'expect(source).not.toMatch(hardcodedNone);' ? [i + 1] : []);
  requireCondition(guardLines.length === 1, 'GUARD_EXPECTATION_IDENTITY_FAILURE', 'Original expectation line not unique');
  evidence.guard = {file: GUARD_FILE, full_name: GUARD, blob: GUARD_BLOB, expectation_line: guardLines[0]};
  checkState('before_baseline', baselineRows, false);
  evidence.status = 'BASELINE_RUNNING';
  const baseline = await runArm('baseline', false, guardLines[0]);
  checkState('after_baseline', baselineRows, false);
  verifyCompleteScope(baseline);
  requireCondition(baseline.summary?.infrastructure_eligible && baseline.summary.success === true && baseline.process.exit_code === 0 &&
    baseline.summary.counts.failed === 0 && baseline.summary.counts.passed > 0 &&
    baseline.summary.designated_guard_results.length === 1 &&
    baseline.summary.designated_guard_results[0].status === 'passed',
  'BASELINE_INELIGIBLE', 'Full original baseline or designated guard did not pass without infrastructure errors');
  const candidateFile = path.join(ROOT, 'candidate-auth.definition.ts');
  const candidateBytes = fs.readFileSync(candidateFile);
  requireCondition(sha(candidateBytes) === candidateRows.find(row => row.path === CHANGED).sha256,
    'FROZEN_CANDIDATE_BYTES_MISMATCH', 'Prepared candidate bytes differ from fixed manifest');
  // Apply only the already frozen bytes. There is no mutation/collision search.
  fs.writeFileSync(path.join(PROJECT, CHANGED), candidateBytes);
  checkState('before_selective', candidateRows, true);
  evidence.status = 'SELECTIVE_RUNNING';
  const selective = await runArm('selective', true, guardLines[0]);
  checkState('after_selective', candidateRows, true);
  checkState('before_independent', candidateRows, true);
  evidence.status = 'INDEPENDENT_RUNNING';
  const full = await runArm('independent_full', false, guardLines[0]);
  checkState('after_independent', candidateRows, true);
  verifyCompleteScope(full, baseline.summary);
  const baselineUniverse = multiset(baseline.summary.assertions.map(assertionIdentity));
  const selectiveOriginal = (selective.summary?.assertions || []).every(item => baselineUniverse[assertionIdentity(item)] > 0);
  const targetSelected = (selective.summary?.assertions || []).some(item =>
    item.file === GUARD_FILE && item.full_name === GUARD && ['passed', 'failed'].includes(item.status));
  evidence.conditions = {
    baseline_original_unit_oracle_passes: true,
    unchanged_original_tests_configuration_lock: true,
    identical_candidate_bytes_across_selective_and_independent: true,
    installed_dependencies_unchanged: true,
    native_selection_infrastructure_eligible: !!selective.summary?.infrastructure_eligible,
    independent_infrastructure_eligible: !!full.summary?.infrastructure_eligible,
    nonempty_native_original_passing_calls: selectiveOriginal &&
      selective.process.exit_code === 0 && !!selective.summary?.infrastructure_eligible &&
      selective.summary.success === true &&
      selective.summary.counts.passed > 0 && selective.summary.counts.failed === 0,
    original_security_guard_omitted_from_native_actual_calls: !!selective.summary?.infrastructure_eligible && !targetSelected,
    independent_original_security_expectation_fails: full.process.exit_code === 1 &&
      !!full.summary?.infrastructure_eligible && !!full.summary?.designated_guard_assertion_failure,
    unchanged_complete_original_test_universe: true,
  };
  evidence.qualifying_joint_witness = Object.values(evidence.conditions).every(Boolean);
  evidence.status = !selective.summary?.infrastructure_eligible || !full.summary?.infrastructure_eligible
    ? 'INELIGIBLE_EXECUTION_ERROR'
    : evidence.qualifying_joint_witness ? 'QUALIFYING_ORIGINAL_SECURITY_SOURCE_GUARD_WITNESS' : 'COMPLETED_NO_QUALIFYING_WITNESS';
}
function exportEvidence() {
  evidence.finished_at = new Date().toISOString();
  evidence.evidence_limits = {stdout_per_arm_bytes: MAX_LOG_BYTES, stderr_per_arm_bytes: MAX_LOG_BYTES,
    jest_report_bytes: MAX_REPORT_BYTES, exceeding_any_limit_is_ineligible: true};
  try { evidence.external_artifact_inventory = artifactInventory(OUT); }
  catch (error) {
    evidence.external_artifact_inventory_error = String(error);
    evidence.qualifying_joint_witness = false;
    evidence.status = 'INELIGIBLE_EVIDENCE_INVENTORY_ERROR';
    process.exitCode = 2;
  }
  const payload = Buffer.from(JSON.stringify(evidence));
  const compressed = gzipSync(payload);
  const record = {schema_version: 1, encoding: 'gzip+base64', uncompressed_bytes: payload.length,
    uncompressed_sha256: sha(payload), gzip_bytes: compressed.length,
    gzip_sha256: sha(compressed), payload_base64: compressed.toString('base64')};
  process.stdout.write('SP2027_EVIDENCE:' + JSON.stringify(record) + '\n');
}
try {
  await main();
} catch (error) {
  evidence.status = 'INELIGIBLE_' + (error.code || 'INFRASTRUCTURE_EXCEPTION');
  evidence.fatal_error = {code: error.code || null, message: error.message, stack: error.stack};
  process.exitCode = 2;
} finally {
  exportEvidence();
}

