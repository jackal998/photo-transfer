# photo-transfer — Progress

## Phase 0 — Planning ✓

- [x] Survey all 4 media sources
- [x] Define single source of truth (`\\LinXiaoYun\home\Photos\`)
- [x] Confirm NAS specs (DS920+, DSM 7.2.2, `/volume2/homes/J/Photos/`, 1.8 TB free)
- [x] Resolve architecture decisions (see [`docs/deep-verify.md`](docs/deep-verify.md))
- [x] Scope `photo-transfer` to migration only; AI search + family sharing → separate projects

Docs: [`docs/system-plan.md`](docs/system-plan.md) · [`docs/vision.md`](docs/vision.md)

---

## Phase 1 — Deduplication Scan 🔄 in progress

### 1a — Implementation ✓ (merged)

Scanner lives in **[jackal998/photo-manager](https://github.com/jackal998/photo-manager)**.

| Tool | Purpose |
|------|---------|
| `scan.py` | Walk sources → SHA-256 + pHash → `migration_manifest.sqlite` |
| `review.py` | Interactive terminal triage of `REVIEW_DUPLICATE` rows |

Features delivered:
- SHA-256 exact duplicate detection across all 3 sources
- pHash cross-format dedup (JPG vs HEIC vs RAW vs PNG)
- pHash hamming distance similarity check (burst shots, near-dupes → `REVIEW_DUPLICATE`)
- Live Photo atomic pairs (HEIC + MOV same stem move together)
- RAW + JPG kept together (complementary, not duplicates)
- Magic-byte type verification (catches JPEG files saved as `.HEIC`)
- Google Takeout duplicate numbering handled (`IMG_9556(1).HEIC`)
- Edited variants excluded from pairing (`-已編輯`, `-edited`, …)
- EXIF date via exiftool batch (all formats including RAW, MOV)
- No-EXIF files → `undated/` holding folder

### 1b — Execution ⏳ pending

**Sources to scan:**
| Label | Path |
|-------|------|
| `iphone` | `\\LinXiaoYun\home\Photos\MobileBackup\iPhone\` (dedup ref, kept in place) |
| `takeout` | `D:\Downloads\Takeout\Google 相簿` (galbum already run) |
| `jdrive` | `J:\圖片` |

**Checklist — Phase 1 is complete when:**
- [ ] `scan.py --dry-run` runs without errors against all 3 sources
- [ ] Full scan produces `migration_manifest.sqlite`
- [ ] Summary counts look plausible (no obvious miscount)
- [ ] `REVIEW_DUPLICATE` rows triaged via `review.py`
- [ ] `UNDATED` rows spot-checked; any recoverable dates fixed
- [ ] Manifest approved for Phase 2

---

## Phase 2 — Migration Execution ⏳ pending

### 2a — Implementation ✓ (merged)

| Tool | Purpose |
|------|---------|
| `migrate.py` | Read manifest → copy MOVE files to NAS dest root, resumable |

### 2b — Execution ⏳ pending (requires Phase 1 complete)

- [ ] `migrate.py --dry-run` confirms paths and counts
- [ ] `migrate.py --limit 50` trial run; verify files land correctly on NAS
- [ ] Full migration run
- [ ] Verify file count on NAS matches expected MOVE count
- [ ] No source files deleted until verification passes

---

## Full Vision

The bigger picture (AI search, vector DB, family sharing) lives in [`docs/vision.md`](docs/vision.md).
