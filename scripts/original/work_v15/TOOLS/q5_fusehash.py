#!/usr/bin/env python3
"""Q5: thu hash tren chinh khoi fuse (huong chua thu cua Q2). Doc-only."""
import hashlib, json, os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
TARGET = bytes.fromhex("dc95c0578ef29c83423949bf031ec55130573764038f07ca229d3be1b9c5381e")

def main():
    d = json.load(open(P("FUSE", "fuse2.json")))
    r = {int(k): v for k, v in d["regs"].items()}
    buf = b"".join(struct.pack("<I", r.get(o, 0)) for o in range(0, 0x2000, 4))
    hits, trials = 0, 0
    zones = [("fuse[0:0x718]", 0, 0x718), ("fuse[0:0x344]", 0, 0x344),
             ("fuse[0x71C:0x2000]", 0x71C, 0x2000), ("fuse[0:0x2000]", 0, 0x2000),
             ("fuse[0x110:0x198]", 0x110, 0x198), ("fuse[0xd4:0xf4]", 0xD4, 0xF4)]
    for nm, lo, hi in zones:
        for algo in ("sha256", "sha3_256", "blake2s", "sha1", "md5"):
            trials += 1
            if hashlib.new(algo, buf[lo:hi]).digest()[:32] == TARGET:
                print(f"  KHOP {algo}({nm})"); hits += 1
    for sz in (0x20, 0x40, 0x100, 0x200, 0x400, 0x800, 0x1000, 0x1800):
        for s in range(0, 0x2000 - sz + 1, 4):
            trials += 1
            if hashlib.sha256(buf[s:s + sz]).digest() == TARGET:
                print(f"  KHOP fuse[0x{s:x}:0x{s+sz:x}]"); hits += 1
    print(f"  {trials:,} phep thu -> {hits} khop")
    json.dump(dict(target=TARGET.hex(), trials=trials, hits=hits,
                   note="hash tren chinh khoi fuse: 0 khop -> can ROM TU106 khac"),
              open(P("FUSE", "q5_hash.json"), "w"), indent=1)
    return hits

if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
