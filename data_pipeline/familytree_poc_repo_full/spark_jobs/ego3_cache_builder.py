from pyspark.sql import SparkSession, functions as F, types as T
import argparse, json, datetime
from collections import defaultdict, deque

def parse_args():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--person_id", type=str)
    g.add_argument("--person_ids_path", type=str)
    g.add_argument("--full", action="store_true")
    p.add_argument("--lang", type=str, default="en", choices=["en","ar"])
    p.add_argument("--depth", type=int, default=3)
    return p.parse_args()

def kin_term_en(path_steps, sex):
    U = path_steps.count("U"); D = path_steps.count("D"); S = path_steps.count("S")
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
        return base + " (in-law)"
    return "relative"

def kin_term_ar(path_steps, sex):
    U = path_steps.count("U"); D = path_steps.count("D"); S = path_steps.count("S")
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

def load_person_ids(spark, args):
    if args.person_id: return [args.person_id]
    if args.person_ids_path:
        return [r[0] for r in spark.read.text(args.person_ids_path).collect()]
    return [r[0] for r in spark.table("lake.silver.person_entity").select("entity_person_id").limit(10000).collect()]

def main():
    args = parse_args()
    spark = SparkSession.builder.appName("ego3_cache_builder").getOrCreate()

    pe = spark.table("lake.silver.person_entity").select("entity_person_id","full_name","sex","dob")
    pl = spark.table("lake.silver.parent_links").select("parent_entity_person_id","child_entity_person_id")
    sl = spark.table("lake.silver.spouse_links").select("husband_entity_person_id","wife_entity_person_id")

    persons = {r["entity_person_id"]: {"full_name": r["full_name"], "sex": r["sex"], "dob": str(r["dob"]) if r["dob"] else None}
               for r in pe.collect()}
    from collections import defaultdict
    pdict = defaultdict(set); cdict = defaultdict(set)
    for r in pl.collect():
        p, c = r["parent_entity_person_id"], r["child_entity_person_id"]
        if p and c:
            pdict[c].add(p); cdict[p].add(c)
    parents = dict(pdict); children = dict(cdict)
    sdict = defaultdict(set)
    for r in sl.collect():
        h, w = r["husband_entity_person_id"], r["wife_entity_person_id"]
        if h and w:
            sdict[h].add(w); sdict[w].add(h)
    spouses = dict(sdict)

    ids = load_person_ids(spark, args)

    out_rows = []
    for eid in ids:
        nodes = {}
        edges = set()
        visited_depth = {eid: 0}
        q = deque()
        q.append((eid, "", 0))

        def sex_of(x): return persons.get(x,{}).get("sex")
        def label_of(x): return persons.get(x,{}).get("full_name", x)

        nodes[eid] = {"id": eid, "label": label_of(eid), "sex": sex_of(eid), "kin": "self", "cluster": None}

        while q:
            cur, path, g = q.popleft()

            if g < args.depth:
                for par in parents.get(cur, []):
                    edges.add((cur, par, "CHILD_OF"))
                    new_g = g + 1
                    if visited_depth.get(par, 999) > new_g:
                        visited_depth[par] = new_g
                        q.append((par, path + "U", new_g))
                    kin = (kin_term_en("U", sex_of(par)) if args.lang=="en" else kin_term_ar("U", sex_of(par)))
                    nodes[par] = {"id": par, "label": label_of(par), "sex": sex_of(par), "kin": kin, "cluster": None}

            if g < args.depth:
                for chi in children.get(cur, []):
                    edges.add((chi, cur, "CHILD_OF"))
                    new_g = g + 1
                    if visited_depth.get(chi, 999) > new_g:
                        visited_depth[chi] = new_g
                        q.append((chi, path + "D", new_g))
                    kin = (kin_term_en("D", sex_of(chi)) if args.lang=="en" else kin_term_ar("D", sex_of(chi)))
                    nodes[chi] = {"id": chi, "label": label_of(chi), "sex": sex_of(chi), "kin": kin, "cluster": None}

            for sp in spouses.get(cur, []):
                edges.add((cur, sp, "SPOUSE_OF")); edges.add((sp, cur, "SPOUSE_OF"))
                new_g = g
                if visited_depth.get(sp, 999) >= new_g:
                    visited_depth[sp] = new_g
                    q.append((sp, path + "S", new_g))
                kin = "spouse" if args.lang=="en" else "زوج/زوجة"
                nodes[sp] = {"id": sp, "label": label_of(sp), "sex": sex_of(sp), "kin": kin, "cluster": None}

        for k, v in list(nodes.items()):
            kin = v.get("kin","")
            if "(in-law)" in kin or kin == "spouse" or kin == "زوج/زوجة":
                v["cluster"] = v["cluster"] or "inlaws"
            elif any(w in kin for w in ["grandfather","grandmother","grandparent","الجد","الجدة"]):
                v["cluster"] = v["cluster"] or "ancestors"
            elif any(w in kin for w in ["grandson","granddaughter","grandchild","الحفيد","الحفيدة"]):
                v["cluster"] = v["cluster"] or "descendants"

        payload = {
            "root": eid,
            "nodes": list(nodes.values()),
            "edges": [{"source": s, "target": t, "type": typ} for (s,t,typ) in edges],
            "generated_at": datetime.datetime.utcnow().isoformat()+"Z"
        }
        out_rows.append( (eid, json.dumps(payload)) )

    schema = T.StructType([
        T.StructField("entity_person_id", T.StringType(), False),
        T.StructField("ego_json", T.StringType(), False),
    ])
    spark = SparkSession.getActiveSession()
    df = spark.createDataFrame(out_rows, schema).withColumn("generated_at", F.current_timestamp())

    spark.sql("""
        CREATE TABLE IF NOT EXISTS lake.gold.ego3_cache (
          entity_person_id STRING,
          ego_json STRING,
          generated_at TIMESTAMP
        ) USING ICEBERG
    """)
    df.createOrReplaceTempView("updates")
    spark.sql("""
        MERGE INTO lake.gold.ego3_cache AS t
        USING updates AS s
        ON t.entity_person_id = s.entity_person_id
        WHEN MATCHED THEN UPDATE SET ego_json = s.ego_json, generated_at = s.generated_at
        WHEN NOT MATCHED THEN INSERT (entity_person_id, ego_json, generated_at) VALUES (s.entity_person_id, s.ego_json, s.generated_at)
    """)

if __name__ == "__main__":
    main()
