#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
xmind2pdf.py  -  把 XMind 文件转成「思维导图样式」的 PDF（无需安装 XMind）

特点：
  * 直接解析 XMind 内部的 ZIP 结构（content.json 新版 / content.xml 旧版），不启动 XMind
  * 自带图形界面：把 .xmind 文件拖进窗口，或点击选择，即可在同目录导出同名 .pdf
  * 也支持命令行：  python xmind2pdf.py a.xmind b.xmind

依赖：  pip install reportlab
字体：  使用 reportlab 自带的 STSong-Light 中文字体，无需额外字体文件
"""

import os
import sys
import json
import zipfile
import xml.etree.ElementTree as ET

# ----------------------------- 布局参数 -----------------------------
FONT_SIZE = 11
PAD_X = 10
PAD_Y = 6
LINE_H = 16
MAX_W = 220
H_GAP = 46
V_GAP = 14
PAGE_PADDING = 16
MAX_PAGE_W = 1400   # 允许更宽的页面（适应横向导图）
MAX_PAGE_H = 1000

# 默认配色（当主题没有颜色信息时使用）
DEFAULT_BRANCH_COLORS = ['#FFC947', '#E46D57', '#1F3C88',
                         '#8B5CF6', '#10B981', '#F59E0B',
                         '#EC4899', '#06B6D4']
DETACHED_COLORS =     ['#A78BFA', '#FBBF24', '#34D399',
                         '#60A5FA', '#F472B6', '#FB923C']

# ----------------------------- 中文字体 -----------------------------
FONT = 'STSong-Light'
try:
    import reportlab.pdfbase.pdfmetrics as pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont(FONT))
except Exception:
    FONT = 'Helvetica'


# ============================ 1. 解析 XMind ============================
def parse_xmind(path):
    """返回 sheets 列表，每个 sheet 是一个字典：
       {
         'root': topic_node,          # 主树（中心主题 + attached 子节点）
         'detached': [topic_node],    # 独立浮动主题列表（每个是一棵树）
         'branch_colors': [str],      # 从主题读取的分支颜色列表
       }"""
    if not zipfile.is_zipfile(path):
        raise ValueError("不是有效的 XMind（ZIP）文件: " + path)
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if 'content.json' in names:
            data = json.loads(z.read('content.json').decode('utf-8'))
            return _parse_json(data)
        if 'content.xml' in names:
            return _parse_xml(z.read('content.xml').decode('utf-8'))
    raise ValueError("找不到 content.json / content.xml，无法识别该 XMind 版本")


def _extract_theme_colors(sheet_data):
    """从 sheet 的 theme 数据中提取分支颜色"""
    try:
        theme = sheet_data.get("theme", {})
        map_props = theme.get("map", {}).get("properties", {})
        mlc = map_props.get("multi-line-colors", "")
        if mlc:
            colors = [c.strip() for c in mlc.split() if c.strip().startswith("#")]
            if colors:
                return colors
    except Exception:
        pass
    return list(DEFAULT_BRANCH_COLORS)


def _make_topic(title_str, note_str=""):
    return {'title': _clean(title_str), 'children': [], 'note': note_str}


def _json_topic(t):
    title = t.get('title', '') or ''
    if isinstance(title, list):
        title = ' '.join(str(x) for x in title)
    node = _make_topic(title, _note(t))
    ch = t.get('children') or {}
    for c in (ch.get('attached') or []):
        node['children'].append(_json_topic(c))
    return node


def _parse_json(data):
    if isinstance(data, list):
        data = {'sheets': data}
    sheets = []
    for sheet in data.get('sheets', []):
        rt = sheet.get('rootTopic', {})
        root = _json_topic(rt)
        # detached 节点是独立的浮动主题，不是 root 的子节点
        detached = []
        ch = rt.get('children') or {}
        for d in (ch.get('detached') or []):
            detached.append(_json_topic(d))
        branch_colors = _extract_theme_colors(sheet)
        sheets.append({
            'root': root,
            'detached': detached,
            'branch_colors': branch_colors,
        })
    return sheets


def _note(t):
    n = t.get('notes', {})
    if isinstance(n, dict):
        return (n.get('plain', {}).get('content') or '').strip()
    return ''


def _parse_xml(xml_text):
    root = ET.fromstring(xml_text)

    def local(tag):
        return tag.split('}')[-1]

    def xml_topic(el):
        title = ''
        children = []
        for child in el:
            tag = local(child.tag)
            if tag == 'title':
                title = (child.text or '').strip()
            elif tag == 'children':
                for sub in child:
                    if local(sub.tag) == 'topics':
                        for t in sub:
                            if local(t.tag) == 'topic':
                                children.append(xml_topic(t))
        return {'title': title or '(无标题)', 'children': children, 'note': ''}

    sheets = []
    for sheet_el in root.iter():
        if local(sheet_el.tag) == 'sheet':
            for topic in sheet_el:
                if local(topic.tag) == 'topic':
                    sheets.append({'root': xml_topic(topic),
                                   'detached': [],
                                   'branch_colors': list(DEFAULT_BRANCH_COLORS)})
                    break
    return sheets


def _clean(s):
    if not s or not str(s).strip():
        return '(无标题)'
    return ' '.join(str(s).split())


# ============================ 2. 布局计算 ==============================
def wrap_text(text, max_w):
    lines, cur = [], ''
    for ch in str(text):
        if ch == '\n':
            lines.append(cur); cur = ''; continue
        test = cur + ch
        if pdfmetrics.stringWidth(test, FONT, FONT_SIZE) <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = ch
    if cur: lines.append(cur)
    return lines or ['']


def measure(node):
    node['_lines'] = wrap_text(node['title'], MAX_W)
    w = max(pdfmetrics.stringWidth(l, FONT, FONT_SIZE) for l in node['_lines']) + 2 * PAD_X
    node['_w'] = w
    node['_h'] = len(node['_lines']) * LINE_H + 2 * PAD_Y
    for c in node['children']:
        measure(c)


def compute_total_h(node):
    """计算子树总高度"""
    if not node['children']:
        node['_th'] = node['_h']; return node['_th']
    s = sum(compute_total_h(c) for c in node['children'])
    s += V_GAP * (len(node['children']) - 1)
    node['_th'] = max(node['_h'], s)
    return node['_th']


def subtree_w(node):
    if not node['children']: return node['_w']
    return node['_w'] + H_GAP + max(subtree_w(c) for c in node['children'])


def assign_color_tree(node, color, depth=0):
    node['_color'] = color
    node['_depth'] = depth
    for c in node['children']:
        assign_color_tree(c, color, depth + 1)


def place_rightward(node, x, y_top):
    """把一棵树放在 x 右侧，从 y_top 开始向下排列子节点。返回树的总高度。"""
    node['_x'] = x
    node['_y'] = y_top + (node['_th'] - node['_h']) / 2
    if not node['children']:
        return node['_th']
    kids_h = sum(c['_th'] for c in node['children']) + V_GAP * (len(node['children']) - 1)
    cy = y_top + (node['_th'] - kids_h) / 2
    cx = node['_x'] + node['_w'] + H_GAP
    for c in node['children']:
        place_rightward(c, cx, cy)
        cy += c['_th'] + V_GAP
    return node['_th']


def build_layout_main(root, branch_colors):
    """
    布局主树：中心节点在左，一级分支向右展开（保持原始顺序和颜色）。
    返回 (width, height)，所有节点获得 _x, _y, _w, _h, _color, _depth。
    """
    measure(root)
    root['_depth'] = 0
    root['_color'] = '#070D59'  # 中心节点深蓝底色

    # 给每个一级分支分配颜色（按顺序取主题颜色）
    for i, c in enumerate(root['children']):
        color = branch_colors[i % len(branch_colors)]
        assign_color_tree(c, color, depth=1)

    for c in root['children']:
        compute_total_h(c)

    # 根节点位置
    root_w = root['_w']
    root_h = root['_h']

    # 计算所有子树需要的空间
    total_kids_h = sum(c['_th'] for c in root['children']) + V_GAP * max(0, len(root['children']) - 1)
    overall_h = max(root_h, total_kids_h)

    # 根节点靠左
    root['_x'] = PAGE_PADDING
    root['_y'] = (overall_h - root_h) / 2

    # 一级分支向右排列
    rx = root['_x'] + root_w + H_GAP
    ry = (overall_h - total_kids_h) / 2
    for c in root['children']:
        place_rightward(c, rx, ry)
        ry += c['_th'] + V_GAP

    # 计算边界
    minx = miny = float('inf')
    maxx = maxy = float('-inf')
    def walk(n):
        nonlocal minx, miny, maxx, maxy
        minx = min(minx, n['_x']); miny = min(miny, n['_y'])
        maxx = max(maxx, n['_x'] + n['_w']); maxy = max(maxy, n['_y'] + n['_h'])
        for ch in n['children']: walk(ch)
    walk(root)

    # 平移到原点
    sx, sy = minx, miny
    def shift(n):
        n['_x'] -= sx; n['_y'] -= sy
        for ch in n['children']: shift(ch)
    shift(root)

    return maxx - minx, maxy - miny


def build_layout_detached(detached_list, base_color_idx=0):
    """
    布局独立浮动主题：每个 detached 节点作为独立小树，
    水平排列在主树下方（或右侧），各自独立不连线到根节点。
    返回 [(node, width, height), ...] 和总占用宽高。
    """
    results = []
    for dnode in detached_list:
        measure(dnode)
        assign_color_tree(dnode, DETACHED_COLORS[base_color_idx % len(DETACHED_COLORS)], depth=1)
        base_color_idx += 1
        compute_total_h(dnode)  # 计算整棵树高度（含自身和所有子节点）
        for c in dnode['children']:
            compute_total_h(c)

        # 简单的右向布局
        place_rightward(dnode, 0, 0)
        tw = subtree_w(dnode)
        th = dnode['_th']

        # 收集边界
        minx = miny = float('inf')
        maxx = maxy = float('-inf')
        def walk(n):
            nonlocal minx, miny, maxx, maxy
            minx = min(minx, n['_x']); miny = min(miny, n['_y'])
            maxx = max(maxx, n['_x'] + n['_w']); maxy = max(maxy, n['_y'] + n['_h'])
            for ch in n['children']: walk(ch)
        walk(dnode)

        sx, sy = minx, miny
        def shift(n):
            n['_x'] -= sx; n['_y'] -= sy
            for ch in n['children']: shift(ch)
        shift(dnode)

        results.append((dnode, maxx - minx, maxy - miny))

    return results


# ============================ 3. 渲染 PDF ============================
def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


def lighten(rgb, f=0.85):
    return tuple(r + (1-r)*f for r in rgb)


def T(x, y, s, OX, OY, pageH):
    return (x*s + OX, pageH - (y*s + OY))


def render_pdf(sheets, out_path):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(out_path)
    for sheet in sheets:
        root = sheet['root']
        detached = sheet.get('detached', [])
        branch_colors = sheet.get('branch_colors', DEFAULT_BRANCH_COLORS)

        # ---- 布局主树 ----
        mw, mh = build_layout_main(root, branch_colors)

        # ---- 布局独立浮动主题 ----
        det_results = build_layout_detached(detached) if detached else []

        # ---- 计算整体尺寸：主树在上，浮动主题在下 ----
        det_gap = 30  # 主树与浮动区域之间的间距
        if det_results:
            dw_max = max(w for _, w, _ in det_results)
            dh_sum = sum(h for _, _, h in det_results) + det_gap * (len(det_results) - 1)
            total_w = max(mw, dw_max)
            total_h = mh + det_gap + dh_sum
        else:
            total_w, total_h = mw, mh

        # 缩放
        avail_w = MAX_PAGE_W - 2*PAGE_PADDING
        avail_h = MAX_PAGE_H - 2*PAGE_PADDING
        if total_w <= avail_w and total_h <= avail_h:
            pageW, pageH = total_w + 2*PAGE_PADDING, total_h + 2*PAGE_PADDING
            sc, ox, oy = 1.0, PAGE_PADDING, PAGE_PADDING
        else:
            sc = min(avail_w/total_w, avail_h/total_h)
            pageW, pageH = MAX_PAGE_W, MAX_PAGE_H
            ox = (pageW - total_w*sc)/2
            oy = (pageH - total_h*sc)/2

        c.setPageSize((pageW, pageH))
        c.setFillColorRGB(1,1,1)
        c.rect(0,0,pageW,pageH,fill=1,stroke=0)

        # ---- 渲染主树 ----
        _render_tree(c, root, sc, ox, oy, pageH)

        # ---- 渲染浮动主题（放在主树下方）----
        if det_results:
            dy = oy + mh*sc + det_gap*sc
            dx_base = ox
            for dnode, dw, dh in det_results:
                _render_tree(c, dnode, sc, dx_base, dy, pageH)
                dy += dh*sc + det_gap*sc

        c.showPage()
    c.save()


def _render_tree(c, root, sc, ox, oy, pageH):
    """渲染一棵完整的树（含连线和节点）"""
    nodes, edges = [], []
    def collect(n):
        nodes.append(n)
        for ch in n['children']:
            edges.append((n, ch))
            collect(ch)
    collect(root)

    for parent, child in edges:
        _draw_edge(c, parent, child, sc, ox, oy, pageH)
    for node in nodes:
        _draw_node(c, node, sc, ox, oy, pageH)


def _draw_edge(c, parent, child, sc, ox, oy, pageH):
    pr = parent['_x'] + parent['_w']
    cl = child['_x']
    x1, y1 = T(pr, parent['_y']+parent['_h']/2, sc, ox, oy, pageH)
    x2, y2 = T(cl, child['_y']+child['_h']/2, sc, ox, oy, pageH)
    mx = (x1+x2)/2
    color = hex2rgb(child.get('_color','#888'))
    c.setStrokeColorRGB(*color)
    c.setLineWidth(max(0.8, 1.4*sc))
    p = c.beginPath(); p.moveTo(x1,y1)
    p.curveTo(mx,y1,mx,y2,x2,y2)
    c.drawPath(p,stroke=1,fill=0)


def _draw_node(c, node, sc, ox, oy, pageH):
    x0, y0, w, h = node['_x'], node['_y'], node['_w'], node['_h']
    left, bottom = T(x0, y0+h, sc, ox, oy, pageH)
    width, height = w*sc, h*sc
    depth = node.get('_depth', 0)

    if depth == 0:
        fill, text_col = hex2rgb('#070D59'), (1,1,1)   # 中心节点深蓝底白字
    elif depth == 1:
        fill, text_col = hex2rgb(node['_color']), (1,1,1)  # 一级分支：彩色底白字
    else:
        fill, text_col = lighten(hex2rgb(node['_color']), 0.82), (0.13,0.13,0.13)  # 更浅底深字

    c.setFillColorRGB(*fill)
    r = min(6, width/2, height/2)
    c.roundRect(left,bottom,width,height,r,stroke=0,fill=1)

    c.setFillColorRGB(*text_col)
    sz = max(6, FONT_SIZE*sc)
    c.setFont(FONT, sz)
    for k, line in enumerate(node['_lines']):
        lt = y0 + PAD_Y + k*LINE_H
        X = x0*sc + ox + PAD_X*sc
        Yb = pageH - ((lt + LINE_H*0.78)*sc + oy)
        c.drawString(X, Yb, line)


# ============================ 4. 转换入口 ============================
def convert(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    out = os.path.splitext(path)[0] + '.pdf'
    sheets = parse_xmind(path)
    if not sheets:
        raise ValueError("文件中没有可解析的导图内容")
    render_pdf(sheets, out)
    return out


# ============================ 5. 图形界面 ============================
def run_gui():
    import tkinter as tk
    from tkinter import filedialog

    app = tk.Tk()
    app.title("XMind → PDF 转换器（免装 XMind）")
    try: app.state('normal')
    except Exception: pass
    app.geometry("580x400")

    status_var = tk.StringVar(value="")

    def _norm(p):
        if isinstance(p, bytes): p = p.decode('utf-8','ignore')
        return p

    def do_convert(paths):
        paths = [_norm(p) for p in paths]
        lines, last_ok = [], None
        for p in paths:
            try:
                out = convert(p)
                lines.append("✔ " + os.path.basename(p) + "\n    → " + out)
                last_ok = out
            except Exception as e:
                lines.append("✘ " + os.path.basename(p) + "\n    错误: " + str(e))
        status_var.set("\n".join(lines))
        if last_ok:
            try: os.startfile(os.path.dirname(last_ok))
            except Exception: pass

    def choose():
        files = filedialog.askopenfilenames(
            title="选择 XMind 文件",
            filetypes=[("XMind 文件","*.xmind"),("所有文件","*.*")])
        if files: do_convert(list(files))

    tk.Label(app, text="把 XMind 文件拖到下方，或点击选择",
             font=("Microsoft YaHei UI",13)).pack(pady=(14,6))

    drop = tk.Label(app, text="📂  拖入 XMind 文件\n（也可以点击这里选择）",
                    width=42, height=8, relief="groove", bg="#eef3fb",
                    font=("Microsoft YaHei UI",11))
    drop.pack(pady=4)
    drop.bind("<Button-1>", lambda e: choose())
    tk.Button(app, text="选择文件并转换", command=choose,
              font=("Microsoft YaHei UI",10)).pack(pady=4)

    st = tk.Label(app, textvariable=status_var, justify="left", anchor="nw",
                  font=("Consolas",9), bg="white", relief="sunken", wraplength=540)
    st.pack(fill="both", expand=True, padx=14, pady=(10,14))

    try:
        from windnd import hook_dropfiles
        hook_dropfiles(drop, lambda files: app.after(0, do_convert, files))
    except Exception:
        pass

    app.mainloop()


def main():
    try:
        if len(sys.argv) > 1:
            for f in sys.argv[1:]:
                try:
                    out = convert(f)
                    print("OK  ", f, "->", out)
                except Exception as e:
                    print("ERR ", f, "->", e)
        else:
            run_gui()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        try:
            log = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "xmind2pdf_error.log")
            with open(log,"w",encoding="utf-8") as f: f.write(tb)
        except Exception: pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            r=tk.Tk(); r.withdraw()
            messagebox.showerror("XMind → PDF 出错","程序异常，详情见 xmind2pdf_error.log\n\n"+tb[:2000])
        except Exception: pass


if __name__ == '__main__':
    main()
