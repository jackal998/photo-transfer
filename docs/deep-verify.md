# Deep Verify — Photo Manager Plan

## Context

Verification of the system plan before implementation begins. No code exists yet. This document surfaces contradictions, resolves decisions, and flags what remains open.

---

## Resolved Decisions

| Decision | Resolution |
|----------|------------|
| Date fallback chain | **EXIF DateTimeOriginal → flag for manual review**. No `mtime` fallback. Files without EXIF go to `undated\` holding folder. |
| Live Photos | **Atomic pairs**: same-stem HEIC+MOV always migrate and dedup as a unit. |
| Folder slugs | **CJK characters allowed as-is** (`20240601_大阪`). Works on Synology (Linux UTF-8) and Windows NTFS. |
| Other owners | EJ only for this transfer phase. |
| 2018–2019 iPhone gap | Accepted — will surface in `undated\` or `_archive\` during dedup scan. |
| Dedup approach | Manifest-only (non-destructive Phase 1); execution in Phase 2 after review. |
| Family folder / hardlinks | **Out of scope** for `photo-transfer` — handled by a separate project. |
| AI search / vector DB | **Out of scope** for `photo-transfer` — handled by a separate project. |

---

## Target Structure (photo-transfer scope)

```
/volume2/homes/J/Photos/           (\\LinXiaoYun\home\Photos\)
├── MobileBackup\iPhone\YYYY\      ← auto-upload, untouched
├── YYYY\YYYYMMDD_slug\            ← migrated from Takeout + J:\圖片
├── undated\                       ← no EXIF date
└── _archive\legacy_unsorted\      ← unorganized J:\圖片 folders
```

---

## Remaining Open Items

### O1. NAS hardware + DSM version *(HIGH)*
Docker Compose support, inotify availability, and hardlink behavior across volumes all depend on DSM version. Qdrant RAM requirements (~2–4 GB for 50k vectors) must fit NAS free RAM.
**Needed before:** Phase 5.

### O2. Who owns files besides EJ? *(MEDIUM)*
Survey mentions "Ginny" folder on J:\圖片. If there are other personal owners, the `personal\` tree needs additional subdirectories.
**Needed before:** Phase 3 (directory structure creation).

### O3. iPhone 2018–2019 gap *(MEDIUM)*
Two years of iPhone photos are missing. Before migration, decide: search for those years (old device, iCloud, Google Photos export) or accept the gap.
**Needed before:** Phase 2.

### O4. `galbum` interface contract *(HIGH)*
Plan says galbum is "already built and tested" but its inputs, outputs, failure modes, and supported formats are undocumented.
**Needed before:** Phase 1.

### O5. Storage budget confirmation *(MEDIUM)*
Rough estimate: 200–450 GB total before dedup. Confirm NAS free space before starting migration.

---

## Edge Cases to Address During Implementation

### E1. pHash false positives need human review
pHash flags burst shots, bracketed exposures, and near-duplicate compositions. The migration manifest must include a `REVIEW_DUPLICATE` status for pHash matches with similarity above threshold but below certainty. These are never auto-deleted.

### E2. HEIC / RAW / video pipeline gaps
- **HEIC**: needs `pillow-heif` or `libheif` on Windows for CLIP
- **RAW** (ARW, CR3, DNG): needs `rawpy` to convert to preview JPEG before CLIP
- **Videos**: 1 frame per 10 seconds, capped at 50 frames per video

### E3. Hardlink + DB drift (Phase 4)
If a family hardlink is deleted via File Station outside the CLI, the DB record becomes stale. The management script needs a periodic `reconcile` command.

### E4. Deduplication must be manifest-only (non-destructive)
Phase 2 produces a manifest only. Source files are not deleted until Phase 3 is fully verified.

### E5. Filename collisions in destination
Two files from different sources may produce the same `YYYYMMDD_event/filename`. Migration script must detect and resolve collisions (append `_2`, `_3`, or prompt).

---

## Pre-Coding Checklist

| Priority | Item | Owner |
|----------|------|-------|
| HIGH | Confirm NAS model + DSM version + free RAM | User |
| HIGH | Document `galbum` interface (input/output/failures) | User |
| MEDIUM | Decide: other owners besides EJ? | User |
| MEDIUM | Decide: search for 2018–2019 iPhone backup? | User |
| MEDIUM | Confirm NAS free space (200–450 GB needed) | User |
| CODE | pHash manual-review step in Phase 2 | system-plan.md ✓ |
| CODE | HEIC/RAW/video pipeline details in Phase 5 | system-plan.md ✓ |
| CODE | Hardlink reconcile command in Phase 4 | system-plan.md ✓ |
| CODE | Migration manifest schema defined | system-plan.md ✓ |
