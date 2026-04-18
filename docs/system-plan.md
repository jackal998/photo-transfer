# photo-transfer — Plan

**Scope:** One-time migration of personal media from 3 sources into a unified structure on the NAS. Deduplication, AI search, family sharing, and ongoing management are handled by separate projects.

---

## Sources

| Source | Location | Status |
|--------|----------|--------|
| iPhone backup | `\\LinXiaoYun\home\Photos\MobileBackup\iPhone\` — already on NAS | Keep in place (auto-upload path, untouched) |
| Google Takeout | `D:\Downloads\Takeout\Google 相簿` — local disk | `galbum` already run; metadata embedded |
| Personal archive | `J:\圖片` — NAS, unorganized | Needs migration |
| Family NAS | `\\LinXiaoYun\photo` | **Out of scope** |

---

## Target Structure

All migrated content lands under the user's Synology personal space, alongside the existing iPhone auto-upload path:

```
\\LinXiaoYun\home\Photos\          →  /volume2/homes/J/Photos/
├── MobileBackup\
│   └── iPhone\
│       └── YYYY\                  ← auto-upload, untouched
├── YYYY\
│   └── YYYYMMDD_slug\             ← migrated from Takeout + J:\圖片
├── undated\                       ← no EXIF; manual review
└── _archive\
    └── legacy_unsorted\           ← unorganized J:\圖片 top-level folders
```

### Rules

- **Naming:** `YYYYMMDD_slug` — CJK allowed (`20240601_大阪`), underscores, no spaces
- **Date source:** EXIF `DateTimeOriginal` only — no `mtime` fallback
- **No EXIF:** file goes to `undated\` (never silently mis-dated)
- **Live Photos:** same-stem HEIC+MOV pairs are atomic — always move and dedup together
- **Collisions:** append `_2`, `_3`, etc. on filename collision in destination

### Source priority (for dedup)

iPhone backup > Google Takeout > J:\圖片

---

## Phases

### Phase 1 — Deduplication scan (non-destructive)

Script hashes all 3 sources (SHA-256 + pHash), produces `migration_manifest.sqlite`. No files are moved or deleted. pHash near-matches get `REVIEW_DUPLICATE` status and are never auto-deleted.

```sql
CREATE TABLE migration_manifest (
  id           INTEGER PRIMARY KEY,
  source_path  TEXT NOT NULL,
  dest_path    TEXT,
  action       TEXT NOT NULL,  -- MOVE | SKIP | REVIEW_DUPLICATE | UNDATED
  source_hash  TEXT,
  phash        TEXT,
  duplicate_of TEXT,
  reason       TEXT,
  executed     INTEGER DEFAULT 0
);
```

### Phase 2 — Migration

Execute the manifest: copy files to `/volume2/homes/J/Photos/YYYY/YYYYMMDD_slug/`. Delete confirmed duplicates only after the new structure is verified complete.

---

## NAS Reference

| Item | Value |
|------|-------|
| Device | Synology DS920+ |
| DSM | 7.2.2 |
| Photos path (Linux) | `/volume2/homes/J/Photos/` |
| Photos path (SMB) | `\\LinXiaoYun\home\Photos\` |
| SSH user | `jackal998` (admin) — use full path, not `~/` |
| volume2 free | 1.8 TB |
