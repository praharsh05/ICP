"""
Residents Ego Cache Builder - Pre-compute 2-hop sponsorship networks
FULLY IMPLEMENTED VERSION

Note: Resident networks are different from citizen networks:
- Based on SPONSORSHIP relationships (not biological family)
- Typically 2 hops: Sponsor -> Sponsored Residents -> Their Family Members
- No parent-child or spouse relationships (those are in citizen data)
"""
from pyspark.sql import SparkSession, functions as F, types as T
import argparse, json, datetime
from collections import defaultdict, deque

def parse_args():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--person_id", type=str, help="Single entity_person_id to process")
    g.add_argument("--person_ids_path", type=str, help="File with list of entity_person_ids")
    g.add_argument("--full", action="store_true", help="Process all residents (use with caution)")
    p.add_argument("--lang", type=str, default="en", choices=["en","ar"], help="Language for labels")
    p.add_argument("--depth", type=int, default=2, help="Number of sponsorship hops (typically 1-2)")
    p.add_argument("--batch_size", type=int, default=1000, help="Batch size for processing")
    return p.parse_args()

def relationship_label_en(rel_code):
    """Map relationship codes to English labels"""
    mapping = {
        '2': 'wife',
        '3': 'son', 
        '4': 'daughter',
        '5': 'brother',
        '6': 'sister',
        '7': 'father',
        '8': 'mother',
        '9': 'other_family_member'
    }
    return mapping.get(str(rel_code), 'family_member')

def relationship_label_ar(rel_code):
    """Map relationship codes to Arabic labels"""
    mapping = {
        '2': 'زوجة',
        '3': 'ابن',
        '4': 'ابنة',
        '5': 'أخ',
        '6': 'أخت',
        '7': 'أب',
        '8': 'أم',
        '9': 'فرد من العائلة'
    }
    return mapping.get(str(rel_code), 'فرد من العائلة')

def load_person_ids(spark, args):
    """Load list of person IDs to process"""
    if args.person_id: 
        return [args.person_id]
    if args.person_ids_path:
        return [r[0] for r in spark.read.text(args.person_ids_path).collect()]
    # Full mode - process all residents (use with caution!)
    return [r[0] for r in spark.table("lake.silver.residents_person_entity").select("entity_person_id").limit(10000).collect()]

def main():
    args = parse_args()
    spark = SparkSession.builder \
        .appName("residents_ego3_cache_builder") \
        .getOrCreate()
    
    print("=" * 80)
    print("RESIDENTS EGO CACHE BUILDER (SPONSORSHIP NETWORKS)")
    print("=" * 80)
    
    # Load data from silver layer
    print("\nLoading residents data from silver layer...")
    
    # Resident persons with their attributes
    pe = spark.table("lake.silver.residents_person_entity").select(
        "entity_person_id",
        F.coalesce(F.col("full_name_en"), F.col("full_name")).alias("full_name"),
        "sex",
        "sponsor_number",
        "relation_to_sponsor",
        "relationship_code"
    )
    
    # Sponsorship links (who sponsors whom)
    sl = spark.table("lake.silver.residents_sponsorship_links").select(
        "sponsor_entity_person_id",
        "sponsored_entity_person_id",
        "relation_to_sponsor",
        "relationship_code",
        "sponsor_type"
    )
    
    # Family groups (residents grouped by sponsor)
    fg = spark.table("lake.silver.residents_family_groups").select(
        "entity_person_id",
        "sponsor_id",
        "family_group_id"
    )
    
    print(f"✓ Loaded {pe.count():,} residents")
    print(f"✓ Loaded {sl.count():,} sponsorship links")
    print(f"✓ Loaded {fg.count():,} family group memberships")
    
    # Collect into memory for BFS traversal
    print("\nCollecting data into memory for BFS traversal...")
    persons = {r["entity_person_id"]: {
        "full_name": r["full_name"],
        "sex": r["sex"],
        "sponsor_number": r["sponsor_number"],
        "relation_to_sponsor": r["relation_to_sponsor"],
        "relationship_code": r["relationship_code"]
    } for r in pe.collect()}
    
    # Build sponsorship dictionaries
    # sponsor -> list of sponsored residents
    sponsored_by = defaultdict(set)
    # resident -> their sponsor
    sponsor_of = {}
    
    for r in sl.collect():
        sponsor_id = r["sponsor_entity_person_id"]
        sponsored_id = r["sponsored_entity_person_id"]
        rel = r["relation_to_sponsor"]
        rel_code = r["relationship_code"]
        sponsor_type = r["sponsor_type"]
        
        if sponsor_id and sponsored_id:
            sponsored_by[sponsor_id].add((sponsored_id, rel, rel_code, sponsor_type))
            sponsor_of[sponsored_id] = (sponsor_id, rel, rel_code, sponsor_type)
    
    # Build family group memberships
    # family_group_id -> list of members
    family_groups = defaultdict(set)
    # person -> their family group
    person_to_group = {}
    
    for r in fg.collect():
        person_id = r["entity_person_id"]
        group_id = r["family_group_id"]
        
        if person_id and group_id:
            family_groups[group_id].add(person_id)
            person_to_group[person_id] = group_id
    
    # Load person IDs to process
    ids = load_person_ids(spark, args)
    print(f"\nProcessing {len(ids)} sponsorship network(s)...")
    
    # Build ego networks
    out_rows = []
    for idx, eid in enumerate(ids):
        if idx % 100 == 0 and idx > 0:
            print(f"  Processed {idx}/{len(ids)} networks...")
        
        # Skip if person doesn't exist
        if eid not in persons:
            print(f"  ⚠️  Skipping {eid} - not in residents data")
            continue
        
        # BFS traversal for sponsorship network
        nodes = {}
        edges = set()
        visited = {eid}
        q = deque()
        q.append((eid, 0, None))  # (person_id, depth, role)
        
        def label_of(x):
            return persons.get(x, {}).get("full_name", x)
        
        def sex_of(x):
            return persons.get(x, {}).get("sex")
        
        def rel_label(rel_code, lang="en"):
            if lang == "en":
                return relationship_label_en(rel_code)
            return relationship_label_ar(rel_code)
        
        # Add ego node
        ego_data = persons.get(eid, {})
        nodes[eid] = {
            "id": eid,
            "label": label_of(eid),
            "sex": sex_of(eid),
            "role": "self",
            "relation": None,
            "cluster": "ego"
        }
        
        # BFS traversal
        while q:
            cur, depth, role = q.popleft()
            
            # Stop at max depth
            if depth >= args.depth:
                continue
            
            # Traverse UP to sponsor (if has one)
            if cur in sponsor_of:
                sponsor_id, rel, rel_code, sponsor_type = sponsor_of[cur]
                
                if sponsor_id not in visited:
                    visited.add(sponsor_id)
                    edges.add((cur, sponsor_id, "SPONSORED_BY"))
                    
                    # Determine role
                    if sponsor_type == "citizen":
                        sponsor_role = "citizen_sponsor"
                        cluster = "sponsors"
                    else:
                        sponsor_role = "resident_sponsor"
                        cluster = "sponsors"
                    
                    nodes[sponsor_id] = {
                        "id": sponsor_id,
                        "label": label_of(sponsor_id),
                        "sex": sex_of(sponsor_id),
                        "role": sponsor_role,
                        "relation": rel,
                        "cluster": cluster
                    }
                    
                    q.append((sponsor_id, depth + 1, sponsor_role))
            
            # Traverse DOWN to sponsored residents (if any)
            if cur in sponsored_by:
                for sponsored_id, rel, rel_code, sponsor_type in sponsored_by[cur]:
                    if sponsored_id not in visited:
                        visited.add(sponsored_id)
                        edges.add((sponsored_id, cur, "SPONSORED_BY"))
                        
                        rel_text = rel_label(rel_code, args.lang)
                        
                        nodes[sponsored_id] = {
                            "id": sponsored_id,
                            "label": label_of(sponsored_id),
                            "sex": sex_of(sponsored_id),
                            "role": "sponsored_resident",
                            "relation": rel_text,
                            "cluster": "sponsored"
                        }
                        
                        q.append((sponsored_id, depth + 1, "sponsored_resident"))
            
            # Add family group members (same sponsor)
            if cur in person_to_group:
                group_id = person_to_group[cur]
                for member_id in family_groups.get(group_id, set()):
                    if member_id not in visited and member_id != cur:
                        visited.add(member_id)
                        
                        # Don't add edge, just note they're in same family group
                        # (could add SAME_FAMILY_GROUP edge if desired)
                        
                        member_data = persons.get(member_id, {})
                        rel_code = member_data.get("relationship_code")
                        rel_text = rel_label(rel_code, args.lang)
                        
                        nodes[member_id] = {
                            "id": member_id,
                            "label": label_of(member_id),
                            "sex": sex_of(member_id),
                            "role": "family_member",
                            "relation": rel_text,
                            "cluster": "family"
                        }
                        
                        # Optionally add family group edge
                        edges.add((cur, member_id, "SAME_FAMILY_GROUP"))
        
        # Create JSON payload
        payload = {
            "root": eid,
            "lang": args.lang,
            "depth": args.depth,
            "network_type": "sponsorship",
            "nodes": list(nodes.values()),
            "edges": [{"source": s, "target": t, "type": typ} for (s, t, typ) in edges],
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z"
        }
        
        out_rows.append((eid, json.dumps(payload, ensure_ascii=False)))
    
    # Create DataFrame
    print(f"\nCreating DataFrame with {len(out_rows)} sponsorship networks...")
    schema = T.StructType([
        T.StructField("entity_person_id", T.StringType(), False),
        T.StructField("ego_json", T.StringType(), False),
    ])
    df = spark.createDataFrame(out_rows, schema).withColumn("generated_at", F.current_timestamp())
    
    # Create table if not exists
    spark.sql("""
        CREATE TABLE IF NOT EXISTS lake.gold.residents_ego3_cache (
          entity_person_id STRING,
          ego_json STRING,
          generated_at TIMESTAMP
        ) USING ICEBERG
        PARTITIONED BY (days(generated_at))
    """)
    
    # Merge into target table (upsert)
    print(f"\nMerging into lake.gold.residents_ego3_cache...")
    df.createOrReplaceTempView("updates")
    spark.sql("""
        MERGE INTO lake.gold.residents_ego3_cache AS t
        USING updates AS s
        ON t.entity_person_id = s.entity_person_id
        WHEN MATCHED THEN 
            UPDATE SET ego_json = s.ego_json, generated_at = s.generated_at
        WHEN NOT MATCHED THEN 
            INSERT (entity_person_id, ego_json, generated_at) 
            VALUES (s.entity_person_id, s.ego_json, s.generated_at)
    """)
    
    print("\n" + "=" * 80)
    print(f"✅ Created {len(out_rows)} resident sponsorship networks")
    print("=" * 80)
    
    spark.stop()

if __name__ == "__main__":
    main()
