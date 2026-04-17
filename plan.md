# Photo Manager — System Plan

## 1. Survey Findings

### J:\圖片 — Personal NAS (unorganized)

Event-based folders using `YYYYMMDD_event_name` convention, mixing Chinese and English names. Covers 2006–2024 with good coverage of personal events (travel, outings, occasions). Also contains miscellaneous top-level folders (ASUS, BlueStacks, Camera Roll, Feedback, Ginny, etc.) that are not event-organized. The naming scheme is good where it exists but inconsistent elsewhere. This is the richest personal archive.

### D:\Downloads\Takeout\Google 相簿 — Google Takeout (local, unstructured)

Mix of named albums and year-based folders (`Photos from 2011` through `Photos from 2025`). Album names reveal personal tagging (E.J., E.J.+曉灣, 凱凱, 德國, 大阪42, etc.) and organizational intent. Contains trash and test artifacts (垃圾桶, 測試, 封存檔案). Still on local disk, not migrated to NAS. The JSON sidecar files from Takeout contain timestamp, GPS, and description metadata — these should be embedded into media files using `galbum` before migration.

### \\LinXiaoYun\photo — Shared Family NAS (partially organized)

The most consistently organized location. Event folders use `YYYY MMDD event_name` format with Chinese descriptions (family outings, holidays, birthdays, New Year gatherings). Goes back to 2003 and covers family events through at least 2017+. This is the shared family archive — populated deliberately with curated content.

### \\LinXiaoYun\home\Photos\MobileBackup\iPhone — iPhone Sync (NAS, organized)

Year-based organization: 2017, 2020–2026. Missing 2018–2019 (gap in backup). This is raw iPhone camera roll, organized by year but not by event. Likely the highest-volume, most recent content.

---

## 2. Proposed Single Source of Truth

All originals live under a single root on the NAS, organized by **owner → year → event**:

```

\\LinXiaoYun\media\
├── personal\
│   └── EJ\
│       ├── 2024\
│       │   ├── 20240601_大阪\
│       │   └── 20241225_christmas\
│       └── 2023\
├── family\               ← curated shared events (not duplicates — see Section 3)
│   └── 2024\
│       └── 20240101_newyear\
└── archive\              ← old unorganized material post-migration
    └── legacy_unsorted\

```

**Naming convention:** `YYYYMMDD_slug` where slug is lowercase ASCII or CJK, no spaces (use underscores). Date comes from EXIF `DateTimeOriginal` when available, file mtime as fallback.

**The `family\` folder does not store files.** It stores references only (see Section 3).

---

## 3. Shared Photos as References, Not Duplicates

The core problem: a photo shot by EJ that is "shared to family" should not be physically copied to the family folder. Doing so creates two files with no link, diverging metadata, and wasted storage.

### Options evaluated

**Symlinks** — Linux-native, work on Synology DSM natively via SSH or File Station. However, Windows SMB clients do not follow symlinks transparently by default (they see the link, not the file). This makes them unreliable for cross-platform access via Explorer or Photos apps on Windows/iOS.

**Hardlinks** — Same inode, both paths point to identical bytes. Work transparently on all clients. Limitation: only work within the same filesystem/volume. Since personal and family are on the same NAS, this is viable. Deleting one path does not remove the data until all links are gone. Cannot span volumes.

**Reference database (recommended)** — A SQLite database (or JSON manifest) stores records like `{shared_path, owner_path, added_by, added_at}`. The family view is a virtual directory: a script or web UI renders the family album by reading references and serving or streaming from the owner path. No physical copy. Metadata edits happen only on the owner file. Deletion from shared view removes only the reference row. This is the cleanest model and the foundation for the AI search layer (Section 5).

**Synology Shared Links / Photos App** — Synology Photos has a "shared album" concept that works this way natively but is locked to the Synology Photos UI. Fine as a viewing interface but not a data architecture.

### Recommendation

Use **hardlinks for migration** (safest, transparent to all clients, no infrastructure needed) combined with a **reference database for ongoing management**. During initial migration, hardlink personal originals into the family tree for already-shared content. Going forward, the reference DB tracks what is shared and the physical hardlinks are created/removed by the management script.

---

## 4. Deduplication Strategy

Before migrating, find and eliminate duplicates across all 4 locations.

**Step 1 — Hash all files.** Compute SHA-256 or perceptual hash (pHash) for every media file across all locations. SHA-256 catches exact byte-for-byte duplicates (same file, different path). pHash catches visually identical images that differ in metadata, compression, or minor edits.

**Step 2 — Build a duplicate map.** Group files by hash. For each duplicate group, keep the copy with the best metadata (EXIF timestamp, GPS, description) and/or the highest resolution. The iPhone backup and Google Takeout folders will have heavy overlap.

**Step 3 — Resolve by source priority.** Priority order: iPhone backup (original, full quality) > Google Takeout (has sidecar metadata) > J:\圖片 (may be older exports) > family NAS (curated copies). When two files are identical, prefer the source higher in the priority chain.

**Tool recommendation:** `dupeGuru` (GUI) or a custom Python script using `imagehash` + SQLite for a scriptable, repeatable approach that integrates with the migration pipeline.

---

## 5. Vector DB + AI Search Layer

### Goal

Search photos by natural language: "group photo at a restaurant with family", "the trip to Germany", "Kiki the dog", "beach with sunset". Not just by date or filename.

### Embedding pipeline

1. **Ingest:** walk the NAS media tree, skip already-indexed files (track by file path + mtime in SQLite)
2. **Vision model:** run each image through a CLIP model (e.g. `openai/clip-vit-large-patch14` via `transformers`) to get a 768-dim image embedding
3. **Caption generation:** run a lightweight captioning model (e.g. `Salesforce/blip-image-captioning-base` or `llava` for richer descriptions) to generate text descriptions — store these in the DB for full-text search and LLM context
4. **Face detection:** use `face_recognition` or `InsightFace` to detect and cluster faces; assign labels manually or via a small UI ("who is this?")
5. **GPS → place name:** reverse-geocode GPS coordinates to human-readable place names using `timezonefinder` + a geocoding library (`geopy` + Nominatim)
6. **Index:** upsert embeddings + metadata into vector DB

### Vector DB: Qdrant (recommended)

Self-hosted on the NAS via Docker. Supports: named collections, payload filters (filter by date, owner, place before vector search), cosine similarity, and a REST API. Alternatives: Chroma (simpler, Python-native, less scalable), Weaviate (heavier, more features), pgvector (if already using Postgres).

### Metadata stored per vector

```json
{
  "file_path": "\\LinXiaoYun\\media\\personal\\EJ\\2024\\20240601_大阪\\IMG_4234.jpg",
  "owner": "EJ",
  "date": "2024-06-01",
  "place_name": "Osaka, Japan",
  "gps": [34.6937, 135.5023],
  "caption": "Two people smiling at a street food stall at night",
  "faces": ["EJ", "曉灣"],
  "tags": ["travel", "food", "night"],
  "is_shared": true
}
```

### Query flow

User query → embed with CLIP text encoder → nearest-neighbor search in Qdrant (filtered by owner/date if specified) → return top-K file paths → display thumbnails.

---

## 6. Phased Roadmap

### Phase 1 — Embed Google Takeout metadata (immediate, tool already built)

Run `galbum` on `D:\Downloads\Takeout\Google 相簿` to embed all JSON sidecar metadata (timestamp, GPS, description) into the media files before migration. This is already built and tested.

### Phase 2 — Deduplication scan

Script to hash all 4 locations, produce a duplicate report, and generate a migration manifest: which files to keep, where they go in the new tree, which are duplicates to discard.

### Phase 3 — Migration to unified NAS structure

Execute the migration manifest. Move/copy files into `\\LinXiaoYun\media\personal\EJ\` and `\\LinXiaoYun\media\archive\legacy_unsorted\`. Create hardlinks for already-shared family content. Delete confirmed duplicates.

### Phase 4 — Reference database + sharing workflow

SQLite DB tracking `(owner_path, shared_path, shared_by, shared_at)`. CLI command: `photo-manager share <file> --to family` creates a hardlink and inserts a DB record. `photo-manager unshare <file>` removes the link and record.

### Phase 5 — AI indexing pipeline

Docker Compose stack on NAS: Qdrant + a Python indexer service that watches for new files (inotify or cron), generates CLIP embeddings + captions + face clusters, and upserts to Qdrant.

### Phase 6 — Search interface

Simple web UI or CLI: natural language query → vector search → results with thumbnails. Optionally integrate with Synology Photos via API.

---

## 7. Open Questions

Before coding starts, the following decisions are needed:

1. **NAS model and OS:** Is LinXiaoYun a Synology? Which DSM version? This affects Docker support, hardlink behavior, and SMB symlink settings.

2. **Who are the owners?** Just EJ, or multiple family members each with their own personal folder? This determines if the `personal/` tree has multiple subdirectories.

3. **iPhone backup gap (2018–2019):** Are those years backed up elsewhere, or are they genuinely missing? Worth locating before migration.

4. **Face labeling UX:** Manual labeling via a CLI prompt, a simple web form, or integrate with an existing tool? This has a big impact on Phase 5 effort.

5. **Takeout scope:** The Google Takeout covers 2011–2025. Is the full Takeout downloaded, or just a partial export? There may be more data to pull before the Google account is closed or cleaned up.

6. **`galbum` integration point:** Should Phase 1 (Takeout embedding) happen before or after deduplication? Running it before means the migrated files already have metadata; running it after means less work on files that get discarded as duplicates.

7. **Storage budget:** The iPhone backup alone (2017–2026) plus Takeout (2011–2025) plus J:\圖片 (2006–2024) could easily be 200–500 GB. Is NAS storage sufficient, and should RAW files and videos be treated differently from JPEGs?
