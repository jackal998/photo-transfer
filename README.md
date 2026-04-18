# photo-transfer

One-time migration of personal photos from three sources into a single, organised structure on a Synology NAS.

**Scope:** deduplication scan + file migration only.  
AI search, family sharing, and ongoing management are handled by separate projects (see [`docs/vision.md`](docs/vision.md)).

---

## How it works

```
photo-manager/scan.py          →  migration_manifest.sqlite   (non-destructive scan)
photo-manager/review.py        →  triage REVIEW_DUPLICATE rows
photo-transfer/migrate.py      →  copy MOVE files to NAS
```

The scan and review steps run from **[jackal998/photo-manager](https://github.com/jackal998/photo-manager)**.  
The migration step runs from this repo.

---

## Sources

| Label | Location | Treatment |
|-------|----------|-----------|
| `iphone` | `\\LinXiaoYun\home\Photos\MobileBackup\iPhone\` | Kept in place — dedup reference only |
| `takeout` | `D:\Downloads\Takeout\Google 相簿` | galbum metadata already embedded |
| `jdrive` | `J:\圖片` | Needs reorganisation |

---

## Destination

All migrated content lands under the user's Synology personal space:

```
\\LinXiaoYun\home\Photos\          →  /volume2/homes/J/Photos/
├── MobileBackup\iPhone\YYYY\      ← auto-upload, untouched
├── YYYY\YYYYMMDD_slug\            ← migrated from Takeout + J:\圖片
├── undated\                       ← no EXIF; manual review
```

Date source: **EXIF `DateTimeOriginal` only** — no `mtime` fallback.

---

## Usage

### Step 1 — Scan (run from photo-manager)

```powershell
cd path\to\photo-manager

python scan.py `
  --source iphone="\\LinXiaoYun\home\Photos\MobileBackup\iPhone" `
  --source takeout="D:\Downloads\Takeout\Google 相簿" `
  --source jdrive="J:\圖片" `
  --output migration_manifest.sqlite

# Dry run first (no file written):
python scan.py ... --dry-run
```

### Step 2 — Review near-duplicates (run from photo-manager)

```powershell
python review.py --manifest migration_manifest.sqlite
```

### Step 3 — Migrate (run from this repo)

```powershell
cd path\to\photo-transfer

# Preview only:
python migrate.py `
  --manifest path\to\migration_manifest.sqlite `
  --dest-root "\\LinXiaoYun\home\Photos" `
  --dry-run

# Trial batch:
python migrate.py ... --limit 50

# Full run:
python migrate.py `
  --manifest path\to\migration_manifest.sqlite `
  --dest-root "\\LinXiaoYun\home\Photos"
```

---

## Project structure

```
photo-transfer/
├── migrate.py          # CLI: execute MOVE actions from manifest
├── transfer/
│   ├── db.py           # Manifest read + execution status tracking
│   └── executor.py     # File copy + collision resolution
├── tests/
│   ├── test_db.py
│   └── test_executor.py
└── docs/
    ├── system-plan.md  # Scoped migration plan
    ├── deep-verify.md  # Architecture decisions & edge cases resolved
    └── vision.md       # Full 6-phase vision (AI search, family sharing, …)
```

---

## NAS reference

| Item | Value |
|------|-------|
| Device | Synology DS920+ / DSM 7.2.2 |
| Photos path (SMB) | `\\LinXiaoYun\home\Photos\` |
| Photos path (SSH) | `/volume2/homes/J/Photos/` |
| SSH user | `jackal998` (admin) |
| Free space | 1.8 TB |

---

## Progress

See [PROGRESS.md](PROGRESS.md) for phase-by-phase status.
