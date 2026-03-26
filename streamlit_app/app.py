"""Graph-first Streamlit UI for SAP O2C Flow Engine."""

import html
import json
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components

API_BASE = "https://dodge-5seu.onrender.com/api"

st.set_page_config(
    page_title="Mapping | Order to Cash",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed",
)



def _inject_css() -> None:
    st.markdown(
        """
<style>
html, body, .stApp {
    margin: 0; padding: 0;
    min-height: 100vh;
    overflow-x: hidden;
    overflow-y: auto;
    background: #ffffff !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
header[data-testid="stHeader"],
footer[data-testid="stFooter"],
#MainMenu,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

.block-container {
    padding: 0 !important; max-width: 100% !important;
    background: #ffffff !important;
}
.stApp > div[data-testid="stAppViewContainer"] { min-height: 100vh; overflow: visible; }
.stApp > div[data-testid="stAppViewContainer"] > section[data-testid="stMain"] { min-height: 100vh; overflow: visible; }
section[data-testid="stMain"] > div.block-container {
    min-height: 100vh;
    overflow: visible;
    display: flex; flex-direction: column;
}

.stVerticalBlock { gap: 0 !important; }
[data-testid="column"] .stVerticalBlock { gap: 0 !important; }
[data-testid="stVerticalBlockBorderWrapper"] { gap: 0 !important; padding: 0 !important; }
div[data-testid="stMarkdown"] { margin: 0 !important; padding: 0 !important; }

.top-nav {
    display: flex; align-items: center;
    padding: 0 24px; height: 52px;
    background: #ffffff;
    border-bottom: 1px solid #eaecf0;
    flex-shrink: 0; z-index: 1000;
    box-sizing: border-box;
}
.top-nav svg { width: 20px; height: 20px; color: #111827; flex-shrink: 0; }
.top-nav .divider { color: #d1d5db; margin: 0 16px; font-weight: 300; font-size: 18px; }
.top-nav .breadcrumb { font-size: 15px; display: flex; align-items: center; gap: 6px; }
.top-nav .path { color: #9ca3af; font-weight: 400; }
.top-nav .title { color: #111827; font-weight: 600; }

section[data-testid="stMain"] > div.block-container > div[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stHorizontalBlock"],
div[data-testid="stHorizontalBlock"] {
    flex: 1 1 auto;
    min-height: 0;
    overflow: visible !important;
    align-items: flex-start !important;
    gap: 0 !important;
}
[data-testid="column"] { padding: 0 !important; }

[data-testid="column"]:nth-child(1) {
    border-right: 1px solid #eaecf0;
    background: #ffffff !important;
    position: relative;
    align-self: flex-start !important;
    min-height: calc(100vh - 52px);
    overflow: hidden;
}
[data-testid="column"]:nth-child(2) {
    background: #ffffff !important;
    position: relative;
    align-self: flex-start !important;
    max-height: calc(100vh - 52px) !important;
    height: auto !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    scrollbar-width: thin;
    scrollbar-color: #d1d5db transparent;
}
[data-testid="column"]:nth-child(2)::-webkit-scrollbar { width: 6px; }
[data-testid="column"]:nth-child(2)::-webkit-scrollbar-track { background: transparent; }
[data-testid="column"]:nth-child(2)::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
[data-testid="column"]:nth-child(2)::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
[data-testid="column"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="column"]:nth-child(2) .stVerticalBlock {
    overflow: visible !important;
    height: auto !important;
    max-height: none !important;
}

.chat-header {
    padding: 16px 24px 12px 24px;
    border-bottom: 1px solid #eaecf0;
    flex-shrink: 0;
}
.chat-header h2 { margin: 0 0 2px 0; font-size: 15px; font-weight: 600; color: #111827; }
.chat-header p { margin: 0; font-size: 12px; color: #6b7280; }

.chat-container {
    padding: 20px 24px;
    display: flex; flex-direction: column; gap: 18px;
}

.msg-row { display: flex; gap: 10px; }
.msg-row.user { justify-content: flex-end; }

.avatar {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 13px; flex-shrink: 0;
}
.avatar-ai { background: #111827; color: #ffffff; }
.avatar-user { background: #e5e7eb; color: #9ca3af; }
.avatar-user svg { width: 18px; height: 18px; fill: currentColor; }

.msg-content { max-width: 85%; }
.msg-meta { display: flex; align-items: baseline; gap: 6px; margin-bottom: 3px; }
.msg-row.user .msg-meta { justify-content: flex-end; }
.msg-name { font-size: 13px; font-weight: 600; color: #111827; }
.msg-role { font-size: 11px; color: #9ca3af; }

.msg-text { font-size: 14px; line-height: 1.55; color: #374151; white-space: pre-wrap; word-break: break-word; }
.msg-row.user .msg-text {
    background: #27272a; color: #ffffff;
    padding: 10px 14px; border-radius: 14px 2px 14px 14px;
}

.chat-input-area { padding: 12px 20px 16px 20px; background: #ffffff; }
.chat-input-box {
    border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; background: #ffffff;
}
.chat-status-bar {
    background: #f9fafb; padding: 8px 12px; border-bottom: 1px solid #f3f4f6;
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; color: #4b5563; font-weight: 500;
}
.status-dot { width: 6px; height: 6px; background: #22c55e; border-radius: 50%; }

[data-testid="stForm"] { border: none !important; padding: 0 !important; margin: 0 !important; background: transparent !important; }
[data-testid="stTextArea"] { min-height: unset !important; }
[data-testid="stTextArea"] textarea {
    border: none !important; box-shadow: none !important; background: #ffffff !important;
    padding: 10px 12px !important; color: #111827 !important; font-size: 14px !important;
    min-height: 60px !important; max-height: 60px !important; resize: none !important;
    caret-color: #111827 !important;
}
[data-testid="stTextArea"] textarea::placeholder {
    color: #9ca3af !important;
    opacity: 1 !important;
}
[data-testid="stTextArea"] textarea:focus {
    outline: none !important;
    caret-color: #111827 !important;
}
[data-testid="stFormSubmitButton"] {
    display: flex; justify-content: flex-end;
    margin-top: -40px !important; margin-right: 10px !important; padding-bottom: 8px !important;
}
[data-testid="stFormSubmitButton"] button {
    background: #6b7280 !important; color: #ffffff !important; border: none !important;
    border-radius: 6px !important; padding: 4px 18px !important; font-size: 13px !important;
    min-height: 30px !important; font-weight: 500 !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    background: #4b5563 !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def api_get(path: str, params: dict[str, Any] | None = None) -> dict:
    resp = requests.get(f"{API_BASE}{path}", params=params or {}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: dict[str, Any]) -> dict:
    resp = requests.post(f"{API_BASE}{path}", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _default_focus() -> dict[str, Any]:
    return {
        "limit": 450,
        "sales_order": "",
        "delivery_document": "",
        "billing_document": "",
        "journal_document": "",
    }


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "focus" not in st.session_state:
        st.session_state.focus = _default_focus()
    if "last_graph" not in st.session_state:
        st.session_state.last_graph = {"nodes": [], "edges": []}


def subgraph_params() -> dict[str, Any]:
    """Query params for GET /graph/subgraph — one focused entity at a time (priority order)."""
    f = st.session_state.focus
    p: dict[str, Any] = {"limit": int(f.get("limit", 450))}
    if f.get("sales_order"):
        p["sales_order"] = f["sales_order"]
    elif f.get("delivery_document"):
        p["delivery_document"] = f["delivery_document"]
    elif f.get("billing_document"):
        p["billing_document"] = f["billing_document"]
    elif f.get("journal_document"):
        p["journal_document"] = f["journal_document"]
    return p


def handle_submit():
    prompt = st.session_state.chat_input_val
    if prompt and prompt.strip():
        st.session_state.messages.append({"role": "user", "text": prompt.strip()})
        try:
            answer_payload = api_post("/ask", {"query": prompt.strip()})
            st.session_state.messages.append(
                {"role": "assistant", "text": answer_payload.get("answer", "")}
            )

            ent_ids = answer_payload.get("details", {}).get("entity_ids", {})
            so = str(ent_ids.get("salesOrder") or "").strip()
            deliv = str(ent_ids.get("deliveryDocument") or "").strip()
            bill = str(ent_ids.get("billingDocument") or "").strip()
            je = str(ent_ids.get("journalEntry") or "").strip()

            ev = answer_payload.get("details", {}).get("evidence") or {}
            ev_jes = (ev.get("entity_ids") or {}).get("journalEntries") or []
            if not je and ev_jes:
                je = str(ev_jes[0]).strip()

            if so:
                st.session_state.focus = {
                    **_default_focus(),
                    "sales_order": so,
                }
            elif deliv:
                st.session_state.focus = {
                    **_default_focus(),
                    "delivery_document": deliv,
                }
            elif bill:
                st.session_state.focus = {
                    **_default_focus(),
                    "billing_document": bill,
                }
            elif je:
                st.session_state.focus = {
                    **_default_focus(),
                    "journal_document": je,
                }
        except Exception as exc:
            st.session_state.messages.append(
                {"role": "assistant", "text": f"Request failed: {exc}"}
            )


def primary_detail_node_id(nodes: list[dict], highlight_ids: list[str]) -> str | None:
    """Prefer JournalEntry, then Billing/Delivery/SO hub, for auto-opening the overlay card."""
    hi = set(highlight_ids)
    if not hi:
        return None
    order = ("JournalEntry", "BillingDocument", "Delivery", "SalesOrder", "Payment")
    for label in order:
        for n in nodes:
            if n.get("type") == label and n.get("id") in hi:
                return str(n["id"])
    return str(highlight_ids[-1])


def build_graph_html(
    nodes: list[dict],
    edges: list[dict],
    highlight_ids: list[str] | None = None,
    highlight_edge_ids: list[str] | None = None,
    auto_card_node_id: str | None = None,
) -> str:
    """vis-network with blue result path and floating node detail card."""
    hubs = {"SalesOrder", "Delivery", "BillingDocument", "JournalEntry", "Payment"}
    hi = set(highlight_ids or [])
    hi_e = set(highlight_edge_ids or [])
    has_focus = bool(hi)

    vis_nodes = []
    for n in nodes:
        nid = n["id"]
        ntype = n.get("type", "Entity")
        is_hub = ntype in hubs
        on_path = nid in hi
        if is_hub:
            if on_path and has_focus:
                bg, border, size = "#dbeafe", "#2563eb", 14
            else:
                bg, border, size = "#eff6ff", "#93c5fd", 10
        else:
            if on_path and has_focus:
                bg, border, size = "#eff6ff", "#2563eb", 8
            else:
                bg, border, size = "#ffffff", "#fca5a5", 4
        bw = 2 if (on_path and has_focus) else 1
        vis_nodes.append({
            "id": nid,
            "label": "",
            "size": size,
            "color": {"background": bg, "border": border,
                       "highlight": {"background": "#dbeafe", "border": "#1d4ed8"}},
            "shape": "dot",
            "borderWidth": bw,
        })

    vis_edges = []
    for e in edges:
        eid = e.get("id") or f"{e.get('source')}|{e.get('target')}|{e.get('type', '')}"
        on_path = eid in hi_e
        if has_focus and on_path:
            ec, ew = "#2563eb", 5
        elif has_focus:
            ec, ew = "#e5e7eb", 1
        else:
            ec, ew = "#bfdbfe", 1
        vis_edges.append({
            "id": eid,
            "from": e["source"],
            "to": e["target"],
            "color": {"color": ec, "highlight": "#1d4ed8"},
            "width": ew,
            "smooth": False,
        })

    node_lookup = {}
    for n in nodes:
        nid = n["id"]
        ntype = n.get("type", "Entity")
        props = n.get("properties", {})
        entity_id = n.get("entityId", ntype)
        node_lookup[nid] = {"type": ntype, "entityId": entity_id, "properties": props}

    edge_list_json = json.dumps(vis_edges)
    node_list_json = json.dumps(vis_nodes)
    lookup_json = json.dumps(node_lookup)
    auto_card_json = json.dumps(auto_card_node_id)

    return f"""
<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
  html, body {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:#ffffff; }}
  #graph-wrap {{ position:relative; width:100%; height:100%; background:#ffffff; }}
  #graph {{ width:100%; height:100%; background:#ffffff; }}
  #card {{
    display:none; position:absolute; top:20px; left:20px;
    background:#fff; border:1px solid #e5e7eb; border-radius:12px;
    box-shadow:0 12px 28px -4px rgba(0,0,0,.12),0 4px 10px -2px rgba(0,0,0,.06);
    width:300px; max-height:calc(100% - 40px); overflow-y:auto; padding:20px;
    z-index:9999; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    font-size:13px; color:#4b5563; line-height:1.55;
  }}
  #card h3 {{
    margin:0 0 14px 0; font-size:16px; color:#111827; font-weight:700;
    border-bottom:1px solid #f3f4f6; padding-bottom:10px;
  }}
  #card .row {{ margin:5px 0; }}
  #card .row strong {{ color:#374151; font-weight:600; }}
  #card .row span {{ color:#6b7280; word-break:break-word; }}
  #card .footer {{
    margin-top:10px; padding-top:8px; border-top:1px solid #f3f4f6;
    color:#9ca3af; font-style:italic; font-size:12px;
  }}
</style>
</head><body>
<div id="graph-wrap">
  <div id="graph"></div>
  <div id="card"></div>
</div>
<script>
var nodesData = {node_list_json};
var edgesData = {edge_list_json};
var lookup = {lookup_json};
var autoCardNodeId = {auto_card_json};

var container = document.getElementById('graph');
var data = {{
  nodes: new vis.DataSet(nodesData),
  edges: new vis.DataSet(edgesData)
}};
var options = {{
  physics: {{ enabled: true, solver: 'barnesHut', barnesHut: {{ gravitationalConstant: -2800, springLength: 130 }}, stabilization: {{ iterations: 160 }} }},
  interaction: {{ hover: true, zoomView: true, dragView: true }},
  layout: {{ improvedLayout: false }},
  edges: {{ arrows: {{ to: {{ enabled: false }}, from: {{ enabled: false }} }}, smooth: false }},
  nodes: {{ font: {{ size: 10, color: '#111827' }} }}
}};
var network = new vis.Network(container, data, options);

var card = document.getElementById('card');

function renderCard(nodeId) {{
  var info = lookup[nodeId];
  if (!info) return;
  var html = '<h3>' + info.type + '</h3>';
  html += '<div class="row"><strong>Entity:</strong> <span>' + info.type + '</span></div>';
  var props = info.properties || {{}};
  var keys = Object.keys(props);
  var limit = Math.min(keys.length, 12);
  for (var i = 0; i < limit; i++) {{
    html += '<div class="row"><strong>' + keys[i] + ':</strong> <span>' + (props[keys[i]] !== null && props[keys[i]] !== undefined ? String(props[keys[i]]) : '') + '</span></div>';
  }}
  if (keys.length > 12) {{
    html += '<div class="footer">Additional fields hidden for readability</div>';
  }}
  var connCount = 0;
  edgesData.forEach(function(e) {{
    if (e.from === nodeId || e.to === nodeId) connCount++;
  }});
  html += '<div class="row"><strong>Connections:</strong> <span>' + connCount + '</span></div>';
  card.innerHTML = html;
  card.style.display = 'block';
}}

network.on('selectNode', function(params) {{
  renderCard(params.nodes[0]);
}});

network.on('deselectNode', function() {{
  card.style.display = 'none';
}});

network.on('click', function(params) {{
  if (params.nodes.length === 0) {{
    card.style.display = 'none';
    network.unselectAll();
  }}
}});

network.once('stabilizationIterationsDone', function() {{
  try {{
    network.fit({{ animation: {{ duration: 450, easingFunction: 'easeInOutQuad' }} }});
  }} catch (e) {{}}
  setTimeout(function() {{
    if (!autoCardNodeId || !lookup[autoCardNodeId]) return;
    network.selectNodes([autoCardNodeId]);
    renderCard(autoCardNodeId);
  }}, 500);
}});
</script>
</body></html>
"""


# ── Render ──────────────────────────────────────────────
_inject_css()
init_state()

st.markdown(
    '<div class="top-nav">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>'
    '<line x1="9" y1="3" x2="9" y2="21"></line></svg>'
    '<span class="divider">|</span>'
    '<div class="breadcrumb"><span class="path">Mapping /</span>'
    '<span class="title">Order to Cash</span></div></div>',
    unsafe_allow_html=True,
)

c_left, c_right = st.columns([4, 1], gap="small")

# ── Left column: graph ──────────────────────────────────
with c_left:
    try:
        graph_data = api_get("/graph/subgraph", params=subgraph_params())
        st.session_state.last_graph = graph_data
    except Exception:
        graph_data = st.session_state.last_graph

    filtered_nodes = graph_data.get("nodes", [])
    filtered_edges = graph_data.get("edges", [])
    hi_ids = graph_data.get("highlightNodeIds") or []
    he_ids = graph_data.get("highlightEdgeIds") or []
    auto_card = primary_detail_node_id(filtered_nodes, hi_ids)

    graph_html = build_graph_html(
        filtered_nodes,
        filtered_edges,
        hi_ids,
        he_ids,
        auto_card,
    )
    components.html(graph_html, height=720, scrolling=False)

# ── Right column: chat ──────────────────────────────────
with c_right:
    st.markdown(
        '<div class="chat-header">'
        "<h2>Chat with Graph</h2>"
        "<p>Order to Cash</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    msgs_html = '<div class="chat-container" id="chat-box">'
    msgs_html += (
        '<div class="msg-row ai">'
        '<div class="avatar avatar-ai">D</div>'
        '<div class="msg-content">'
        '<div class="msg-meta"><span class="msg-name">Dodge AI</span>'
        '<span class="msg-role">Graph Agent</span></div>'
        '<div class="msg-text">Hi! I can help you analyze the '
        "<strong>Order to Cash</strong> process.</div>"
        "</div></div>"
    )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            msgs_html += (
                '<div class="msg-row user">'
                '<div class="msg-content">'
                '<div class="msg-meta"><span class="msg-name">You</span>'
                '<div class="avatar avatar-user">'
                '<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
                '<circle cx="12" cy="7" r="4"/></svg></div></div>'
                f'<div class="msg-text">{html.escape(msg["text"])}</div>'
                "</div></div>"
            )
        else:
            msgs_html += (
                '<div class="msg-row ai">'
                '<div class="avatar avatar-ai">D</div>'
                '<div class="msg-content">'
                '<div class="msg-meta"><span class="msg-name">Dodge AI</span>'
                '<span class="msg-role">Graph Agent</span></div>'
                f'<div class="msg-text">{html.escape(msg["text"])}</div>'
                "</div></div>"
            )

    msgs_html += "</div>"
    st.markdown(msgs_html, unsafe_allow_html=True)

    st.markdown(
        '<div class="chat-input-area"><div class="chat-input-box">'
        '<div class="chat-status-bar"><div class="status-dot"></div>'
        "Dodge AI is awaiting instructions</div>",
        unsafe_allow_html=True,
    )
    with st.form("chat_form", clear_on_submit=True):
        st.text_area(
            "Query",
            key="chat_input_val",
            label_visibility="collapsed",
            placeholder="Analyze anything",
        )
        st.form_submit_button("Send", on_click=handle_submit)
    st.markdown("</div></div>", unsafe_allow_html=True)
