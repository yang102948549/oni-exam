"""Stage the locked Node runtime beside the Python sidecar for Tauri resources."""
from pathlib import Path
import shutil
import subprocess

app = Path(__file__).resolve().parents[1]
source = app / 'engine' / 'kordoc'
target = app / 'src-tauri' / 'kordoc-runtime'
node = shutil.which('node')
if not node or not (source / 'node_modules/kordoc/package.json').is_file():
    raise SystemExit('Install Node.js >=20 and run npm run parser:install first.')
major = int(subprocess.check_output([node, '--version'], text=True).lstrip('v').split('.')[0])
if major < 20:
    raise SystemExit('Node.js >=20 required')
# Validate the exact stage before replacing stale dependency versions.
if target.exists():
    assert target.resolve().parent == (app / 'src-tauri').resolve()
    shutil.rmtree(target)
target.mkdir(parents=True)
shutil.copy2(node, target / 'node.exe')
shutil.copy2(source / 'parse.mjs', target / 'parse.mjs')
shutil.copy2(source / 'package-lock.json', target / 'package-lock.json')
shutil.copytree(source / 'node_modules', target / 'node_modules')
print(f'Parser runtime staged: {target}')
