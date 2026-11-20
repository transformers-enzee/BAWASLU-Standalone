/** Version-contract helpers shared by legacy feature tests.
 *
 * The UI now receives the deployed version from /api/health. Tests must
 * verify that wiring rather than parse a frozen JSX string.
 * These assertions use source only: no network, DB, or model calls.
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const backend=()=>readFileSync(new URL('../../backend/app/main.py',import.meta.url),'utf8');
const VERSION=/'build_version':os\.getenv\('BAWASLU_BUILD_VERSION','([0-9]+\.[0-9]+)'\)/;

export function readBackendVersion(source){
 const match=String(source||'').match(VERSION);
 assert.ok(match,'Backend health must use the image-supplied build version');
 return match[1];
}

function runtimeWiring(shell){
 const source=String(shell||'');
 return source.includes("fetch('/api/health'") &&
  source.includes("cache:'no-store'") &&
  source.includes("data-build-version={buildInfo.build_version||'unavailable'}") &&
  source.includes("<AccessNavigation access={access} user={user} build={buildInfo}/>") &&
  source.includes("buildInfo.build_version?'v'+buildInfo.build_version");
}

export function readShellVersion(shell){
 assert.ok(runtimeWiring(shell),'Frontend must render the backend health version in all build labels');
 return readBackendVersion(backend());
}

export function hasDynamicBuildVersion(shell,version){
 return runtimeWiring(shell) && readBackendVersion(backend())===String(version||'');
}
