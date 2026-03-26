from __future__ import annotations

import asyncio
import html
import json
from typing import Any

import gradio as gr
from loguru import logger

CUSTOM_CSS = """
.main-header { text-align: center; padding: 1.5rem 0 0.5rem; }
.main-header h1 {
    font-size: 1.8rem; font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;
}
.main-header p { color: #6b7280; font-size: 0.95rem; margin: 0.25rem 0 0; }
.stat-card {
    background: linear-gradient(135deg, #f0f4ff 0%, #e8ecf8 100%);
    border-radius: 12px; padding: 1rem 1.25rem; text-align: center;
    border: 1px solid #dde3f0;
}
.stat-card .num { font-size: 1.6rem; font-weight: 700; color: #4f46e5; }
.stat-card .label { font-size: 0.8rem; color: #6b7280; margin-top: 2px; }
"""


def _run_async(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ── 颜色配置（与前端保持一致）──
TYPE_COLORS: dict[str, str] = {
    "Person": "#ef4444",
    "Organization": "#3b82f6",
    "Location": "#10b981",
    "Technology": "#8b5cf6",
    "Concept": "#f59e0b",
    "Event": "#ec4899",
}
DEFAULT_NODE_COLOR = "#6b7280"


def _build_cytoscape_html(graph_data: dict[str, Any]) -> str:
    """Render an interactive Cytoscape.js graph inside an iframe srcdoc.
    
    gr.HTML uses innerHTML which does NOT execute <script> tags.
    Wrapping in <iframe srcdoc> gives an independent document context where scripts run.
    """
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    stats = graph_data.get("stats", {})

    if not nodes:
        return """
        <div style="text-align:center;padding:80px 20px;color:#9ca3af;
                    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
          <div style="font-size:3.5rem;margin-bottom:16px;">🕸️</div>
          <div style="font-size:1.1rem;font-weight:600;margin-bottom:6px;">暂无图谱数据</div>
          <div style="font-size:0.9rem;">请先在「文档管理」中上传 PDF 文档</div>
        </div>"""

    total_nodes = stats.get("nodes", len(nodes))
    total_edges = stats.get("edges", len(edges))
    shown_nodes = stats.get("shown_nodes", len(nodes))
    shown_edges = stats.get("shown_edges", len(edges))

    # ── Cytoscape 数据：直接用原始字符串，json.dumps 处理 JS 转义 ──
    cy_nodes = []
    for n in nodes:
        name = str(n.get("label", n.get("id", "")))
        cy_nodes.append({
            "data": {
                "id": name,
                "label": name,
                "type": str(n.get("type", "")),
                "color": TYPE_COLORS.get(n.get("type", ""), DEFAULT_NODE_COLOR),
                "source_docs": [str(d) for d in n.get("source_docs", [])],
                "aliases": [str(a) for a in n.get("aliases", [])],
            }
        })

    cy_edges = []
    for i, e in enumerate(edges):
        cy_edges.append({
            "data": {
                "id": f"e{i}",
                "source": str(e.get("source", "")),
                "target": str(e.get("target", "")),
                "label": str(e.get("label", "")),
            }
        })

    nodes_json = json.dumps(cy_nodes, ensure_ascii=False)
    edges_json = json.dumps(cy_edges, ensure_ascii=False)

    # ── 类型图例（外层统计栏，纯 HTML 无 JS，直接渲染正常）──
    seen_types: list[str] = []
    for n in nodes:
        t = n.get("type", "")
        if t and t not in seen_types:
            seen_types.append(t)

    legend_html = "".join(
        f'<span style="display:inline-flex;align-items:center;margin:2px 8px 2px 0;font-size:0.8rem;">'
        f'<span style="width:10px;height:10px;border-radius:50%;'
        f'background:{TYPE_COLORS.get(t, DEFAULT_NODE_COLOR)};'
        f'display:inline-block;margin-right:5px;"></span>{html.escape(t)}</span>'
        for t in seen_types
    )
    truncate_tip = (
        f'<span style="color:#f59e0b;font-size:0.78rem;margin-left:8px;">'
        f'⚠ 显示 {shown_nodes}/{total_nodes} 节点，{shown_edges}/{total_edges} 边</span>'
        if shown_nodes < total_nodes or shown_edges < total_edges else ""
    )

    # ── iframe 内部完整 HTML 文档 ──
    # 使用 jsdelivr CDN（在中国大陆一般可访问）
    # JS 字符串用单引号，避免与 json.dumps 生成的双引号 " 冲突
    inner_html = (
        "<!DOCTYPE html>"
        "<html><head><meta charset='utf-8'>"
        "<script src='https://cdn.jsdelivr.net/npm/cytoscape@3.29.2/dist/cytoscape.min.js'></script>"
        "<style>"
        "* { box-sizing: border-box; margin: 0; padding: 0; }"
        "body { background: #fafbff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; overflow: hidden; }"
        "#cy { width: 100vw; height: 100vh; }"
        "#toolbar { position: fixed; top: 8px; left: 8px; display: flex; gap: 5px; flex-wrap: wrap;"
        "           background: rgba(255,255,255,0.96); padding: 7px; border-radius: 10px;"
        "           border: 1px solid #e5e7eb; z-index: 999; max-width: 380px; }"
        "input, select { padding: 4px 9px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 12px; outline: none; background: #fff; }"
        "button { padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; border: none; }"
        ".btn-primary { background: #4f46e5; color: #fff; }"
        ".btn-secondary { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }"
        "#detail { position: fixed; right: 8px; top: 8px; width: 195px; background: #fff;"
        "          border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px;"
        "          font-size: 12px; display: none; max-height: 90vh; overflow-y: auto; z-index: 999; }"
        "</style></head><body>"
        "<div id='toolbar'>"
        "  <input id='search' type='text' placeholder='搜索实体...' oninput='doSearch(this.value)' style='width:110px'>"
        "  <select id='layout' onchange='doLayout(this.value)'>"
        "    <option value='cose'>力导向</option>"
        "    <option value='concentric'>同心圆</option>"
        "    <option value='breadthfirst'>层次</option>"
        "    <option value='circle'>圆形</option>"
        "    <option value='grid'>网格</option>"
        "  </select>"
        "  <button class='btn-primary' onclick='cy.fit(undefined,30)'>适应</button>"
        "  <button class='btn-secondary' onclick='doReset()'>重置</button>"
        "</div>"
        "<div id='cy'></div>"
        "<div id='detail'>"
        "  <div style='font-weight:700;margin-bottom:8px;font-size:13px;'>节点详情</div>"
        "  <div id='dc'></div>"
        "</div>"
        f"<script>"
        f"const NODES={nodes_json};"
        f"const EDGES={edges_json};"
        "const cy=cytoscape({"
        "  container:document.getElementById('cy'),"
        "  elements:{nodes:NODES,edges:EDGES},"
        "  style:["
        "    {selector:'node',style:{"
        "      'background-color':'data(color)',"
        "      'label':'data(label)',"
        "      'font-size':'11px','color':'#1f2937',"
        "      'text-valign':'bottom','text-halign':'center','text-margin-y':'4px',"
        "      'width':'34px','height':'34px',"
        "      'border-width':'2px','border-color':'#fff',"
        "      'text-background-color':'rgba(255,255,255,0.85)',"
        "      'text-background-opacity':1,'text-background-padding':'2px',"
        "      'text-background-shape':'roundrectangle',"
        "      'text-max-width':'75px','text-wrap':'ellipsis'"
        "    }},"
        "    {selector:'node.highlighted',style:{"
        "      'border-color':'#4f46e5','border-width':'3px','width':'42px','height':'42px'"
        "    }},"
        "    {selector:'node.dimmed',style:{'opacity':0.15}},"
        "    {selector:'edge',style:{"
        "      'width':1.5,'line-color':'#94a3b8',"
        "      'target-arrow-color':'#94a3b8','target-arrow-shape':'triangle',"
        "      'curve-style':'bezier',"
        "      'label':'data(label)','font-size':'9px','color':'#64748b',"
        "      'text-background-color':'rgba(255,255,255,0.85)',"
        "      'text-background-opacity':1,'text-background-padding':'2px',"
        "      'text-rotation':'autorotate','text-max-width':'60px','text-wrap':'ellipsis'"
        "    }},"
        "    {selector:'edge.highlighted',style:{"
        "      'line-color':'#4f46e5','target-arrow-color':'#4f46e5','width':2.5"
        "    }},"
        "    {selector:'edge.dimmed',style:{'opacity':0.1}}"
        "  ],"
        "  layout:{name:'cose',animate:true,animationDuration:700,"
        "           nodeRepulsion:8000,gravity:0.2,idealEdgeLength:80},"
        "  wheelSensitivity:0.3"
        "});"
        "cy.on('tap','node',function(evt){"
        "  const d=evt.target.data();"
        "  document.getElementById('detail').style.display='block';"
        "  const c=d.color||'#6b7280';"
        "  const docs=(d.source_docs||[]).map(s=>"
        "    '<div style=\"background:#f0f4ff;padding:1px 7px;border-radius:5px;margin:2px 0;font-size:11px\">'+s+'</div>'"
        "  ).join('')||'—';"
        "  document.getElementById('dc').innerHTML="
        "    '<div style=\"display:flex;align-items:center;gap:5px;margin-bottom:7px\">'"
        "    +'<span style=\"width:10px;height:10px;border-radius:50%;background:'+c+';display:inline-block\"></span>'"
        "    +'<strong style=\"word-break:break-all\">'+d.label+'</strong></div>'"
        "    +'<div style=\"margin-bottom:5px\"><span style=\"color:#6b7280;font-size:11px\">类型</span><br>'"
        "    +'<span style=\"background:'+c+'20;color:'+c+';padding:1px 8px;border-radius:10px;font-size:11px\">'+d.type+'</span></div>'"
        "    +'<div><span style=\"color:#6b7280;font-size:11px\">来源文档</span><br>'+docs+'</div>';"
        "  cy.elements().removeClass('highlighted dimmed');"
        "  const nbr=evt.target.neighborhood().add(evt.target);"
        "  cy.elements().not(nbr).addClass('dimmed');"
        "  nbr.addClass('highlighted');"
        "});"
        "cy.on('tap',function(evt){"
        "  if(evt.target===cy){"
        "    cy.elements().removeClass('highlighted dimmed');"
        "    document.getElementById('detail').style.display='none';"
        "  }"
        "});"
        "function doSearch(kw){"
        "  kw=kw.trim().toLowerCase();"
        "  if(!kw){cy.elements().removeClass('highlighted dimmed');return;}"
        "  const m=cy.nodes().filter(n=>n.data('label').toLowerCase().includes(kw));"
        "  if(!m.length){cy.elements().removeClass('highlighted dimmed');return;}"
        "  cy.elements().addClass('dimmed');"
        "  m.neighborhood().add(m).removeClass('dimmed').addClass('highlighted');"
        "}"
        "function doLayout(name){"
        "  const o={"
        "    cose:{name:'cose',animate:true,animationDuration:500,nodeRepulsion:8000,gravity:0.2},"
        "    concentric:{name:'concentric',animate:true},"
        "    breadthfirst:{name:'breadthfirst',animate:true,directed:true},"
        "    circle:{name:'circle',animate:true},"
        "    grid:{name:'grid',animate:true}"
        "  };"
        "  cy.layout(o[name]||o.cose).run();"
        "}"
        "function doReset(){"
        "  cy.elements().removeClass('highlighted dimmed');"
        "  document.getElementById('detail').style.display='none';"
        "  document.getElementById('search').value='';"
        "}"
        "</script></body></html>"
    )

    # srcdoc 属性值只需转义 & 和 "（不转义 < > 以保留 HTML 标签）
    srcdoc = inner_html.replace("&", "&amp;").replace('"', "&quot;")

    return (
        f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
        f'<div style="display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap;align-items:center;">'
        f'<div style="flex:1;min-width:80px;background:linear-gradient(135deg,#eff6ff,#dbeafe);'
        f'border-radius:10px;padding:10px;text-align:center;border:1px solid #bfdbfe;">'
        f'<div style="font-size:1.4rem;font-weight:700;color:#2563eb;">{total_nodes}</div>'
        f'<div style="font-size:0.78rem;color:#6b7280;">实体节点</div></div>'
        f'<div style="flex:1;min-width:80px;background:linear-gradient(135deg,#f0fdf4,#dcfce7);'
        f'border-radius:10px;padding:10px;text-align:center;border:1px solid #bbf7d0;">'
        f'<div style="font-size:1.4rem;font-weight:700;color:#16a34a;">{total_edges}</div>'
        f'<div style="font-size:0.78rem;color:#6b7280;">关系连接</div></div>'
        f'<div style="flex:1;min-width:80px;background:linear-gradient(135deg,#fdf4ff,#f3e8ff);'
        f'border-radius:10px;padding:10px;text-align:center;border:1px solid #e9d5ff;">'
        f'<div style="font-size:1.4rem;font-weight:700;color:#9333ea;">{len(seen_types)}</div>'
        f'<div style="font-size:0.78rem;color:#6b7280;">实体类型</div></div>'
        f'<div style="flex:3;min-width:180px;background:#fafafa;border-radius:10px;'
        f'padding:10px;border:1px solid #e5e7eb;">{legend_html}{truncate_tip}</div>'
        f'</div>'
        f'<iframe srcdoc="{srcdoc}" '
        f'style="width:100%;height:560px;border:1px solid #e5e7eb;border-radius:12px;display:block;" '
        f'></iframe>'
        f'<div style="font-size:0.75rem;color:#9ca3af;margin-top:5px;text-align:center;">'
        f'单击节点查看详情 · 滚轮缩放 · 拖拽移动</div>'
        f'</div>'
    )


def _format_answer_html(
    answer: str,
    strategy: str,
    confidence: float,
    sources: list,
    reasoning_path: list[str],
) -> str:
    strategy_label = {
        "vector": "向量检索", "graph": "图谱推理", "hybrid": "混合检索"
    }.get(strategy, strategy)
    strategy_color = {
        "vector": "#2563eb", "graph": "#16a34a", "hybrid": "#d97706"
    }.get(strategy, "#6b7280")
    conf_color = "#16a34a" if confidence >= 0.7 else "#d97706" if confidence >= 0.4 else "#ef4444"

    meta_html = f"""
    <div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
      <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 14px;
           border-radius:20px;background:{strategy_color}10;border:1px solid {strategy_color}30;">
        <span style="color:{strategy_color};font-weight:600;font-size:0.85rem;">{strategy_label}</span>
      </div>
      <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 14px;
           border-radius:20px;background:{conf_color}10;border:1px solid {conf_color}30;">
        <span style="color:{conf_color};font-weight:600;font-size:0.85rem;">置信度 {confidence:.0%}</span>
      </div>
    </div>"""

    reasoning_html = ""
    if reasoning_path:
        steps = " → ".join(
            f'<span style="background:#f0fdf4;padding:2px 8px;border-radius:6px;'
            f'font-size:0.82rem;">{html.escape(s)}</span>'
            for s in reasoning_path
        )
        reasoning_html = f"""
        <div style="margin-bottom:12px;padding:10px 14px;background:#f8fafc;
             border-radius:8px;border:1px solid #e2e8f0;">
          <div style="font-size:0.78rem;color:#64748b;margin-bottom:6px;font-weight:600;">推理路径</div>
          <div>{steps}</div>
        </div>"""

    sources_html = ""
    if sources:
        items = [
            f'<div style="padding:8px 10px;background:#fff;border-radius:6px;'
            f'border:1px solid #e5e7eb;margin-bottom:5px;">'
            f'<div style="font-size:0.75rem;color:#6b7280;margin-bottom:2px;">'
            f'来源{i+1} · {html.escape(s.doc_id)} · 第{s.page}页</div>'
            f'<div style="font-size:0.83rem;color:#374151;">'
            f'{html.escape(s.text[:150])}{"..." if len(s.text) > 150 else ""}</div>'
            f'</div>'
            for i, s in enumerate(sources)
        ]
        sources_html = f"""
        <div style="margin-top:12px;padding:10px 14px;background:#f8fafc;
             border-radius:8px;border:1px solid #e2e8f0;">
          <div style="font-size:0.78rem;color:#64748b;margin-bottom:8px;font-weight:600;">引用来源</div>
          {''.join(items)}
        </div>"""

    return meta_html + reasoning_html + sources_html


def create_ui(
    upload_handler: Any,
    query_handler: Any,
    list_docs_handler: Any,
    graph_data_handler: Any | None = None,
    list_doc_ids_handler: Any | None = None,
) -> gr.Blocks:
    with gr.Blocks(title="Adaptive-GraphRAG") as app:

        gr.HTML(f"""
        <style>{CUSTOM_CSS}</style>
        <div class="main-header">
            <h1>Adaptive-GraphRAG</h1>
            <p>自适应知识图谱增强检索系统 — 让 RAG 从「死记硬背」升级为「关系推理」</p>
        </div>""")

        with gr.Tabs():
            # ── Tab 1: 文档管理 ──
            with gr.Tab("文档管理"):
                gr.Markdown("##### 上传 PDF 文档，系统将自动解析、分块、向量化并构建知识图谱")
                with gr.Row(equal_height=False):
                    with gr.Column(scale=2):
                        file_input = gr.File(
                            label="选择 PDF 文档", file_types=[".pdf"], type="filepath"
                        )
                        upload_btn = gr.Button("上传并处理", variant="primary", size="lg")
                        upload_status = gr.Textbox(
                            label="处理结果", interactive=False, lines=6,
                            placeholder="上传文档后，处理结果将显示在这里...",
                        )
                    with gr.Column(scale=3):
                        with gr.Row():
                            stat_docs = gr.HTML(
                                '<div class="stat-card"><div class="num">0</div>'
                                '<div class="label">已上传文档</div></div>'
                            )
                            stat_graph_nodes = gr.HTML(
                                '<div class="stat-card"><div class="num">0</div>'
                                '<div class="label">图谱节点</div></div>'
                            )
                            stat_graph_edges = gr.HTML(
                                '<div class="stat-card"><div class="num">0</div>'
                                '<div class="label">图谱关系</div></div>'
                            )
                        doc_list = gr.Dataframe(
                            headers=["ID", "文件名", "页数", "状态", "创建时间"],
                            label="已上传文档", interactive=False, wrap=True,
                        )
                        refresh_btn = gr.Button("刷新列表", size="sm")

                def on_upload(file_path: str | None) -> str:
                    if not file_path:
                        return "请先选择 PDF 文件"
                    return _run_async(upload_handler(file_path))

                def on_refresh() -> tuple[list, str, str, str]:
                    docs = list_docs_handler()
                    status_map = {
                        "ready": "✅ 就绪", "processing": "⏳ 处理中",
                        "failed": "❌ 失败", "pending": "⏸ 待处理",
                    }
                    table = [
                        [d.id, d.filename, str(d.page_count),
                         status_map.get(d.status.value, d.status.value),
                         d.created_at.strftime("%Y-%m-%d %H:%M")]
                        for d in docs
                    ]
                    node_count = 0
                    edge_count = 0
                    if graph_data_handler:
                        data = graph_data_handler()
                        node_count = data.get("stats", {}).get("nodes", 0)
                        edge_count = data.get("stats", {}).get("edges", 0)
                    return (
                        table,
                        f'<div class="stat-card"><div class="num">{len(docs)}</div>'
                        f'<div class="label">已上传文档</div></div>',
                        f'<div class="stat-card"><div class="num">{node_count}</div>'
                        f'<div class="label">图谱节点</div></div>',
                        f'<div class="stat-card"><div class="num">{edge_count}</div>'
                        f'<div class="label">图谱关系</div></div>',
                    )

                upload_btn.click(fn=on_upload, inputs=file_input, outputs=upload_status)
                refresh_btn.click(
                    fn=on_refresh,
                    outputs=[doc_list, stat_docs, stat_graph_nodes, stat_graph_edges],
                )

            # ── Tab 2: 智能问答 ──
            with gr.Tab("智能问答"):
                gr.Markdown("##### 输入问题，系统将根据问题复杂度自动选择最优检索策略")
                with gr.Row(equal_height=False):
                    with gr.Column(scale=2):
                        query_input = gr.Textbox(
                            label="你的问题",
                            placeholder="例如：这篇文档主要讲了什么？\n或者：张三和李四是什么关系？",
                            lines=3,
                        )
                        mode_selector = gr.Radio(
                            choices=[
                                ("自适应 (推荐)", "auto"),
                                ("向量检索", "vector"),
                                ("图谱推理", "graph"),
                                ("混合检索", "hybrid"),
                            ],
                            value="auto", label="检索模式",
                        )
                        ask_btn = gr.Button("开始提问", variant="primary", size="lg")
                    with gr.Column(scale=3):
                        answer_output = gr.Markdown(value="*等待提问...*", label="回答")
                        detail_html = gr.HTML(value="")

                def on_query(question: str, mode: str) -> tuple[str, str]:
                    if not question.strip():
                        return "*请输入问题*", ""
                    result = _run_async(query_handler(question, mode))
                    detail = _format_answer_html(
                        result.answer,
                        result.strategy_used.value,
                        result.confidence,
                        result.sources,
                        result.reasoning_path,
                    )
                    return result.answer, detail

                ask_btn.click(
                    fn=on_query,
                    inputs=[query_input, mode_selector],
                    outputs=[answer_output, detail_html],
                )
                query_input.submit(
                    fn=on_query,
                    inputs=[query_input, mode_selector],
                    outputs=[answer_output, detail_html],
                )

            # ── Tab 3: 知识图谱 ──
            with gr.Tab("知识图谱"):
                gr.Markdown("##### 交互式实体关系图谱 — 单击节点查看详情，搜索高亮，支持多种布局")
                with gr.Row():
                    graph_doc_filter = gr.Dropdown(
                        choices=["全部文档"],
                        value="全部文档",
                        label="文档过滤",
                        interactive=True,
                        scale=2,
                    )
                    graph_refresh_btn = gr.Button("刷新图谱", variant="primary", scale=1)

                graph_display = gr.HTML(
                    value="""<div style="text-align:center;padding:80px 20px;color:#9ca3af;
                    font-family:-apple-system,sans-serif;">
                    <div style="font-size:3.5rem;">🕸️</div>
                    <div style="margin-top:12px;font-size:1.1rem;font-weight:600;">点击「刷新图谱」加载</div>
                    </div>"""
                )

                def on_graph_refresh(doc_filter: str) -> str:
                    if graph_data_handler is None:
                        return "<div>图谱功能未启用</div>"
                    doc_id = None if doc_filter == "全部文档" else doc_filter
                    data = graph_data_handler(doc_id)
                    return _build_cytoscape_html(data)

                def on_tab_load() -> gr.Dropdown:
                    """Populate the doc filter dropdown when the tab is refreshed."""
                    choices = ["全部文档"]
                    if list_doc_ids_handler:
                        choices += list_doc_ids_handler()
                    return gr.Dropdown(choices=choices, value="全部文档")

                graph_refresh_btn.click(
                    fn=on_graph_refresh,
                    inputs=[graph_doc_filter],
                    outputs=[graph_display],
                )
                graph_refresh_btn.click(
                    fn=on_tab_load,
                    outputs=[graph_doc_filter],
                )

        gr.HTML("""
        <div style="text-align:center;padding:12px 0 4px;color:#9ca3af;font-size:0.78rem;">
            Adaptive-GraphRAG · Powered by Ollama + ChromaDB + NetworkX + Cytoscape.js
        </div>""")

    return app
