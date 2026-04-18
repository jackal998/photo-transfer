# Photo Manager — Full System Vision

This document captures the end-to-end plan across all projects. Individual repos implement specific phases:

- **`photo-transfer`** → Phases 1–2 (dedup scan + migration)
- **`photo-manager`** *(separate repo)* → Phases 3–4 (sharing workflow, reference DB)
- *(unnamed)* → Phases 5–6 (AI indexing, search UI)

---

## 1. Survey Findings

### J:\圖片 — Personal NAS (unorganized)

Event-based folders using `YYYYMMDD_event_name` convention, mixing Chinese and English names. Covers 2006–2024 with good coverage of personal events (travel, outings, occasions). Also contains miscellaneous top-level folders (ASUS, BlueStacks, Camera Roll, Feedback, Ginny, etc.) that are not event-organized. This is the richest personal archive.

### D:\Downloads\Takeout\Google 相簿 — Google Takeout (local)

Mix of named albums and year-based folders (`Photos from 2011` through `Photos from 2025`). JSON sidecar metadata (timestamp, GPS, description) has already been embedded into media files via `galbum`. Ready for deduplication and migration.

### \\LinXiaoYun\photo — Shared Family NAS (partially organized)

Event folders use `YYYY MMDD event_name` format with Chinese descriptions. Goes back to 2003 through at least 2017+. Shared family archive populated deliberately with curated content. Deferred to Phase 3.

### \\LinXiaoYun\home\Photos\MobileBackup\iPhone — iPhone Sync (NAS)

Year-based: 2017, 2020–2026. Gap 2018–2019 accepted. Active auto-upload destination — Synology Photos Mobile writes here and this path must not change.

---

## 2. Single Source of Truth

All personal media lives under `\\LinXiaoYun\home\Photos\` (the user's Synology personal space, `/volume2/homes/J/Photos/`). iPhone auto-upload lands here without any manual intervention.

```
\\LinXiaoYun\home\Photos\
├── MobileBackup\
│   └── iPhone\
│       └── YYYY\          ← auto-upload, managed by Synology Photos (untouched)
├── YYYY\
│   └── YYYYMMDD_slug\     ← migrated from Takeout + J:\圖片
├── undated\               ← no EXIF date; flagged for manual review
└── _archive\
    └── legacy_unsorted\   ← unorganized top-level folders from J:\圖片
```

### Naming convention

`YYYYMMDD_slug` — CJK characters allowed (`20240601_大阪`), underscores, no spaces. Date from EXIF `DateTimeOriginal` only; no `mtime` fallback.

### Source → Destination mapping

| Source | Action | Destination |
|--------|--------|-------------|
| `MobileBackup\iPhone\YYYY\` | Keep in place | Unchanged |
| `D:\Downloads\Takeout\Google 相簿` | Dedup, migrate | `home\Photos\YYYY\YYYYMMDD_slug\` |
| `J:\圖片` — `YYYYMMDD_*` folders | Dedup, preserve name, migrate | `home\Photos\YYYY\YYYYMMDD_slug\` |
| `J:\圖片` — unorganized folders | Move as-is | `home\Photos\_archive\legacy_unsorted\` |
| `\\LinXiaoYun\photo` (family NAS) | Deferred to Phase 3 | — |

### Source priority (dedup)

iPhone backup > Google Takeout > J:\圖片

### Live Photos

Same-stem HEIC+MOV pairs are **atomic** — always migrate, dedup, and land together.

---

## 3. Shared Photos — References, Not Duplicates *(Phase 3)*

A photo shot by EJ that is "shared to family" should not be physically copied. The solution:

**Hardlinks** — same inode, both paths point to identical bytes. Transparent to all SMB clients (Windows Explorer, Synology Photos). Deleting the family path removes only that reference; the personal original is unaffected. Only work within the same volume (volume2) — confirmed viable.

**Reference DB** — SQLite audit log tracking `(personal_path, family_path, shared_by, shared_at)`. Used by the CLI to know which family paths exist and to power `unshare`.

### Workflow

```
photo-manager share <file> --to family
  └── Windows CLI → SSH → jackal998@LinXiaoYun
        └── ln /volume2/homes/J/Photos/2024/20240601_大阪/IMG_4234.jpg \
               /volume2/homes/J/Photos/family/2024/20240601_大阪/IMG_4234.jpg
        └── INSERT INTO shares (personal_path, family_path, ...)
```

```
photo-manager unshare <file>
  └── SSH → rm <family_path>
  └── DELETE FROM shares WHERE personal_path = ...
```

```
photo-manager reconcile
  └── scan DB, remove records for hardlinks that no longer exist
      (handles files deleted via File Station outside the CLI)
```

### Family folder structure

```
\\LinXiaoYun\home\Photos\family\
└── YYYY\
    └── YYYYMMDD_slug\      ← hardlinked files; transparent to all clients
```

---

## 4. Deduplication Strategy *(Phase 1 — photo-transfer)*

**Step 1 — Hash.** SHA-256 (exact) + pHash (near-duplicate) across all 3 active sources.

**Step 2 — Manifest (non-destructive).** Produce `migration_manifest.sqlite` with actions `MOVE | SKIP | REVIEW_DUPLICATE | UNDATED`. Nothing is deleted in this step.

**Step 3 — Human review.** pHash near-matches (burst shots, bracketed exposures) get `REVIEW_DUPLICATE` — never auto-deleted.

**Step 4 — Execute.** Phase 2 runs the manifest. Sources deleted only after new structure is verified.

```sql
CREATE TABLE migration_manifest (
  id           INTEGER PRIMARY KEY,
  source_path  TEXT NOT NULL,
  dest_path    TEXT,
  action       TEXT NOT NULL,
  source_hash  TEXT,
  phash        TEXT,
  duplicate_of TEXT,
  reason       TEXT,
  executed     INTEGER DEFAULT 0
);
```

---

## 5. Vector DB + AI Search Layer *(Phase 5)*

### Architecture

```
Windows Machine (CPU/GPU — NAS has no GPU)
  ├── AI indexer (Python)
  │     ├── reads from /volume2/homes/J/Photos/ via SMB
  │     ├── CLIP clip-vit-large-patch14 → 768-dim embeddings (photos)
  │     ├── frame sampler → average embeddings (videos, 1fps, cap 50 frames)
  │     ├── BLIP/LLaVA captions
  │     ├── InsightFace face detection + clustering
  │     ├── geopy + Nominatim GPS → place name
  │     └── upserts to Qdrant REST API on NAS
  └── Search UI / CLI
        └── queries Qdrant REST API

NAS (DS920+, DSM 7.2.2)
  └── Docker: Qdrant (memory_limit: 512m)
```

### Scope

Photos and videos: JPEG, HEIC, PNG, MOV, MP4.

- **HEIC**: `pillow-heif` required on Windows
- **RAW** (ARW, CR3, DNG): `rawpy` preview conversion before CLIP
- **Videos**: 1 frame per 10 seconds, capped at 50 frames; average frame embeddings

### Metadata per vector

```json
{
  "file_path": "\\\\LinXiaoYun\\home\\Photos\\2024\\20240601_大阪\\IMG_4234.jpg",
  "owner": "EJ",
  "date": "2024-06-01",
  "place_name": "Osaka, Japan",
  "gps": [34.6937, 135.5023],
  "caption": "Two people smiling at a street food stall at night",
  "faces": ["EJ", "曉灣"],
  "tags": ["travel", "food", "night"],
  "media_type": "photo"
}
```

### Query flow

User query → CLIP text encoder → nearest-neighbor search in Qdrant (filtered by date/owner/place) → top-K file paths → thumbnails.

---

## 6. Search Interface *(Phase 6)*

Simple web UI or CLI: natural language query → vector search → results with thumbnails. Optionally integrate with Synology Photos via API.

---

## NAS Reference

| Item | Value |
|------|-------|
| Device | Synology DS920+ (Intel Celeron J4125, no GPU) |
| DSM | 7.2.2 (2024-11-15) |
| Docker | 20.10.23 |
| RAM available | ~1.8 GB |
| Photos path (Linux) | `/volume2/homes/J/Photos/` |
| Photos path (SMB) | `\\LinXiaoYun\home\Photos\` |
| SSH user | `jackal998` (admin) — use full path, never `~/` |
| volume2 free | 1.8 TB |
