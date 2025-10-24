import os, json, time, datetime
from pyspark.sql import SparkSession, functions as F, types as T
from dotenv import load_dotenv



# ====== NEW: light helper libs for local ego build ======
try:
    import pandas as pd
except ImportError:
    pd = None
try:
    import networkx as nx
except ImportError:
    nx = None

# ---- Config ----
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
WAREHOUSE = os.path.join(BASE, "warehouse")
EXPORTS = os.path.join(BASE, "neo4j_exports")
EGO_OUT = os.path.join(BASE, "ego3_cache_json")
os.makedirs(EXPORTS, exist_ok=True)
os.makedirs(EGO_OUT, exist_ok=True)

ICEBERG_JAR = "/Users/praharshdubey/jars/iceberg-spark-runtime-4.0_2.13-1.10.0.jar"

# ENV for Neo4j LOAD CSV (not used by Spark; just here for reference)
load_dotenv(os.path.join(BASE, ".env"))

spark = (
    SparkSession.builder
    .appName("family-local-etl")
    .config("spark.jars", ICEBERG_JAR)
    .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.local.type", "hadoop")
    .config("spark.sql.catalog.local.warehouse", f"file://{WAREHOUSE}")
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# ---- Load CSVs ----
def csv(path):
    return (spark.read
            .option("header", True)
            .option("inferSchema", True)
            .csv(path))

person = csv(os.path.join(DATA, "PERSON_MASTER.csv"))
detail = csv(os.path.join(DATA, "CITI_RECORD_DETAIL.csv"))
master = csv(os.path.join(DATA, "CITI_RECORD_MASTER.csv"))

# Optional relationships lookup (code -> name)
relmap = None
relpath = os.path.join(DATA, "RELATIONSHIPS.csv")
if os.path.exists(relpath):
    relmap = csv(relpath).select(
        F.col("code").cast("int").alias("rel1_code"),
        F.col("description_eng").alias("rel_name")
    )

# ---- Canonicalize minimal columns we care about ----
person = (person
    .withColumn("spm_person_no", F.col("spm_person_no").cast("string"))
    .withColumn("sex", F.upper(F.coalesce(F.col("sex"), F.col("Sex"), F.lit(""))))
    .withColumn("full_name", F.col("full_name").cast("string"))
    .withColumn("national_id", F.col("national_id").cast("string"))
    .withColumn("passport", F.col("passport").cast("string"))
    .dropDuplicates(["spm_person_no"])
)

detail = (detail
    .withColumn("spm_person_no", F.col("spm_person_no").cast("string"))
    .withColumn("spm_person_no_father", F.col("spm_person_no_father").cast("string"))
    .withColumn("spm_person_no_mother", F.col("spm_person_no_mother").cast("string"))
    .withColumn("crm_seq", F.col("crm_seq").cast("string"))
    .withColumn("rel1_code", F.col("rel1_code").cast("int"))
)

master = (master
    .withColumn("crm_seq", F.col("crm_seq").cast("string"))
    .withColumn("spm_person_no", F.col("spm_person_no").cast("string"))
)

if relmap is not None:
    detail = detail.join(relmap, on="rel1_code", how="left")

# ---- GOLD: identity view of people ----
people_gold = person.select("spm_person_no", "full_name", "sex", "national_id", "passport")

# ---- GOLD: parent-child edges (biological graph only) ----
pc_edges = (
    detail
      .select(
          F.col("spm_person_no").alias("child"),
          F.col("spm_person_no_father").alias("father"),
          F.col("spm_person_no_mother").alias("mother"))
)

father_edges = (pc_edges
    .filter(F.col("father").isNotNull())
    .select(F.col("father").alias("src"), F.col("child").alias("dst"))
    .withColumn("type", F.lit("PARENT_OF"))
    .withColumn("parent_sex", F.lit("M"))
)
mother_edges = (pc_edges
    .filter(F.col("mother").isNotNull())
    .select(F.col("mother").alias("src"), F.col("child").alias("dst"))
    .withColumn("type", F.lit("PARENT_OF"))
    .withColumn("parent_sex", F.lit("F"))
)
parent_edges = father_edges.unionByName(mother_edges)

# ---- GOLD: spouse edges (polygyny allowed, no end-date data) ----
wives = detail.filter(F.col("rel1_code")==2).select("crm_seq", F.col("spm_person_no").alias("wife"))
husbands = detail.filter(F.col("rel1_code")==1).select("crm_seq", F.col("spm_person_no").alias("husband"))
spouse_edges = (husbands.join(wives, on="crm_seq", how="inner")
    .select(F.col("husband").alias("a"), F.col("wife").alias("b"))
    .dropDuplicates()
    .select(F.least("a","b").alias("src"), F.greatest("a","b").alias("dst"))
    .dropDuplicates()
    .withColumn("type", F.lit("SPOUSE_OF"))
)

# ---- GOLD: family membership edges (optional)
fam_edges = (detail
    .select(F.col("crm_seq"), F.col("spm_person_no").alias("person"))
    .dropDuplicates()
)

# ---- Write GOLD tables (Iceberg) ----
spark.sql("CREATE NAMESPACE IF NOT EXISTS local.default")

(people_gold
 .writeTo("local.default.people_gold")
 .using("iceberg")
 .tableProperty("format-version", "2")
 .createOrReplace())

(parent_edges
 .writeTo("local.default.parent_edges")
 .using("iceberg")
 .tableProperty("format-version", "2")
 .createOrReplace())

(spouse_edges
 .writeTo("local.default.spouse_edges")
 .using("iceberg")
 .tableProperty("format-version", "2")
 .createOrReplace())

(fam_edges
 .writeTo("local.default.family_membership")
 .using("iceberg")
 .tableProperty("format-version", "2")
 .createOrReplace())

# ---- Export CSVs for Neo4j LOAD CSV (nodes & relationships) ----
nodes_for_neo = (people_gold
    .select(
        F.col("spm_person_no").alias("spm_person_no"),
        F.col("full_name"),
        F.when(F.col("sex").isin("M","F"), F.col("sex")).otherwise(F.lit("")).alias("sex"),
        F.col("national_id"),
        F.col("passport")
    )
    .dropDuplicates(["spm_person_no"])
)
rels_parent_for_neo = (parent_edges
    .select(F.col("src").alias("parent_id"), F.col("dst").alias("child_id"), F.col("parent_sex"))
    .dropDuplicates()
)
rels_spouse_for_neo = (spouse_edges
    .select(F.col("src").alias("p1"), F.col("dst").alias("p2"))
    .dropDuplicates()
)

nodes_for_neo.coalesce(1).write.mode("overwrite").option("header", True).csv(os.path.join(EXPORTS, "nodes"))
rels_parent_for_neo.coalesce(1).write.mode("overwrite").option("header", True).csv(os.path.join(EXPORTS, "rels_parent"))
rels_spouse_for_neo.coalesce(1).write.mode("overwrite").option("header", True).csv(os.path.join(EXPORTS, "rels_spouse"))

print("\nDone (base tables). Iceberg:", WAREHOUSE)
print("Neo4j CSVs:", EXPORTS)

# ============================================================
# NEW: EGO 3-GENERATION CACHE (JSON) -> Iceberg + files
# ============================================================
if pd is None or nx is None:
    print("\n[ego3_cache] Skipping: please install pandas and networkx:\n  pip install pandas networkx\n")
else:
    # Collect small working sets into pandas
    pdf_people = people_gold.toPandas()
    pdf_parent = parent_edges.select("src","dst","type").toPandas()
    pdf_spouse = spouse_edges.select("src","dst","type").toPandas()

    # Build person index for fast lookups
    name_by_id = {r["spm_person_no"]: (r["full_name"] if pd.notna(r["full_name"]) else r["spm_person_no"]) for _, r in pdf_people.iterrows()}
    sex_by_id  = {r["spm_person_no"]: (r["sex"] if pd.notna(r["sex"]) else "") for _, r in pdf_people.iterrows()}

    # Build directed bio graph (parent->child) and undirected spouse graph
    G = nx.DiGraph()
    for pid in name_by_id.keys():
        G.add_node(pid)
    for _, r in pdf_parent.iterrows():
        G.add_edge(r["src"], r["dst"], type="PARENT_OF")
    S = nx.Graph()
    for pid in name_by_id.keys():
        S.add_node(pid)
    for _, r in pdf_spouse.iterrows():
        S.add_edge(r["src"], r["dst"], type="SPOUSE_OF")

    # Utility sets for kin groups around ego
    def parents_of(x):
        return {u for u, v, d in G.in_edges(x, data=True) if d.get("type")=="PARENT_OF"}
    def children_of(x):
        return {v for u, v, d in G.out_edges(x, data=True) if d.get("type")=="PARENT_OF"}
    def spouses_of(x):
        return set(S.neighbors(x))
    def grandparents_of(x):
        gs = set()
        for p in parents_of(x):
            gs |= parents_of(p)
        return gs
    def grandkids_of(x):
        gk = set()
        for c in children_of(x):
            gk |= children_of(c)
        return gk
    def siblings_of(x):
        sib = set()
        P = parents_of(x)
        for p in P:
            sib |= children_of(p)
        sib.discard(x)
        return sib
    def spouse_parents(x):
        ins = set()
        for s in spouses_of(x):
            ins |= parents_of(s)
        return ins

    # Build one ego JSON
    CL_INLAWS = "__cluster_inlaws__"
    CL_GPS    = "__cluster_grandparents__"
    CL_GCK    = "__cluster_grandchildren__"

    def label_for(pid):
        return name_by_id.get(pid, pid)

    def kin_for(pid, ego, parents, children, spouses, siblings):
        if pid == ego: return "self"
        if pid in spouses: return "spouse"
        if pid in parents:
            return "father" if sex_by_id.get(pid,"")=="M" else "mother"
        if pid in children:
            return "son" if sex_by_id.get(pid,"")=="M" else "daughter"
        if pid in siblings:
            return "brother" if sex_by_id.get(pid,"")=="M" else "sister"
        return ""

    def build_ego3(ego, lang="en"):
        # Close generations
        spouses = spouses_of(ego)
        parents = parents_of(ego)
        siblings = siblings_of(ego)
        children = children_of(ego)
        gps = grandparents_of(ego)
        gck = grandkids_of(ego)
        inlaws = spouse_parents(ego) - parents  # exclude overlap with ego parents

        # Nodes (explicit)
        explicit = set([ego]) | spouses | parents | siblings | children
        nodes = []
        for pid in sorted(explicit):
            nodes.append({
                "id": pid,
                "label": label_for(pid),
                "sex": sex_by_id.get(pid, ""),
                "kin": kin_for(pid, ego, parents, children, spouses, siblings)
            })
        # Clusters if any
        if gps:
            nodes.append({"id": CL_GPS, "label": "Grandparents", "sex":"", "kin":""})
        if gck:
            nodes.append({"id": CL_GCK, "label": "Grandchildren", "sex":"", "kin":""})
        if inlaws:
            nodes.append({"id": CL_INLAWS, "label": "In-laws", "sex":"", "kin":""})

        # Edges (explicit only) + cluster edges
        explicit_ids = {n["id"] for n in nodes if not n["id"].startswith("__cluster_")}
        edges = []
        # parent edges
        for u, v, d in G.edges(data=True):
            if d.get("type")!="PARENT_OF": continue
            if u in explicit_ids and v in explicit_ids:
                edges.append({"source": u, "target": v, "type":"CHILD_OF"})
        # spouse edges
        for u, v, d in S.edges(data=True):
            if u in explicit_ids and v in explicit_ids:
                edges.append({"source": u, "target": v, "type":"SPOUSE_OF"})
        # clusters
        if gps:
            # link cluster to parents if present, else to ego
            linked = False
            for p in parents:
                if p in explicit_ids:
                    edges.append({"source": CL_GPS, "target": p, "type":"ancestor"}); linked=True
            if not linked:
                edges.append({"source": CL_GPS, "target": ego, "type":"ancestor"})
        if inlaws:
            if spouses:
                for s in spouses:
                    if s in explicit_ids:
                        edges.append({"source": CL_INLAWS, "target": s, "type":"in-law"})
            else:
                edges.append({"source": CL_INLAWS, "target": ego, "type":"in-law"})
        if gck:
            any_child = False
            for c in children:
                if c in explicit_ids:
                    edges.append({"source": CL_GCK, "target": c, "type":"descendant"}); any_child=True
            if not any_child:
                edges.append({"source": CL_GCK, "target": ego, "type":"descendant"})

        payload = {
            "root": ego,
            "lang": lang,
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "nodes": nodes,
            "edges": edges
        }
        return payload

    # Choose which egos to build.
    # For local testing: every person in the CSVs.
    all_egos = list(name_by_id.keys())

    print(f"\n[ego3_cache] Building {len(all_egos)} ego payload(s) ...")
    rows = []
    for ego in all_egos:
        payload = build_ego3(ego, lang="en")
        # to files (pretty)
        with open(os.path.join(EGO_OUT, f"{ego}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        # to Iceberg rows
        rows.append((ego, "en", json.dumps(payload, ensure_ascii=False)))

    # Write Iceberg table
    schema = T.StructType([
        T.StructField("ego_id", T.StringType(), False),
        T.StructField("lang", T.StringType(), False),
        T.StructField("payload", T.StringType(), False),
    ])
    ego_df = spark.createDataFrame(rows, schema=schema)

    (ego_df
     .writeTo("local.default.ego3_cache")
     .using("iceberg")
     .tableProperty("format-version", "2")
     .createOrReplace())

    print(f"[ego3_cache] Wrote Iceberg table local.default.ego3_cache and {len(all_egos)} JSON file(s) to {EGO_OUT}")

print("\nAll done.")