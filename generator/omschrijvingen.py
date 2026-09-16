#!/usr/bin/env python3
"""Hulpmiddel voor handgeschreven omschrijvingen (fase 4).

  python3 generator/omschrijvingen.py batch 1 [--grootte 200] [--min 2 --max 4]
      schrijft data/omschrijvingen/batch-001-in.tsv (woord, huidige omschrijving)
  python3 generator/omschrijvingen.py check data/omschrijvingen/batch-001.tsv
      controleert een ingevulde batch (woord<TAB>oms1<TAB>oms2[<TAB>oms3])
  python3 generator/omschrijvingen.py merge
      voegt alle goedgekeurde batches samen tot data/omschrijvingen.tsv
"""
import argparse
import csv
import glob
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from woorden import lees_woordenlijst, split_letters, wrap_omschrijving  # noqa: E402

DATA = os.path.join(HIER, "data")
BATCH_DIR = os.path.join(DATA, "omschrijvingen")


def kandidaten(min_len, max_len):
    rows = [r for r in lees_woordenlijst(os.path.join(DATA, "woorden.tsv"))
            if min_len <= len(split_letters(r["woord"])) <= max_len]
    rows.sort(key=lambda r: r["rang"])
    return rows


def cmd_batch(args):
    rows = kandidaten(args.min, args.max)
    start = (args.nummer - 1) * args.grootte
    deel = rows[start:start + args.grootte]
    if not deel:
        sys.exit(f"geen woorden voor batch {args.nummer} ({len(rows)} kandidaten)")
    pad = os.path.join(BATCH_DIR, f"batch-{args.nummer:03d}-in.tsv")
    with open(pad, "w", encoding="utf-8") as f:
        f.write("woord\thuidige_omschrijving\n")
        for r in deel:
            f.write(f"{r['woord']}\t{r['omschrijving']}\n")
    print(f"{pad}: {len(deel)} woorden (van {len(rows)} kandidaten van {args.min}-{args.max} letters)")


def stam(woord):
    w = woord.lower()
    return w if len(w) < 4 else w[:4]


def controleer(pad, bekend):
    fouten, n_woorden, n_oms = [], 0, 0
    gezien = set()
    with open(pad, encoding="utf-8") as f:
        for nr, regel in enumerate(f, 1):
            regel = regel.rstrip("\n")
            if not regel.strip() or regel.startswith("#") or regel.startswith("woord\t"):
                continue
            delen = [d.strip() for d in regel.split("\t")]
            woord, omsen = delen[0].upper(), [d for d in delen[1:] if d]
            if woord not in bekend:
                fouten.append(f"regel {nr}: {woord} staat niet in de woordenlijst")
                continue
            if woord in gezien:
                fouten.append(f"regel {nr}: {woord} komt dubbel voor")
            gezien.add(woord)
            if not 1 <= len(omsen) <= 3:
                fouten.append(f"regel {nr}: {woord} heeft {len(omsen)} omschrijvingen (1-3 verwacht)")
            n_woorden += 1
            for o in omsen:
                n_oms += 1
                if not wrap_omschrijving(o):
                    fouten.append(f"regel {nr}: {woord}: '{o}' past niet in 2 regels van 9 tekens")
                if stam(woord) in o.lower().replace("-", ""):
                    fouten.append(f"regel {nr}: {woord}: '{o}' bevat de stam van het antwoord")
                if o[0].islower():
                    fouten.append(f"regel {nr}: {woord}: '{o}' begint met een kleine letter")
                if o.endswith("."):
                    fouten.append(f"regel {nr}: {woord}: '{o}' eindigt op een punt")
            if len(set(o.lower() for o in omsen)) != len(omsen):
                fouten.append(f"regel {nr}: {woord}: dubbele omschrijving")
    return fouten, n_woorden, n_oms


def cmd_check(args):
    bekend = {r["woord"] for r in lees_woordenlijst(os.path.join(DATA, "woorden.tsv"))}
    exit_code = 0
    for pad in args.bestanden:
        fouten, n_w, n_o = controleer(pad, bekend)
        print(f"{'FOUT' if fouten else 'OK'}  {pad}: {n_w} woorden, {n_o} omschrijvingen")
        for fout in fouten:
            print("  " + fout)
        if fouten:
            exit_code = 1
    return exit_code


def cmd_merge(args):
    bekend = {r["woord"] for r in lees_woordenlijst(os.path.join(DATA, "woorden.tsv"))}
    uit = os.path.join(DATA, "omschrijvingen.tsv")
    n = 0
    with open(uit, "w", encoding="utf-8") as f:
        f.write("woord\tomschrijving\tbron\n")
        for pad in sorted(glob.glob(os.path.join(BATCH_DIR, "batch-*.tsv"))):
            if pad.endswith("-in.tsv"):
                continue
            fouten, _, _ = controleer(pad, bekend)
            if fouten:
                print(f"overgeslagen (fouten): {pad}")
                continue
            with open(pad, encoding="utf-8") as g:
                for regel in g:
                    regel = regel.rstrip("\n")
                    if not regel.strip() or regel.startswith("#") or regel.startswith("woord\t"):
                        continue
                    delen = [d.strip() for d in regel.split("\t")]
                    for o in delen[1:]:
                        if o:
                            f.write(f"{delen[0].upper()}\t{o}\tclaude\n")
                            n += 1
    print(f"{uit}: {n} omschrijvingen")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("batch"); b.add_argument("nummer", type=int); b.add_argument("--grootte", type=int, default=200)
    b.add_argument("--min", type=int, default=2); b.add_argument("--max", type=int, default=4); b.set_defaults(fn=cmd_batch)
    c = sub.add_parser("check"); c.add_argument("bestanden", nargs="+"); c.set_defaults(fn=cmd_check)
    m = sub.add_parser("merge"); m.set_defaults(fn=cmd_merge)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
