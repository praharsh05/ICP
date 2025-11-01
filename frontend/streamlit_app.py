
import streamlit as st
import requests

st.set_page_config(page_title='Family Tree Viewer',
                   layout='wide', page_icon='🌳')
st.markdown('''
<style>
:root { --gold: #DAA520; --gold-soft:#f7e8b1; --ink:#1f2937; }
html, body, [class*="css"]  { background-color: #ffffff !important; color: var(--ink); }
h1, h2, h3 { color: var(--gold); letter-spacing: .3px; }
div.stButton>button { background-color: var(--gold); color: white; border: 0; border-radius: 8px; }
</style>
''', unsafe_allow_html=True)

st.title('Family Tree — PoC')

api_url = 'http://localhost:6694'
lang = 'en'

t1, t2 = st.tabs(['Tree', 'LCA'])

# --- ADD: compact “card” CSS for the accordion ---
st.markdown("""
<style>
.ac-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.ac-card {
  display:flex; align-items:center; gap:10px; padding:8px 10px; border:1px solid #eee;
  border-radius:10px; background:#fff;
  box-shadow: 0 4px 12px rgba(0,0,0,.05);
  min-height: 46px;
}
.ac-card.self   { border-color: var(--gold); box-shadow: 0 0 0 2px rgba(218,165,32,.18), 0 6px 18px rgba(0,0,0,.06); background: #fffaf0; }
.ac-avatar { width:28px; height:28px; border-radius:6px; overflow:hidden; flex:0 0 28px; background:#f2e7d7; display:grid; place-items:center; }
.ac-avatar img { width:100%; height:100%; object-fit:cover; }
.ac-info { line-height:1.2; min-width:0; }
.ac-kin  { font-size:11px; color:#6b7280; margin-bottom:2px; }
.ac-name { font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
</style>
""", unsafe_allow_html=True)

# --- ADD: helpers to group + render cards from API payload ---
def _avatar(api_url: str, sex: None):
    if str(sex or "").upper() == "F":
        return f"{api_url}/static/img/female_icon.jpg"
    return f"{api_url}/static/img/male_icon.jpg"

def _group_nodes(tree: dict):
    nodes = tree.get("nodes", [])
    # normalize fields
    for n in nodes:
        n.setdefault("label", n.get("full_name") or n.get("name") or n.get("id"))
        n.setdefault("kin", "")
        n["kin_low"] = str(n["kin"]).lower()

    # buckets
    self_nodes   = [n for n in nodes if n["kin_low"] == "self"]
    parents      = [n for n in nodes if n["kin_low"] in {"father","mother","parent"}]
    children     = [n for n in nodes if n["kin_low"] in {"son","daughter","child"}]
    spouses      = [n for n in nodes if n["kin_low"] in {"husband","wife","spouse"}]
    siblings     = [n for n in nodes if n["kin_low"] in {"brother","sister","sibling"}]
    grandparents = [n for n in nodes if "grandfather" in n["kin_low"] or "grandmother" in n["kin_low"] or "grandparent" in n["kin_low"]]
    grandkids    = [n for n in nodes if n["kin_low"] in {"grandson","granddaughter","grandchild"}]
    inlaws       = [n for n in nodes if "in-law" in n["kin_low"] or "in law" in n["kin_low"]]

    return {
        "Self": self_nodes,
        "Parents": parents,
        "Children": children,
        "Spouses": spouses,
        "Siblings": siblings,
        "Grandparents": grandparents,
        "Grandchildren": grandkids,
        "In-laws": inlaws,
    }

def _card_html(person: dict, api_url: str):
    kin = person.get("kin") or ""
    name = person.get("label") or person.get("id")
    img = _avatar(api_url, person.get("sex"))
    self_class = " self" if (str(kin).lower() == "self") else ""
    return f"""
    <div class="ac-card{self_class}">
      <div class="ac-avatar"><img src="{img}" alt=""></div>
      <div class="ac-info">
        <div class="ac-kin">{kin}</div>
        <div class="ac-name" title="{name}">{name}</div>
      </div>
    </div>
    """

with t1:
    c1, c2 = st.columns([1, 2])
    with c1:
        person_id = st.text_input('Person ID', 'P1968702237')
        if st.button('Load Tree', use_container_width=True):
            try:
                r = requests.get(f'{api_url}/api/v1/persons/{person_id}/tree',
                                 params={'depth': 3, 'lang': lang}, timeout=10)
                st.session_state['tree'] = r.json()
                st.success('Loaded')
            except Exception as e:
                st.error(e)

        # accordion on the LEFT
        if 'tree' in st.session_state:
            st.markdown("### Family Details")
            buckets = _group_nodes(st.session_state['tree'])

            order = [
                "Self", "Parents", "Children",
                "Spouses", "Siblings", "Grandparents",
                "Grandchildren", "In-laws"
            ]

            for title in order:
                people = buckets.get(title, [])
                if not people:
                    continue
                with st.expander(f"{title} ({len(people)})", expanded=(title in ["Self", "Parents", "Children"])):
                    st.markdown('<div class="ac-grid">', unsafe_allow_html=True)
                    for p in people:
                        st.markdown(_card_html(p, api_url), unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        if 'tree' in st.session_state:
            src = f"{api_url}/static/sigma_pretty_tree.html?eid={st.session_state['tree']['root']}&api={api_url}"
            st.components.v1.iframe(src, height=650, scrolling=True)
        else:
            st.info('Load a tree to visualize.')

with t2:
    a = st.text_input('Person A', 'E1')
    b = st.text_input('Person B', 'E7')
    if st.button('Compute LCA'):
        try:
            r = requests.get(
                f'{api_url}/api/v1/lca',
                params={'p1': a, 'p2': b},  # <-- FIXED PARAM NAMES
                timeout=10
            )
            r.raise_for_status()
            st.json(r.json())
        except Exception as e:
            st.error(e)
