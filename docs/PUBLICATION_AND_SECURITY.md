# Publication, licensing and security audit

**Two outputs:** (1) a conservatively selected GitHub-ready *review candidate*, and (2) a **private complete original-byte archive**. The private archive is **not safe to publish as-is**. It includes raw machine paths, local network IPs and firmware/VBIOS/board artifacts requiring rights review.

## Automated decisions

- Kept nearly all unique report Markdown and project-authored source scripts when their contents appeared text-only and they passed a basic secret-marker scan. All shipped historical reports are labelled as such by the top-level docs, even if an individual document contains outdated claims.
- Kept many smaller raw CSV/JSON/log/disassembly excerpts under `evidence/original/`.
- Detected byte-identical files using SHA-256 and kept one public canonical copy. All duplicate input names remain indexed.
- Replaced obvious private IPv4 ranges, `/home/<user>/` prefixes, one recorded lab username and GPU UUID strings with placeholders **only in public copies**. The manifest records which original files were changed. This is only a basic automated scrub.
- **Not included publicly by default:** NVIDIA firmware/GSP/VBIOS dumps and other binaries, unlicensed third-party source snapshots, boardview CAD, photographs (may contain serials / EXIF), embedded archives, compiled files, very large generated JSON/disassembly. SHA-256 hashes and original paths remain listed. See `publication_reason` in the inventory.

## Remaining manual checks before creating a public GitHub repository

1. Audit all files identified as public, especially shell/Python scripts and logs, for private details not recognized by regex (usernames, endpoint hostnames, filesystem mount names, serial numbers, camera metadata, tokens in unusual formats).
2. Confirm you have the right to publish each script, disassembly excerpt and report; add a project-specific license only with the authors' consent. Do not assume NVIDIA or third-party material becomes open source because it was used for research.
3. Check claims against their **original captures**. This repository does not independently prove the provenance or timing of every reported live measurement.
4. Avoid publishing exploit claims unsupported by a realistic threat model. Loading unsigned `.ko` as **already privileged root** on a permissive host is not, by itself, an unprivileged privilege-escalation vulnerability.
5. Consider using Git LFS / releases or external archival hosting for large artifacts after permissions review. Never commit the private complete archive to the public git history.

The package is **structured and reviewable**, not a legal clearance or exhaustive credential-leak assessment.

## V2 additions

Ten additional uploads were inspected by byte hash. All raw tarballs and two misnamed binary dumps are kept only in the **private** package. The public package contains only 36 unique UTF-8 source/report/JSON items with the same basic identifier scrub used for V1. Original unredacted bytes appear in the private archive. See [V2 supplemental review](SOURCE_PACK_REVIEW_20261106.md) and [supplemental original-byte/source map](../manifests/SUPPLEMENTAL_SOURCE_INVENTORY.csv). Publishing scripts may require permission and security review.

## V3 publication note

Eight additional snapshots were curated; original tarballs retained private. Public documents/scripts/JSON were scrubbed for lab addresses, account directories, GPU UUID, **CMP 40HX device serial** and the known **GPU PDI**. The same device-ID scrub was also applied to previous public V2 files that were found to contain these identifiers. Changes are traceable via the SHA-256 inventories. `0x0000000000000000` in PDI contexts is a **redaction placeholder**. Do not post the private RAW archive to GitHub. No automated filter ensures complete privacy or licensing compliance.

## V4 source preservation

All seven supplemental tarballs, even duplicate-content uploads, are included byte-for-byte in the **private** archive. The 11 distinct public text sources were screened and scrubbed using the same known patterns as V3. Original raw bytes remain private. This is not an assurance of complete privacy or distribution rights.
