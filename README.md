# PatchSmith

Windows-first desktop app (Python + PySide6) to **create** and **apply** game-style folder patches: compare two game trees, emit a JSON manifest (SHA256 + xdelta or full-file copies), optionally archive with **7-Zip** (`7za`), and apply with pre/post hash checks and optional backup.

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

### Bundled tools (Windows / Linux, repo `bin/`)

| File | Purpose |
|------|---------|
| `xdelta-3.1.0-x86_64.exe` | xdelta3 CLI on Windows |
| `xdelta3-linux` | xdelta3 CLI on Linux (optional) |
| `7za.exe` | 7-Zip standalone CLI on Windows |

PatchSmith resolves tools in this order: `PATCHSMITH_XDELTA3` / `PATCHSMITH_7ZA` → repo `bin/` (or PyInstaller bundle) → patch folder `tools/` → `PATH`.

### macOS

There is **no** xdelta3 binary in `bin/` for macOS yet. Install:

- **xdelta3:** `brew install xdelta` — see [Homebrew `xdelta` formula](https://formulae.brew.sh/formula/xdelta).
- **7za:** e.g. `brew install p7zip` (provides `7za`; confirm with `brew info p7zip`).

Override paths anytime with `PATCHSMITH_XDELTA3` and `PATCHSMITH_7ZA`.

## Run

From the repository root:

```bash
python -m patcher.app
python -m patcher.apply_portable   # dev: set PATCHSMITH_PATCH_ROOT to a patch folder first
```

## Patch layout

```
YourPatch/
  patch_manifest.json
  ApplyPatch.exe      # optional: portable apply tool (see below)
  patch_files/
    changed/          # .xdelta or full-file replacements
    new/              # new files
  deleted_files.txt   # optional human-readable list
  tools/              # optional portable xdelta3 / 7za
```

## Portable `ApplyPatch.exe` (Windows end users)

You can ship a **small frozen apply-only program** next to `patch_manifest.json` so players do not need the full PatchSmith app.

1. **Build** the one-file executable (from repo root, after `pip install -r requirements-dev.txt`):

   ```bash
   pyinstaller --noconfirm packaging/apply_patch.spec
   ```

   Output: `dist/ApplyPatch.exe` (embeds PySide6, Python runtime, and copies of `bin/xdelta-3.1.0-x86_64.exe` and `bin/7za.exe` from your repo).

2. **Publish for patch authors:** copy `dist/ApplyPatch.exe` to **`bin/ApplyPatch.exe`** in this repository (or keep it elsewhere and copy when packaging). In **Create Patch**, enable **“Include portable apply tool (ApplyPatch.exe) for end users”** so the file is copied into the patch folder **before** any archive step.

3. **End user layout:** keep `ApplyPatch.exe` in the **same folder** as `patch_manifest.json`. Double-click it, choose the game folder, click **Apply patch**.

4. **Developer testing** of the UI without freezing:

   ```bash
   set PATCHSMITH_PATCH_ROOT=C:\path\to\existing\patch\folder
   python -m patcher.apply_portable
   ```

One-file builds extract to a temp folder on each launch (short delay). For faster cold start, switch the spec to onedir (`COLLECT`) at the cost of many files beside the manifest.

## Licenses (third-party binaries)

- **xdelta:** This project may ship binaries built from the GPL lineage or the Apache-licensed fork. Read [xdelta-gpl `release3_1` README](https://github.com/jmacd/xdelta-gpl/blob/release3_1/README.md) and [jmacd/xdelta](http://github.com/jmacd/xdelta) and document which lineage your shipped `xdelta3` matches.
- **7-Zip / `7za`:** See the official [7-Zip](https://www.7-zip.org/) site for license terms before redistributing `7za.exe`.

## PyInstaller (optional)

- **Full app:** bundle `bin/xdelta-3.1.0-x86_64.exe` and `bin/7za.exe` as data files and point `PATCHSMITH_*` resolution at `_MEIPASS` or the folder next to the frozen executable (see `patcher.core.xdelta` / `archiver`).
- **Portable apply only:** use [`packaging/apply_patch.spec`](packaging/apply_patch.spec) (see **Portable `ApplyPatch.exe`** above).

## Manifest (sketch)

Top-level fields include `manifest_version`, `patch_name`, `from_version`, `to_version`, `created_by`, `xdelta_threshold_mb`, optional `archive_format` (`7z` / `zip`), `archive_compression_level`, and `files[]` with `path`, `action` (`xdelta` | `copy` | `delete`), hashes, sizes, and `patch_path` where applicable.
