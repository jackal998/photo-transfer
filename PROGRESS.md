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

Implemented in **[jackal998/photo-manager](https://github.com/jackal998/photo-manager)** (`feat/dedup-scanner` branch).

Produces `migration_manifest.sqlite` — consumed by Phase 2.

**Scanner features:**
- SHA-256 exact duplicate detection across all 3 sources
- pHash cross-format dedup (JPG vs HEIC vs RAW vs PNG)
- pHash hamming distance similarity check (burst shots, near-dupes → `REVIEW_DUPLICATE`)
- Live Photo atomic pairs (HEIC + MOV same stem move together)
- RAW + JPG kept together (not treated as duplicates)
- Magic-byte type verification (catches JPEG files saved as `.HEIC`)
- Google Takeout duplicate numbering handled (`IMG_9556(1).HEIC`)
- Edited variants excluded from pairing (`-已編輯`, `-edited`, …)
- EXIF date via exiftool batch (all formats including RAW, MOV)
- No-EXIF files → `undated/` holding folder

**Sources scanned:**
| Label | Path |
|-------|------|
| `iphone` | `\\LinXiaoYun\home\Photos\MobileBackup\iPhone\` (dedup ref, kept in place) |
| `takeout` | `D:\Downloads\Takeout\Google 相簿` (galbum already run) |
| `jdrive` | `J:\圖片` |

---

## Phase 2 — Migration Execution ⏳ pending

Executes `migration_manifest.sqlite`: copies files to `/volume2/homes/J/Photos/YYYY/YYYYMMDD_slug/`.

Prerequisites:
- [ ] Phase 1 manifest reviewed and approved
- [ ] `REVIEW_DUPLICATE` rows triaged manually

---

## Full Vision

The bigger picture (AI search, vector DB, family sharing) lives in [`docs/vision.md`](docs/vision.md).
