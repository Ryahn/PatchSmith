# PatchSmith

Windows-first desktop app (Python + PySide6) to **create** and **apply** game-style folder patches: compare two game trees, emit a JSON manifest (SHA256 + xdelta or full-file copies), optionally archive with **7-Zip** (`7za`), and apply with pre/post hash checks and optional backup.

## Version

The release string is defined once in [`patcher/version.py`](patcher/version.py) as `__version__` (also available as `patcher.__version__`). PyInstaller outputs **`PatchSmith-<version>.exe`** / **`ApplyPatch-<version>.exe`** on Windows and **`PatchSmith-<version>`** / **`ApplyPatch-<version>`** on Linux. **Create Patch → Include portable apply tool** copies the matching file from `bin/` next to `patch_manifest.json`.

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

### Bundled tools (Windows / Linux, repo `bin/`)

| File | Purpose |
|------|---------|
| `xdelta-3.1.0-x86_64.exe` | xdelta3 CLI on Windows |
| `xdelta3-linux` | xdelta3 CLI on Linux (optional) |
| `7za.exe` | 7-Zip standalone CLI on Windows |
| `7za-linux` | Optional: Linux `7za` binary placed in `bin/` for bundling / PyInstaller (e.g. copy from `p7zip-full`); not committed by default |

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
  ApplyPatch-<version>.exe   # Windows portable apply (name includes semver)
  ApplyPatch-<version>       # Linux portable apply
  patch_files/
    changed/          # .xdelta or full-file replacements
    new/              # new files
  deleted_files.txt   # optional human-readable list
  tools/              # optional portable xdelta3 / 7za
```

## Portable apply tool (Windows / Linux)

Ship a **small frozen apply-only program** next to `patch_manifest.json` so players do not need the full PatchSmith app.

### Windows

1. Build (repo root, after `pip install -r requirements-dev.txt`):

   ```bash
   pyinstaller --noconfirm packaging/apply_patch.spec
   ```

2. Copy **`dist/ApplyPatch-<version>.exe`** to **`bin/ApplyPatch-<version>.exe`** (same `<version>` as in `patcher/version.py`). In **Create Patch**, enable **Include portable apply tool** so it is copied next to the manifest (and into `.7z` / `.zip` if used).

### Linux

1. Provide **`bin/7za-linux`** (e.g. `cp "$(command -v 7za)" bin/7za-linux` after installing `p7zip-full`) next to the existing **`bin/xdelta3-linux`**.

2. Build:

   ```bash
   pyinstaller --noconfirm packaging/apply_patch_linux.spec
   ```

3. Copy **`dist/ApplyPatch-<version>`** to **`bin/ApplyPatch-<version>`** and mark executable (`chmod +x "bin/ApplyPatch-<version>"`). Enable **Include portable apply tool** in Create Patch to copy that file into the patch folder.

**Developer testing** without freezing:

```bash
# Windows CMD
set PATCHSMITH_PATCH_ROOT=C:\path\to\patch && python -m patcher.apply_portable

# Linux/macOS
export PATCHSMITH_PATCH_ROOT=/path/to/patch && python -m patcher.apply_portable
```

One-file builds extract to a temp folder on each launch (short delay). For faster cold start, switch the spec to onedir (`COLLECT`) at the cost of many files beside the manifest.

## GitHub Actions

Workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs **pytest** on **Windows** and **Ubuntu**, then builds:

| Artifact name | OS | PyInstaller output (under `dist/`) |
|---------------|-----|-------------------------------------|
| `ApplyPatch-<version>-Windows` | Windows | `ApplyPatch-<version>.exe` |
| `ApplyPatch-<version>-Linux` | Ubuntu | `ApplyPatch-<version>` (ELF) |
| `PatchSmith-<version>-Windows` | Windows | `PatchSmith-<version>.exe` |
| `PatchSmith-<version>-Linux` | Ubuntu | `PatchSmith-<version>` (ELF) |

`<version>` matches `patcher/version.py`. Download from the Actions run **Artifacts** list.

### GitHub Releases

Pushing a **semver tag** `v<version>` (for example `v0.1.0`) runs the same builds, then publishes a **[GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)** with the four binaries attached. The tag must match `__version__` in [`patcher/version.py`](patcher/version.py) (without the leading `v`), or the publish step fails.

## Licenses (third-party binaries)

- **xdelta:** This project may ship binaries built from the GPL lineage or the Apache-licensed fork. Read [xdelta-gpl `release3_1` README](https://github.com/jmacd/xdelta-gpl/blob/release3_1/README.md) and [jmacd/xdelta](http://github.com/jmacd/xdelta) and document which lineage your shipped `xdelta3` matches.
- **7-Zip / `7za`:** See the official [7-Zip](https://www.7-zip.org/) site for license terms before redistributing `7za.exe`.

## PyInstaller (optional)

- **Full app:** [`packaging/patchsmith_windows.spec`](packaging/patchsmith_windows.spec) / [`packaging/patchsmith_linux.spec`](packaging/patchsmith_linux.spec) bundle `bin/` tools into `_MEIPASS` (see `patcher.core.xdelta` / `archiver`).
- **Portable apply only:** Windows — [`packaging/apply_patch.spec`](packaging/apply_patch.spec); Linux — [`packaging/apply_patch_linux.spec`](packaging/apply_patch_linux.spec).

## Manifest (sketch)

Top-level fields include `manifest_version`, `patch_name`, `from_version`, `to_version`, `created_by`, `xdelta_threshold_mb`, optional `archive_format` (`7z` / `zip`), `archive_compression_level`, and `files[]` with `path`, `action` (`xdelta` | `copy` | `delete`), hashes, sizes, and `patch_path` where applicable.
