# frontend/streamlit_app.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import requests
import streamlit as st
from streamlit.components.v1 import declare_component


# ---------- Configuration ----------
st.set_page_config(page_title="Family Graph", layout="wide")

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8080")

# If you want to run the component in dev mode (vite dev server), set:
#   export STREAMLIT_SIGMA_URL="http://localhost:5173"
SIGMA_DEV_URL = os.getenv("STREAMLIT_SIGMA_URL")

if SIGMA_DEV_URL:
    sigma = declare_component("streamlit_sigma", url=SIGMA_DEV_URL)
else:
    COMP_DIR = Path(__file__).parent / "components" / "streamlit-sigma" / "build"
    sigma = declare_component("streamlit_sigma", path=str(COMP_DIR))


# ---------- Session State ----------
def _init_state():
    if "center_uid" not in st.session_state:
        st.session_state.center_uid = "U1"  # default UID for mock mode
    if "cursors" not in st.session_state:
        st.session_state.cursors = {"parents": None, "children": None, "spouses": None, "siblings": None}
    if "as_of" not in st.session_state:
        st.session_state.as_of = None
    if "page_size" not in st.session_state:
        st.session_state.page_size = 20
    if "last_payload" not in st.session_state:
        st.session_state.last_payload = None


_init_state()


# ---------- Backend API ----------
def fetch_neighborhood(
    uid: str,
    cursors: Dict[str, str | None],
    as_of: Any | None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Call FastAPI backend to get neighborhood data."""
    params: Dict[str, Any] = {"limit": limit}
    if as_of:
        params["asOfDate"] = str(as_of)
    # add per-group cursors if present
    for g in ("parents", "children", "spouses", "siblings"):
        cur = cursors.get(g)
        if cur:
            params[f"cursor_{g}"] = cur

    url = f"{API_BASE}/person/{uid}/neighborhood"
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


# ---------- Graph payload builder ----------
def build_graph_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the minimal graph payload expected by the Sigma component:
    {
      "nodes": [{"id": "...","label":"...","type":"CENTER|PARENTS|CHILDREN|SPOUSES|SIBLINGS|CLUSTER|HINT_*", ...}],
      "edges": [{"id":"...", "source":"...", "target":"...", "type":"PARENT_OF|SPOUSE_OF|SIBLING_OF|HINT"}]
    }
    """
    nodes: list[Dict[str, Any]] = []
    edges: list[Dict[str, Any]] = []

    c = data["center"]
    center_id = c["uid"]
    nodes.append({"id": center_id, "label": c.get("full_name_en") or center_id, "type": "CENTER"})

    def add_group(name: str, etype: str):
        group = data.get(name, {"items": [], "total": 0, "hasMore": False})
        items = group.get("items", []) or []
        for p in items:
            pid = p["uid"]
            nodes.append(
                {
                    "id": pid,
                    "label": p.get("full_name_en") or pid,
                    "type": name.upper(),
                    "counts": p.get("counts", {}),
                    "role": name,
                }
            )
            if name in ("children", "spouses"):
                edges.append({"id": f"{center_id}-{etype}-{pid}", "source": center_id, "target": pid, "type": etype})
            else:  # parents, siblings
                edges.append({"id": f"{pid}-{etype}-{center_id}", "source": pid, "target": center_id, "type": etype})

        if group.get("hasMore"):
            cid = f"cluster:{name}:{center_id}"
            nodes.append({"id": cid, "label": f"+ more {name}", "type": "CLUSTER", "clusterOf": name})
            edges.append({"id": f"{center_id}-{etype}-{cid}", "source": center_id, "target": cid, "type": etype})

    add_group("parents", "PARENT_OF")
    add_group("children", "PARENT_OF")
    add_group("spouses", "SPOUSE_OF")
    add_group("siblings", "SIBLING_OF")

    # Hint bubbles on siblings & spouses
    def add_hint(person: Dict[str, Any]):
        uid = person["uid"]
        cnt = person.get("counts", {}) or {}
        if cnt.get("children", 0) > 0:
            nid = f"hint:children:{uid}"
            nodes.append({"id": nid, "label": f"{cnt['children']} kid(s)", "type": "HINT_CHILDREN", "of": uid})
            edges.append({"id": f"{uid}-HINT-{nid}", "source": uid, "target": nid, "type": "HINT"})
        if cnt.get("spouses", 0) > 0:
            nid = f"hint:spouses:{uid}"
            nodes.append({"id": nid, "label": f"{cnt['spouses']} spouse(s)", "type": "HINT_SPOUSES", "of": uid})
            edges.append({"id": f"{uid}-HINT-{nid}", "source": uid, "target": nid, "type": "HINT"})

    for sib in (data.get("siblings", {}).get("items", []) or []):
        add_hint(sib)
    for sp in (data.get("spouses", {}).get("items", []) or []):
        add_hint(sp)

    return {"nodes": nodes, "edges": edges}


# ---------- UI Layout ----------
col_left, col_right = st.columns([3, 1], gap="large")

with col_right:
    st.subheader("Controls")
    st.session_state.center_uid = st.text_input("SPM_PERSON_NO", value=st.session_state.center_uid)
    st.session_state.as_of = st.date_input("As-of date (spouses)", value=st.session_state.as_of)
    st.session_state.page_size = st.slider("Page size per group", 5, 50, st.session_state.page_size)
    if st.button("Reset paging"):
        st.session_state.cursors = {"parents": None, "children": None, "spouses": None, "siblings": None}

with col_left:
    st.title("Family Tree and Relationship Mapping")

# ---------- Fetch & Build ----------
try:
    data = fetch_neighborhood(
        st.session_state.center_uid,
        st.session_state.cursors,
        st.session_state.as_of,
        limit=st.session_state.page_size,
    )
    st.session_state.last_payload = data
except Exception as e:
    st.error(f"Failed to fetch neighborhood for '{st.session_state.center_uid}': {e}")
    st.stop()

graph_payload = build_graph_payload(st.session_state.last_payload)

# ---------- Sanity Checks (visible diagnostics) ----------
with st.expander("Sanity Check (debug)", expanded=False):
    totals = {
        "Parents": st.session_state.last_payload.get("parents", {}).get("total", 0),
        "Children": st.session_state.last_payload.get("children", {}).get("total", 0),
        "Spouses": st.session_state.last_payload.get("spouses", {}).get("total", 0),
        "Siblings": st.session_state.last_payload.get("siblings", {}).get("total", 0),
    }
    st.write("**Group totals from backend**", totals)
    st.write(
        "**Graph payload sizes**",
        {"nodes": len(graph_payload["nodes"]), "edges": len(graph_payload["edges"])},
    )
    st.caption(
        "If totals are >0 but you still see a blank canvas, ensure your component assigns x/y positions "
        "(use the ring layout or ForceAtlas2 as discussed)."
    )

# ---------- Render the component ----------
event = sigma(graph=graph_payload, height=820, key="sigma-main")

# ---------- Handle component events ----------
if event:
    etype = event.get("type")
    if etype == "center":
        st.session_state.center_uid = event["uid"]
        # Reset cursors when changing center
        st.session_state.cursors = {"parents": None, "children": None, "spouses": None, "siblings": None}
        st.rerun()

    elif etype == "expand_cluster":
        group = event.get("group")
        # Use the nextCursor returned from the last payload
        next_cur = st.session_state.last_payload.get(group, {}).get("nextCursor")
        if next_cur:
            st.session_state.cursors[group] = next_cur
        else:
            st.toast(f"No more results for {group}", icon="❕")
        st.rerun()