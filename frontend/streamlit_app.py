
import streamlit as st, requests

st.set_page_config(page_title='Family Tree Viewer', layout='wide', page_icon='🌳')
st.markdown('''
<style>
:root { --gold: #DAA520; --gold-soft:#f7e8b1; --ink:#1f2937; }
html, body, [class*="css"]  { background-color: #ffffff !important; color: var(--ink); }
h1, h2, h3 { color: var(--gold); letter-spacing: .3px; }
div.stButton>button { background-color: var(--gold); color: white; border: 0; border-radius: 8px; }
</style>
''', unsafe_allow_html=True)

st.title('Family Tree — PoC')

api_url = 'http://localhost:8000'
lang = ['en','ar']

t1, t2, t3 = st.tabs(['Tree','LCA','Inference'])

with t1:
    c1, c2 = st.columns([1,2])
    with c1:
        person_id = st.text_input('Person ID', 'E1')
        if st.button('Load Tree', use_container_width=True):
            try:
                r = requests.get(f'{api_url}/api/v1/persons/{person_id}/tree', params={'depth':3,'lang':lang}, timeout=10)
                st.session_state['tree'] = r.json()
                st.success('Loaded')
            except Exception as e:
                st.error(e)

    with c2:
        if 'tree' in st.session_state:
            src = f"{api_url}/static/sigma.html?eid={st.session_state['tree']['root']}&api={api_url}"
            st.components.v1.iframe(src, height=650, scrolling=True)
        else:
            st.info('Load a tree to visualize.')

with t2:
    a = st.text_input('Person A', 'E1')
    b = st.text_input('Person B', 'E7')
    if st.button('Compute LCA'):
        try:
            st.json(requests.get(f'{api_url}/api/v1/lca', params={'personA':a,'personB':b}, timeout=10).json())
        except Exception as e:
            st.error(e)

with t3:
    pid = st.text_input('Person ID for inference', 'E1')
    if st.button('Run Inference', use_container_width=True):
        try:
            st.json(requests.post(f'{api_url}/api/v1/infer', json={'person_id':pid}, timeout=10).json())
        except Exception as e:
            st.error(e)
