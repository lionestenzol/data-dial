#!/usr/bin/env python
"""Experiment 011 - replace the exp009 rsync stand-in with the REAL rsync binary
and see whether the crossover headline survives. Honest tool, same pairs."""
from __future__ import annotations
import json, os, re, subprocess, sys, tempfile, gzip, bz2, lzma
sys.path.insert(0, "experiments")
import exp009_crossover as E9

RSYNC = "/tmp/claude-0/-home-user-data-dial/44084ae5-9f89-5472-8890-929f5006120b/scratchpad/mechanics/rsync/rsync"

def transfer_bytes(x): 
    return min(len(gzip.compress(x,9)), len(lzma.compress(x)), len(bz2.compress(x)))

def real_rsync_delta(old: bytes, new: bytes, tmp):
    """Bytes rsync actually sends to turn B's `old` into `new`, delta algorithm
    forced on (local transfers default to whole-file)."""
    src=os.path.join(tmp,"src"); dst=os.path.join(tmp,"dst")
    os.makedirs(src,exist_ok=True); os.makedirs(dst,exist_ok=True)
    open(os.path.join(src,"f"),"wb").write(new)
    open(os.path.join(dst,"f"),"wb").write(old)   # B's basis
    r=subprocess.run([RSYNC,"--no-whole-file","--no-compress","--stats","-a",
                      os.path.join(src,"f"), os.path.join(dst,"")],
                     capture_output=True,text=True)
    # verify reconstruction is byte-exact
    got=open(os.path.join(dst,"f"),"rb").read()
    exact = got==new
    sent=lit=matched=None
    for line in r.stdout.splitlines():
        m=re.search(r"Total bytes sent:\s*([\d,]+)",line); 
        if m: sent=int(m.group(1).replace(",",""))
        m=re.search(r"Literal data:\s*([\d,]+)",line)
        if m: lit=int(m.group(1).replace(",",""))
        m=re.search(r"Matched data:\s*([\d,]+)",line)
        if m: matched=int(m.group(1).replace(",",""))
    return {"sent":sent,"literal":lit,"matched":matched,"exact":exact}

def main():
    # same delta pairs exp009 used
    pairs=[]
    for path in ("HANDOFF.md","experiments/FINDINGS.md","README.md","research/OBJECTIVES.json"):
        pairs+=E9.git_versions(path)
    pairs=pairs[:24]
    print(f"{len(pairs)} delta pairs (same as exp009)\n")
    print(f"{'pair':<34}{'new':>8}{'mine':>8}{'rsync':>8}{'xfer':>8}  exact")
    rows=[]; my_tot=rs_tot=tx_tot=0
    with tempfile.TemporaryDirectory() as tmp:
        for i,(path,old,new) in enumerate(pairs):
            mine=E9.rsync_delta_bytes(old,new)[0]
            rs=real_rsync_delta(old,new,tmp)
            tx=transfer_bytes(new)
            my_tot+=mine; rs_tot+=rs["sent"]; tx_tot+=tx
            rows.append({"pair":f"{os.path.basename(path)}_{i}","new":len(new),
                         "mine":mine,"rsync_sent":rs["sent"],"rsync_literal":rs["literal"],
                         "transfer":tx,"exact":rs["exact"]})
            print(f"{os.path.basename(path)+'_'+str(i):<34}{len(new):>8}{mine:>8}{rs['sent']:>8}{tx:>8}  {rs['exact']}")
    print(f"\n{'TOTAL delta bytes':<34}{'':>8}{my_tot:>8}{rs_tot:>8}{tx_tot:>8}")
    print(f"\nmy stand-in total: {my_tot}")
    print(f"real rsync total:  {rs_tot}   (mine/real = {my_tot/rs_tot:.2f}x)")
    print(f"transfer total:    {tx_tot}")
    all_exact=all(r['exact'] for r in rows)
    print(f"real rsync byte-exact on all pairs: {all_exact}")

    # recompute the exp009 headline with REAL rsync in the delta arm
    R=json.load(open("experiments/exp009_results.json"))
    # exp009 delta items total (my stand-in) vs their transfer
    items=R["rows"]
    # map: only delta-regime items had a related version; recompute always_delta
    # with real rsync delta for those, stand-in transfer elsewhere unchanged.
    delta_regime=[it for it in items if it["regime"]=="delta"]
    # the selector total at T=1s from exp009 (unchanged - recompute drove it)
    sel=R["sweep"]["1000.0"]["selector"]
    # always_delta old (stand-in) and new (real): delta items change
    always_delta_old=R["sweep"]["1000.0"]["always_delta"]
    # replace delta-regime delta bytes: old stand-in sum vs real rsync sum
    old_delta_sum=sum(it["mechs"]["delta"][0] for it in delta_regime if "delta" in it["mechs"])
    always_delta_new = always_delta_old - old_delta_sum + rs_tot
    print(f"\n=== exp009 headline recomputed with REAL rsync ===")
    print(f"selector (unchanged, recompute-driven): {sel}")
    print(f"always-delta with MY stand-in:  {always_delta_old}  -> sel beats {always_delta_old/sel:.2f}x")
    print(f"always-delta with REAL rsync:   {always_delta_new}  -> sel beats {always_delta_new/sel:.2f}x")
    out={"pairs":rows,"my_total":my_tot,"real_rsync_total":rs_tot,"transfer_total":tx_tot,
         "all_exact":all_exact,"selector_1s":sel,
         "always_delta_standin":always_delta_old,"always_delta_real":always_delta_new,
         "sel_beats_standin":always_delta_old/sel,"sel_beats_real":always_delta_new/sel}
    json.dump(out,open("experiments/exp011_results.json","w"),indent=2)

if __name__=="__main__": main()
