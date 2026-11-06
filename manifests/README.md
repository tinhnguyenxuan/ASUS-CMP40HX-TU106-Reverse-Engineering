# Manifest semantics

**Original ZIP:** `tonghopbaocaotatca.zip`, SHA-256 `199dac9335a779f33761244a207e4bac3a58ce9c39768fe64def9996a8e4995e`

Original entries: **1,500**, original uncompressed payload: **726,799,993 bytes**.

Publication disposition (counts of original entries, not unique contents):

- `public_unmodified`: 724
- `public_redacted`: 275
- `duplicate_content`: 234
- `private_only`: 267

One byte-identical original may be represented by a public canonical file; duplicates have `public_path` pointing to it. `SOURCE_INVENTORY.csv` records SHA-256 of the **original input bytes**, not redacted public content; `PUBLIC_SHA256SUMS.txt` records published bytes. Redaction was applied to 275 canonical published files.

`full_path` is the location inside the **private** complete archive (relative to its archive root). Source paths are relative to `codex-work/` in the uploaded ZIP.

## V3

V3 supplements the original 1,500-item source ledger with 500 V2 and **1,035 V3 historical-source occurrences** (some repeats). The V3 CSV records byte hashes of source originals and canonical publication paths. **Public V3 may differ from V1/V2 public bytes** due to additional masking of device-unique serial and PDI; the regenerated `PUBLIC_SHA256SUMS.txt` is authoritative for shipped published bytes. Values identifying a specific device are omitted from public content by design. Original byte-level sources are in the private archive.

## V4

[V4_SOURCE_INVENTORY.csv](V4_SOURCE_INVENTORY.csv) indexes 618 source entries from 7 additional tarballs. [V4_UPLOAD_ARCHIVES_SHA256.csv](V4_UPLOAD_ARCHIVES_SHA256.csv) checks the original byte-identical archives in the private package. File hashes in prior manifests remain original-source hashes, distinct from public redacted hashes.
