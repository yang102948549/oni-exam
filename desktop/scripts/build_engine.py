"""Bundle the existing Python engine and only its required resources."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
STAGE = Path(tempfile.gettempdir()) / 'oni-exam-build' / 'engine-data'
WORK = Path(tempfile.gettempdir()) / 'oni-exam-build' / 'pyinstaller'
SPEC = Path(tempfile.gettempdir()) / 'oni-exam-build'
for name in ['extract_items4.py', 'build_hwpx_doc4.py', 'mathpage.py', 'mathparse.py']:
    dst = STAGE / 'scripts' / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'scripts' / name, dst)
for name in ['seed_package.hwpx', 'oni_icon.png']:
    dst = STAGE / 'work' / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'work' / name, dst)
for font_file in (APP / 'fonts').glob('*'):
    if font_file.is_file():
        dst = STAGE / 'fonts' / font_file.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(font_file, dst)
host = subprocess.check_output(['rustc', '-vV'], text=True).split('host: ')[1].splitlines()[0]
cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--console',
       '--name', 'oni-engine-' + host, '--distpath', str(APP / 'src-tauri' / 'binaries'),
       '--workpath', str(WORK), '--specpath', str(SPEC),
       '--paths', str(ROOT / 'scripts'), '--hidden-import', 'mathpage', '--hidden-import', 'mathparse',
       '--add-data', str(STAGE / 'scripts') + os.pathsep + 'scripts',
       '--add-data', str(STAGE / 'work') + os.pathsep + 'work',
       '--add-data', str(STAGE / 'fonts') + os.pathsep + 'fonts', str(APP / 'engine' / 'worker.py')]
for module in ['numpy', 'pandas', 'matplotlib', 'scipy', 'cv2', 'tkinter', 'IPython', 'torch']:
    cmd += ['--exclude-module', module]
subprocess.run(cmd, check=True)
