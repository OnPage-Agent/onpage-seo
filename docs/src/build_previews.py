#!/usr/bin/env python3
"""Builds report.html and terminal.html from a real audit run, for the README images.

    python3 ../../scripts/audit.py https://socialdonut.co > /tmp/report.md 2> /tmp/progress.txt
    python3 build_previews.py /tmp/report.md /tmp/progress.txt && ./render.sh
"""
import html
import re
import sys

md = open(sys.argv[1]).read()
progress = open(sys.argv[2]).read().strip().splitlines()
esc = html.escape


def inline(t):
    t = esc(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w/])_([^_]+)_(?![\w/])", r"<i>\1</i>", t)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)


def short_where(line):
    m = re.match(r"- \*\*Where:\*\* (.*)", line)
    if not m:
        return line
    items = re.findall(r"`[^`]+`", m.group(1))
    more = re.search(r"and (\d+) more", m.group(1))
    extra = (len(items) - 3) + (int(more.group(1)) if more else 0)
    return "- **Where:** " + ", ".join(items[:3]) + (" and %d more" % extra if extra > 0 else "")


body, in_list = [], False
for line in md.splitlines():
    line = short_where(line)
    if line.startswith("- "):
        if not in_list:
            body.append("<ul>")
            in_list = True
        body.append("<li>%s</li>" % inline(line[2:]))
        continue
    if in_list:
        body.append("</ul>")
        in_list = False
    if line.startswith("# "):
        body.append("<h1>%s</h1>" % inline(line[2:]))
    elif line.startswith("## "):
        body.append("<h2>%s</h2>" % inline(line[3:]))
    elif line.strip() == "---":
        body.append("<hr>")
    elif line.strip():
        body.append("<p>%s</p>" % inline(line))
if in_list:
    body.append("</ul>")

REPORT = """<!doctype html><html><head><meta charset="utf-8">
<!-- Source for docs/assets/report.png: a real Markdown report from audit.py, rendered like GitHub. Built by build_previews.py. -->
<style>
 html,body{width:1200px;margin:0;background:#F6F8FA;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#1F2328}
 .win{margin:28px;background:#fff;border:1px solid #D0D7DE;border-radius:12px;overflow:hidden;box-shadow:0 8px 30px rgba(31,35,40,.08)}
 .top{padding:12px 18px;border-bottom:1px solid #D0D7DE;background:#F6F8FA;font:600 14px ui-monospace,SFMono-Regular,Menlo,monospace;color:#57606A}
 .md{padding:16px 40px 28px} h1{font-size:30px;border-bottom:1px solid #D8DEE4;padding-bottom:8px;margin:12px 0 14px}
 h2{font-size:21px;border-bottom:1px solid #D8DEE4;padding-bottom:6px;margin:26px 0 10px} ul{padding-left:24px;margin:8px 0} li{margin:3px 0}
 code{font:85% ui-monospace,SFMono-Regular,Menlo,monospace;background:rgba(175,184,193,.2);padding:.2em .4em;border-radius:6px}
 a{color:#0969DA;text-decoration:none} hr{border:0;border-top:1px solid #D8DEE4;margin:24px 0} i{color:#57606A}
</style></head><body><div class="win"><div class="top">report.md</div><div class="md">{BODY}</div></div></body></html>"""
open("report.html", "w").write(REPORT.replace("{BODY}", "\n".join(body)))

lines = ['<span class="p">$</span> python3 scripts/audit.py https://socialdonut.co']
lines += ['<span class="m">%s</span>' % esc(l) for l in progress]
lines.append("")
for line in md.splitlines()[:16]:
    line = short_where(line)
    if line.startswith("# "):
        lines.append('<span class="h1">%s</span>' % esc(line))
    elif line.startswith("## "):
        lines.append('<span class="h2">%s</span>' % esc(line))
    elif line.startswith("Score"):
        lines.append('<span class="b">%s</span>' % esc(line))
    else:
        lines.append(esc(line))

TERMINAL = """<!doctype html><html><head><meta charset="utf-8">
<!-- Source for docs/assets/terminal.png: a real run of audit.py (output trimmed, nothing invented). Built by build_previews.py. -->
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
 html,body{width:1200px;margin:0;background:#0B1020}
 .term{margin:28px;background:#121A2E;border:1px solid #24304D;border-radius:14px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.45)}
 .bar{display:flex;gap:8px;align-items:center;padding:13px 16px;border-bottom:1px solid #24304D}
 .bar i{width:12px;height:12px;border-radius:50%} .bar span{margin-left:10px;font:500 13px "JetBrains Mono",monospace;color:#9AA6C2}
 pre{margin:0;padding:20px 24px 26px;font:14.5px/1.62 "JetBrains Mono",monospace;color:#E8ECF6;white-space:pre-wrap;word-break:break-word}
 .p{color:#6E93FF} .m{color:#7F8AA8} .h1{color:#fff;font-weight:600} .h2{color:#F2B54B;font-weight:600} .b{color:#3FCB8A;font-weight:600}
</style></head><body><div class="term"><div class="bar"><i style="background:#FF5F57"></i><i style="background:#FEBC2E"></i><i style="background:#28C840"></i><span>terminal</span></div><pre>{BODY}</pre></div></body></html>"""
open("terminal.html", "w").write(TERMINAL.replace("{BODY}", "\n".join(lines)))
print("built report.html and terminal.html")
