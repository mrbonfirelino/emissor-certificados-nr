# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('templates', 'templates')],
    hiddenimports=['customtkinter', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'tensorflow', 'keras', 'transformers', 'datasets', 'tokenizers', 'huggingface_hub', 'accelerate', 'sklearn', 'scipy', 'numpy', 'pandas', 'pyarrow', 'cv2', 'av', 'soundfile', 'onnxruntime', 'matplotlib', 'nltk', 'sqlalchemy', 'pymysql', 'psycopg2', 'boto3', 'botocore', 'grpc', 'dns', 'pymongo', 'pytest', 'IPython', 'jupyter', 'PyQt5', 'PySide6', 'wx', 'cryptography', 'bcrypt', 'paramiko', 'selenium', 'tornado', 'twisted', 'psutil', 'win32com', 'pythoncom', 'pywintypes', 'rapidfuzz', 'lxml', 'orjson', 'rich', 'pygments', 'emoji', 'fsspec'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='NormaTech',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\logo.ico'],
)
