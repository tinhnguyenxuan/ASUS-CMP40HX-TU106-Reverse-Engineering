# In-progress consumer scan review

The first saved `run.log` ended with `struct.error` while reading `u64(buf,k+8)`:
the final iteration required 4,468 bytes from a 4,464-byte buffer. A scan of
multiword records must require the entire record span before unpacking.
This run does not establish that a scan found no consumers or no valid arrays.
Do not interpret a partially executed scan as exhaustive negative evidence.

The worker may still be correcting this failure. Poll its existing job handle;
do not start a duplicate merely because this intermediate run failed.

The fingerprint observation in the log agrees with the reviewed source mapping:
file `0x22378`, VA `0x04022338`. Only that bounded observation is accepted here.
Function, table and engine identities remain unproven pending a successful run
and raw-instruction/dataflow review.

The next run progressed past the record-buffer scan but stopped at Capstone initialization: `Cs(CS_ARCH_RISCV, CS_MODE_64)` raises `CS_ERR_MODE`. RISC-V requires its architecture-specific mode (`CS_MODE_RISCV64`, plus `CS_MODE_RISCVC` when decoding compressed instructions). The printed label/pointer pairs are unverified candidates, not established BINDATA archives or consumer identities. A complete instruction scan is still outstanding.
