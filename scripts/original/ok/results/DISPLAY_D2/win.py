import re,sys
pat=re.compile(r'^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*\t?([a-z0-9.]+)?\s*(.*)$')
ins={}
for ln in open('gsp.dis',errors='replace'):
    m=pat.match(ln)
    if m: ins[int(m.group(1),16)]=(m.group(2).replace(' ',''),(m.group(3) or '').strip(),(m.group(4) or '').strip())
def win(s,e):
    for a in sorted(ins):
        if s<=a<=e:
            r,mn,o=ins[a]
            print(f"{a:09x}: {r:<8} {mn:<7} {o}")
if __name__=='__main__':
    win(int(sys.argv[1],16),int(sys.argv[2],16))
