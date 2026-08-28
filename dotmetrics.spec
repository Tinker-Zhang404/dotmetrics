from PyInstaller.utils.hooks import collect_all


ultralytics_data, ultralytics_binaries, ultralytics_hiddenimports = collect_all("ultralytics")

a = Analysis(
    ["dotmetrics.py"],
    pathex=["src"],
    binaries=ultralytics_binaries,
    datas=ultralytics_data + [("models/yolov8n-DotMetrics.pt", "models")],
    hiddenimports=ultralytics_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

contaminated_binaries = [
    entry for entry in a.binaries if "codex-runtimes" in str(entry[1]).lower()
]
if contaminated_binaries:
    sources = "\n".join(str(entry[1]) for entry in contaminated_binaries)
    raise RuntimeError(f"Refusing to package external Codex runtime DLLs:\n{sources}")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DotMetrics",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DotMetrics",
)
