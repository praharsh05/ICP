"""
Citizens Ego3 Cache Builder - Pre-compute 3-hop family networks
CSV IN / CSV OUT — Local
- Reads citizens_person_entity, citizens_parent_links, citizens_spouse_links from CSV
- Optionally load a single person_id, a file of person_ids (one per line), or 'full' (use all)
- Writes a CSV with columns: entity_person_id, ego_json, generated_at
"""

from pyspark.sql import SparkSession, functions as F, types as T
from collections import defaultdict, deque
import json, datetime, os


# ── CONFIG: edit these paths/options only ──────────────────────────────────────
PERSON_ENTITY_CSV   = "./out/citizens_person_entity/part-00000-06542abc-55ce-497a-93df-d00b63007866-c000.csv"    # entity_person_id, full_name/full_name_en, sex, dob
PARENT_LINKS_CSV    = "./out/out_links/citizens_parent_links/part-00000-f49f3066-b527-462a-bed4-6a4c285a1f0a-c000.csv"     # parent_entity_person_id, child_entity_person_id
SPOUSE_LINKS_CSV    = "./out/out_links/citizens_spouse_links/part-00000-48d6eaf2-dcfb-4044-b856-4226870e0483-c000.csv"     # husband_entity_person_id, wife_entity_person_id
PERSON_IDS_TXT      = None  # e.g. "./person_ids.txt" (one entity_person_id per line), or None
SINGLE_PERSON_ID    = None  # e.g. "C:abc123..." to build only this ego
PROCESS_FULL        = True  # if True and no PERSON_IDS_TXT/SINGLE_PERSON_ID, process all in PERSON_ENTITY_CSV

LANG                = "en"  # "en" or "ar"
DEPTH               = 3     # BFS hops (1–5 recommended)
BATCH_SIZE          = 1000  # kept for API parity; BFS is in-driver here
CSV_HAS_HEADER      = True
CSV_DELIMITER       = ","
CSV_INFER_SCHEMA    = True
OUTPUT_DIR          = "./out/out_ego3"  # output folder; will contain a CSV dataset
SINGLE_FILE_OUTPUT  = True          # coalesce(1) to write a single part CSV
# ──────────────────────────────────────────────────────────────────────────────


def kin_term_en(path_steps, sex):
    U = path_steps.count("U")
    D = path_steps.count("D")
    S = path_steps.count("S")
    if path_steps == "": return "self"
    if U==0 and D==0 and S>=1: return "spouse"
    if U==1 and D==0: return "father" if sex=="M" else "mother" if sex=="F" else "parent"
    if U==2 and D==0: return "grandfather" if sex=="M" else "grandmother" if sex=="F" else "grandparent"
    if U==0 and D==1: return "son" if sex=="M" else "daughter" if sex=="F" else "child"
    if U==0 and D==2: return "grandson" if sex=="M" else "granddaughter" if sex=="F" else "grandchild"
    if U==1 and D==1 and S==0: return "brother" if sex=="M" else "sister" if sex=="F" else "sibling"
    if U==1 and D==2: return "nephew" if sex=="M" else "niece" if sex=="F" else "nibling"
    if U==2 and D==1: return "uncle" if sex=="M" else "aunt" if sex=="F" else "aunt/uncle"
    if U>=2 and D>=2 and S==0:
        degree = min(U,D) - 1
        removal = abs(U-D)
        degree_names = {1:"first",2:"second",3:"third",4:"fourth"}
        base = f"{degree_names.get(degree,str(degree)+'th')} cousin"
        if removal==0: return base
        if removal==1: return base + " once removed"
        if removal==2: return base + " twice removed"
        return base + f" {removal} times removed"
    if S>=1:
        base = kin_term_en(path_steps.replace("S",""), sex)
        if base == "self": return "spouse"
        return base + "-in-law"
    return "relative"

def kin_term_ar(path_steps, sex):
    U = path_steps.count("U")
    D = path_steps.count("D")
    S = path_steps.count("S")
    if path_steps == "": return "أنا"
    if U==0 and D==0 and S>=1: return "زوج/زوجة"
    if U==1 and D==0: return "الأب" if sex=="M" else "الأم" if sex=="F" else "الوالد"
    if U==2 and D==0: return "الجد" if sex=="M" else "الجدة" if sex=="F" else "الجد/الجدة"
    if U==0 and D==1: return "الابن" if sex=="M" else "الابنة" if sex=="F" else "الابن/الابنة"
    if U==0 and D==2: return "الحفيد" if sex=="M" else "الحفيدة" if sex=="F" else "الحفيد/الحفيدة"
    if U==1 and D==1 and S==0: return "الأخ" if sex=="M" else "الأخت" if sex=="F" else "الأخ/الأخت"
    if U==1 and D==2: return "ابن الأخ/الأخت" if sex=="M" else "ابنة الأخ/الأخت"
    if U==2 and D==1: return "العم/الخال" if sex=="M" else "العمة/الخالة"
    if U>=2 and D>=2 and S==0: return "ابن العم/الخال" if sex=="M" else "ابنة العم/الخالة"
    if S>=1:
        base = kin_term_ar(path_steps.replace("S",""), sex)
        if base == "أنا": return "زوج/زوجة"
        return base + " (نسَب)"
    return "قريب"

def load_person_ids(spark, persons_df):
    # Priority: SINGLE_PERSON_ID > PERSON_IDS_TXT > PROCESS_FULL
    if SINGLE_PERSON_ID:
        return [SINGLE_PERSON_ID]
    if PERSON_IDS_TXT and os.path.exists(PERSON_IDS_TXT):
        ids = [r[0] for r in spark.read.text(PERSON_IDS_TXT).collect()]
        return [x for x in ids if x]
    if PROCESS_FULL:
        return [r[0] for r in persons_df.select("entity_person_id").collect()]
    return []

def main():
    spark = (SparkSession.builder
             .appName("citizens_ego3_cache_builder_csv_local")
             .getOrCreate())
    spark.sparkContext.setLogLevel("INFO")

    print("=" * 80)
    print("CITIZENS EGO3 CACHE BUILDER (CSV IN / CSV OUT)")
    print("=" * 80)

    # ---- Read inputs (CSV) ----------------------------------------------------
    reader = (spark.read
              .option("header", str(CSV_HAS_HEADER).lower())
              .option("inferSchema", str(CSV_INFER_SCHEMA).lower())
              .option("sep", CSV_DELIMITER)
              .option("mode", "PERMISSIVE")
              .option("multiLine", "true")
              .option("quote", '"')
              .option("escape", '"'))

    pe_raw = reader.csv(PERSON_ENTITY_CSV)
    pl_raw = reader.csv(PARENT_LINKS_CSV)
    sl_raw = reader.csv(SPOUSE_LINKS_CSV)

    pe = pe_raw.toDF(*[c.lower() for c in pe_raw.columns])
    pl = pl_raw.toDF(*[c.lower() for c in pl_raw.columns])
    sl = sl_raw.toDF(*[c.lower() for c in sl_raw.columns])

    # Make sure expected columns exist (rename/backfill if needed)
    # Person entity
    needed_pe = {"entity_person_id","full_name","full_name_en","sex","dob"}
    for col in needed_pe:
        if col not in pe.columns:
            pe = pe.withColumn(col, F.lit(None).cast("string"))
    pe = pe.select(
        "entity_person_id",
        F.coalesce(F.col("full_name_en"), F.col("full_name")).alias("full_name"),
        F.col("sex").cast("string").alias("sex"),
        "dob"
    )

    # Parent links
    for col in ["parent_entity_person_id","child_entity_person_id"]:
        if col not in pl.columns:
            pl = pl.withColumn(col, F.lit(None).cast("string"))
    pl = pl.select("parent_entity_person_id","child_entity_person_id")

    # Spouse links
    for col in ["husband_entity_person_id","wife_entity_person_id"]:
        if col not in sl.columns:
            sl = sl.withColumn(col, F.lit(None).cast("string"))
    sl = sl.select("husband_entity_person_id","wife_entity_person_id")

    print(f"✓ Loaded {pe.count():,} citizens")
    print(f"✓ Loaded {pl.count():,} parent-child links")
    print(f"✓ Loaded {sl.count():,} spouse links")

    # ---- Collect to driver for BFS -------------------------------------------
    print("\nCollecting data into memory for BFS traversal...")
    persons = {r["entity_person_id"]: {
        "full_name": r["full_name"],
        "sex": r["sex"],
        "dob": str(r["dob"]) if r["dob"] else None
    } for r in pe.collect()}

    pdict = defaultdict(set)  # child -> parents
    cdict = defaultdict(set)  # parent -> children
    for r in pl.collect():
        p, c = r["parent_entity_person_id"], r["child_entity_person_id"]
        if p and c:
            pdict[c].add(p)
            cdict[p].add(c)
    parents = dict(pdict)
    children = dict(cdict)

    sdict = defaultdict(set)  # spouses (bidirectional)
    for r in sl.collect():
        h, w = r["husband_entity_person_id"], r["wife_entity_person_id"]
        if h and w:
            sdict[h].add(w)
            sdict[w].add(h)
    spouses = dict(sdict)

    # ---- Which persons to build ------------------------------------------------
    ids = load_person_ids(spark, pe)
    print(f"\nProcessing {len(ids)} ego network(s)...")

    # ---- BFS + kinship --------------------------------------------------------
    out_rows = []
    for idx, eid in enumerate(ids):
        if idx and idx % 100 == 0:
            print(f"  Processed {idx}/{len(ids)} networks...")

        if eid not in persons:
            print(f"  ⚠️  Skipping {eid} - not in citizens data")
            continue

        nodes = {}
        edges = set()
        visited_depth = {eid: 0}
        q = deque([(eid, "", 0)])

        def sex_of(x):  return persons.get(x, {}).get("sex")
        def label_of(x): return persons.get(x, {}).get("full_name", x)

        # ego
        nodes[eid] = {"id": eid, "label": label_of(eid), "sex": sex_of(eid), "kin": "self", "cluster": None}

        while q:
            cur, path, g = q.popleft()

            # parents (U)
            if g < DEPTH:
                for par in parents.get(cur, []):
                    edges.add((cur, par, "CHILD_OF"))
                    new_g = g + 1
                    if visited_depth.get(par, 999) > new_g:
                        visited_depth[par] = new_g
                        q.append((par, path + "U", new_g))
                    kin = kin_term_en(path + "U", sex_of(par)) if LANG == "en" else kin_term_ar(path + "U", sex_of(par))
                    nodes[par] = {"id": par, "label": label_of(par), "sex": sex_of(par), "kin": kin, "cluster": None}

            # children (D)
            if g < DEPTH:
                for chi in children.get(cur, []):
                    edges.add((chi, cur, "CHILD_OF"))
                    new_g = g + 1
                    if visited_depth.get(chi, 999) > new_g:
                        visited_depth[chi] = new_g
                        q.append((chi, path + "D", new_g))
                    kin = kin_term_en(path + "D", sex_of(chi)) if LANG == "en" else kin_term_ar(path + "D", sex_of(chi))
                    nodes[chi] = {"id": chi, "label": label_of(chi), "sex": sex_of(chi), "kin": kin, "cluster": None}

            # spouses (S) — lateral
            for sp in spouses.get(cur, []):
                edges.add((cur, sp, "SPOUSE_OF"))
                edges.add((sp, cur, "SPOUSE_OF"))
                new_g = g  # spouse hop doesn't increase genealogical distance
                if visited_depth.get(sp, 999) >= new_g:
                    visited_depth[sp] = new_g
                    q.append((sp, path + "S", new_g))
                kin = "spouse" if LANG == "en" else "زوج/زوجة"
                nodes[sp] = {"id": sp, "label": label_of(sp), "sex": sex_of(sp), "kin": kin, "cluster": None}

        # clusters for quick UI grouping (optional)
        for k, v in list(nodes.items()):
            kin = v.get("kin", "")
            if "-in-law" in kin or "نسَب" in kin or kin in ["spouse", "زوج/زوجة"]:
                v["cluster"] = "inlaws"
            elif any(w in kin for w in ["grandfather", "grandmother", "grandparent", "الجد", "الجدة"]):
                v["cluster"] = "ancestors"
            elif any(w in kin for w in ["grandson", "granddaughter", "grandchild", "الحفيد", "الحفيدة"]):
                v["cluster"] = "descendants"

        payload = {
            "root": eid,
            "lang": LANG,
            "depth": DEPTH,
            "nodes": list(nodes.values()),
            "edges": [{"source": s, "target": t, "type": typ} for (s, t, typ) in edges],
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z"
        }
        out_rows.append((eid, json.dumps(payload, ensure_ascii=False)))

    # ---- Write CSV output ------------------------------------------------------
    print(f"\nCreating DataFrame with {len(out_rows)} ego networks...")
    schema = T.StructType([
        T.StructField("entity_person_id", T.StringType(), False),
        T.StructField("ego_json", T.StringType(), False),
    ])
    df = spark.createDataFrame(out_rows, schema).withColumn("generated_at", F.current_timestamp())

    out_path = f"{OUTPUT_DIR.rstrip('/')}/citizens_ego3_cache"
    dfw = df.coalesce(1) if SINGLE_FILE_OUTPUT else df
    print(f"✓ Writing ego3 cache CSV to: {out_path}")
    dfw.write.mode("overwrite").option("header", "true").csv(out_path)

    print("\n" + "=" * 80)
    print(f"✅ Created {len(out_rows)} citizen ego networks (CSV)")
    print("=" * 80)

    spark.stop()

if __name__ == "__main__":
    main()
