#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招聘需求简报 · 最小集查询 Demo
================================

任务：林亦舟查到当前招聘需求简报里「必备条件 / 偏好条件」的要求
资料：当前有效版本简报；作废与旧版本排除；合同硬约束与内部附加条件分列；
      客户内部筛选标准与财务预算不开放
输出：简短答案（哪些必备、哪些偏好）+ 来源原文（版本号 + 字段）
新增只读任务：只查林亦舟本人负责批次的简报确认状态与版本（不写回、不发外部消息）
验收：来源支持答案、权限正确、失败可解释、能按手册维护

教学说明：数据为合成演练样本，不代表任何企业真实经营数据。
          身份由 CLI 参数模拟，不是真实鉴权；生产环境须接正式 IdP。

用法：
    python3 brief_demo.py query J-2026-001                # 查必备/偏好（默认林亦舟）
    python3 brief_demo.py query J-2026-001 --field 财务预算  # 试探不开放字段（演示失败可解释）
    python3 brief_demo.py status                           # 只读查本人批次状态与版本
    python3 brief_demo.py status --as-user E002            # 换人查（只能看到自己的）
    python3 brief_demo.py query J-2026-003                 # 只有作废版本（演示失败可解释）
    python3 brief_demo.py query J-2026-004                 # 有效版本但未确认（演示提醒）
    python3 brief_demo.py raci                             # 角色分工
    python3 brief_demo.py manual                           # 维护手册
    python3 brief_demo.py demo                             # 一键跑全部场景
"""

import argparse
import json
import sys

TODAY = "2026-10-13"

# ---------------------------------------------------------------- 合成数据

USERS = {
    "E001": {"name": "林亦舟", "role": "招聘与用工服务顾问"},
    "E002": {"name": "同事甲", "role": "招聘与用工服务顾问"},
}

RACI = {
    "制度负责人": "顾明岚（服务业务负责人）：业务目标、试点范围与验收口径",
    "事实核对":   "唐映秋（排期与培训协调员）：交接留痕——版本/未结项/截止时间",
    "运行维护":   "秦芮（数据与系统工程师）：简报数据维护、失败快照、字段对齐",
    "质量把关":   "傅景（质量复核负责人）：授权确认、四要素留痕、异常人工队列",
    "客户口径":   "叶书（客户岗位负责人）：用途确认属对外承诺前置，不代客户表态",
}

# 条件 tier: 必备 / 偏好
# 条件 type: 合同硬约束 / 内部附加条件 / 客户口径
BRIEFS = [
    {
        "job_code": "J-2026-001",
        "title": "数据工程师（某银行科技子公司）",
        "owner": "E001",
        "versions": [
            {
                "version": "v1",
                "status": "superseded",          # 旧版本
                "valid_until": "2026-09-30",
                "confirmed": True,
                "conditions": [
                    {"field": "工作经验", "type": "内部附加条件", "tier": "必备",
                     "text": "3年以上数据开发经验"},
                    {"field": "证书", "type": "内部附加条件", "tier": "偏好",
                     "text": "持有PMP者优先"},
                ],
            },
            {
                "version": "v2",
                "status": "active",              # 当前有效
                "valid_until": "2026-12-31",
                "confirmed": True,
                "conditions": [
                    {"field": "学历", "type": "内部附加条件", "tier": "必备",
                     "text": "全日制本科及以上，计算机相关专业"},
                    {"field": "工作经验", "type": "合同硬约束", "tier": "必备",
                     "text": "3年以上数据开发经验（合同附件三约定）"},
                    {"field": "到岗时间", "type": "合同硬约束", "tier": "必备",
                     "text": "录用后4周内到岗（合同附件三约定）"},
                    {"field": "证书", "type": "内部附加条件", "tier": "偏好",
                     "text": "持有CDGA/CDMP者优先"},
                    {"field": "行业背景", "type": "客户口径", "tier": "偏好",
                     "text": "有银行/金融行业数据项目经历者优先（客户口头口径，叶书确认）"},
                ],
                "restricted_fields": ["客户内部筛选标准", "财务预算"],
            },
        ],
    },
    {
        "job_code": "J-2026-002",
        "title": "Java 开发工程师（某零售集团）",
        "owner": "E002",
        "versions": [
            {
                "version": "v1",
                "status": "active",
                "valid_until": "2026-11-30",
                "confirmed": True,
                "conditions": [
                    {"field": "学历", "type": "内部附加条件", "tier": "必备",
                     "text": "本科及以上"},
                ],
                "restricted_fields": ["客户内部筛选标准", "财务预算"],
            },
        ],
    },
    {
        "job_code": "J-2026-003",
        "title": "测试工程师（某保险公司）",
        "owner": "E001",
        "versions": [
            {
                "version": "v1",
                "status": "voided",              # 作废，保留原因
                "valid_until": "2026-08-31",
                "confirmed": False,
                "void_reason": "客户取消岗位，需求作废（2026-08-20 顾明岚确认）",
                "conditions": [],
            },
        ],
    },
    {
        "job_code": "J-2026-004",
        "title": "产品经理（某券商）",
        "owner": "E001",
        "versions": [
            {
                "version": "v2",
                "status": "active",
                "valid_until": "2026-12-31",
                "confirmed": False,              # 双条件之一不满足
                "conditions": [
                    {"field": "学历", "type": "内部附加条件", "tier": "必备",
                     "text": "本科及以上"},
                ],
                "restricted_fields": ["客户内部筛选标准", "财务预算"],
            },
        ],
    },
]

# ---------------------------------------------------------------- 核心逻辑

def _version_state(v):
    """双条件管理：版本有效期 + 确认状态（f24/f34 口径）"""
    reasons = []
    if v["status"] == "voided":
        reasons.append("已作废：%s" % v.get("void_reason", "未留原因"))
    elif v["status"] == "superseded":
        reasons.append("旧版本，已被后继版本取代")
    if v.get("valid_until", "9999-12-31") < TODAY:
        reasons.append("版本有效期已过（至 %s）" % v["valid_until"])
    if not v["confirmed"]:
        reasons.append("确认状态=未确认")
    return reasons


def find_brief(job_code):
    for b in BRIEFS:
        if b["job_code"] == job_code:
            return b
    return None


def active_version(brief):
    """返回 (当前有效版本, 审计轨迹)。有效 = 非 voided/superseded 且未过期；
    confirmed 单独标记，不静默吞掉。"""
    chosen, audit = None, []
    for v in brief["versions"]:
        reasons = _version_state(v)
        if v["status"] == "active" and "版本有效期已过（至 %s）" % v.get("valid_until") not in reasons:
            if chosen is None:
                chosen = v
                audit.append({"version": v["version"], "decision": "采用", "reason": "当前有效版本"})
            else:
                audit.append({"version": v["version"], "decision": "排除", "reason": "同一简报出现多个有效版本（版本断链，需人工处理队列）"})
        else:
            audit.append({"version": v["version"], "decision": "排除", "reason": "；".join(reasons) or "非有效状态"})
    return chosen, audit


def cmd_query(job_code, as_user, field=None):
    user = USERS.get(as_user)
    if user is None:
        return _fail("unknown_user", "用户 %s 不在权威员工表中" % as_user)

    brief = find_brief(job_code)
    if brief is None:
        return _fail("brief_not_found",
                     "未找到岗位代号 %s。失败可解释：请核对代号（当前库内：%s）"
                     % (job_code, "、".join(b["job_code"] for b in BRIEFS)))

    ver, audit = active_version(brief)

    # 试探不开放字段 → 权限正确（失败可解释）
    if field:
        if ver and field in ver.get("restricted_fields", []):
            return _fail("field_not_open",
                         "字段「%s」不开放。最小集资料边界：客户内部筛选标准与财务预算不对招聘顾问开放；"
                         "如业务确需，走顾明岚→叶书的客户口径确认流程" % field)
        if ver and any(c["field"] == field for c in ver["conditions"]):
            pass  # 落到正常输出，仅输出该字段
        else:
            return _fail("field_not_found", "字段「%s」在 %s 中不存在" % (field, ver["version"] if ver else "任何版本"))

    if ver is None:
        return _fail("no_active_version",
                     "岗位 %s 没有可用的有效版本。排除轨迹：%s"
                     % (job_code, json.dumps(audit, ensure_ascii=False)))

    conds = ver["conditions"]
    if field:
        conds = [c for c in conds if c["field"] == field]

    must = [c for c in conds if c["tier"] == "必备"]
    pref = [c for c in conds if c["tier"] == "偏好"]

    src = lambda c: "版本 %s · 字段「%s」· 类型 %s" % (ver["version"], c["field"], c["type"])
    answer_text = "必备 %d 项：%s；偏好 %d 项：%s" % (
        len(must), "、".join(c["field"] for c in must),
        len(pref), "、".join(c["field"] for c in pref))

    out = {
        "task": "查询当前招聘需求简报的必备/偏好条件",
        "as_user": "%s %s" % (as_user, user["name"]),
        "job": {"code": job_code, "title": brief["title"]},
        "answer": {
            "必备条件": [{"要求": c["text"], "来源": src(c)} for c in must],
            "偏好条件": [{"要求": c["text"], "来源": src(c)} for c in pref],
        },
        "answer_text": answer_text,
        "not_open": ver.get("restricted_fields", []),
        "audit": {
            "used_version": ver["version"],
            "confirmed": ver["confirmed"],
            "excluded_versions": [a for a in audit if a["decision"] == "排除"],
            "write_back": False, "external_message": False,
        },
    }
    if not ver["confirmed"]:
        out["warning"] = ("当前版本 %s 确认状态=未确认，答案仅供预览；"
                          "正式使用需业务负责人确认（傅景质量把关）" % ver["version"])
    return out


def cmd_status(as_user):
    """新增只读任务：只查本人负责批次的确认状态与版本。不写回、不发外部消息。"""
    user = USERS.get(as_user)
    if user is None:
        return _fail("unknown_user", "用户 %s 不在权威员工表中" % as_user)
    mine = []
    for b in BRIEFS:
        if b["owner"] != as_user:
            continue
        ver, _ = active_version(b)
        mine.append({
            "job_code": b["job_code"], "title": b["title"],
            "当前版本": ver["version"] if ver else None,
            "确认状态": "已确认" if (ver and ver["confirmed"]) else "未确认",
            "有效期至": ver["valid_until"] if ver else None,
        })
    return {
        "task": "只读查询本人负责批次的简报确认状态与版本",
        "as_user": "%s %s" % (as_user, user["name"]),
        "batches": mine,
        "note": "只读：不写回任何系统、不发送外部消息；他人批次不可见",
    }


def _fail(code, reason):
    return {"error": code, "reason": reason, "explainable_failure": True}


MANUAL = """\
维护手册（对应验收第 4 条：能按手册维护 · 运行维护：秦芮）
================================================

1. 新增一份简报
   在 BRIEFS 追加一条：job_code 唯一；首个版本 status="active"，写 valid_until 与 confirmed。

2. 简报内容变更（发新版本）
   旧版本 status 改为 "superseded"；新增版本号更高的 active 版本。
   双条件：版本有效期（valid_until）+ 确认状态（confirmed）任一不满足即不可作为答案依据。

3. 作废一份简报
   版本 status 改为 "voided"，必须填 void_reason（作废原因留痕，不靠文件名猜）。
   作废后 query 会返回 no_active_version，并在排除轨迹中展示原因。

4. 新增/调整条件
   每条条件必须带：field（字段名）、type（合同硬约束/内部附加条件/客户口径）、
   tier（必备/偏好）、text（来源原文）。答案的"来源"列直接引用这四项。

5. 调整不开放字段
   版本的 restricted_fields 列表维护"不开放"字段；当前为：客户内部筛选标准、财务预算。

6. 失败排查（失败可解释）
   brief_not_found   → 岗位代号写错，看 reason 里列出的库内代号
   no_active_version → 全部版本被排除，看 excluded_versions 里的逐条原因
   field_not_open    → 权限边界，不是 bug；确需访问走客户口径流程
   unknown_user      → as-user 不在 USERS 权威表

7. 责任分工见 raci 命令；验收四条见 README.md。
"""


# ---------------------------------------------------------------- 页面版（serve）

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>招聘需求简报 · 最小集查询 Demo</title>
<style>
  :root{--brand:#1f3d2b;--ink:#1f2937;--muted:#6b7280;--line:#e5e3da;--bg:#f7f6f1;--card:#fff;--amber:#b45309;--red:#a32d2d;--green:#0F6E56;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);padding:28px 16px;line-height:1.7;}
  .wrap{max-width:860px;margin:0 auto;}
  h1{font-size:20px;color:var(--brand);margin-bottom:2px;}
  .sub{font-size:13px;color:var(--muted);margin-bottom:20px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 24px;margin-bottom:16px;}
  label{font-size:13px;color:var(--brand);font-weight:600;display:block;margin:10px 0 4px;}
  select,input[type=text]{border:1px solid #d6d3c8;border-radius:8px;padding:8px 10px;font-size:14px;background:#fbfaf6;}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;}
  button{border:1px solid var(--brand);background:var(--brand);color:#fff;border-radius:9px;padding:8px 18px;font-size:14px;cursor:pointer;}
  button.ghost{background:transparent;color:var(--brand);}
  button.mini{padding:4px 12px;font-size:12px;border-radius:7px;}
  .chip{display:inline-block;border:1px solid #d6d3c8;background:#fbfaf6;color:#4b5563;border-radius:7px;padding:3px 10px;font-size:12px;cursor:pointer;margin:2px 4px 2px 0;}
  h2{font-size:15px;color:var(--brand);margin:4px 0 10px;}
  .ans{font-size:15px;margin-bottom:12px;}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
  @media(max-width:640px){.cols{grid-template-columns:1fr;}}
  .col{border:1px solid var(--line);border-radius:10px;padding:12px 14px;}
  .col h3{font-size:13px;margin-bottom:8px;}
  .col.must h3{color:#a32d2d;}
  .col.pref h3{color:var(--green);}
  .item{border-top:1px dashed var(--line);padding:8px 0;}
  .item:first-of-type{border-top:none;}
  .req{font-size:14px;}
  .src{font-size:12px;color:var(--muted);margin-top:2px;}
  .src b{color:var(--brand);}
  .note{font-size:12px;color:var(--muted);margin-top:10px;}
  .warn{background:#FAEEDA;border:1px solid #EF9F27;border-radius:8px;padding:8px 12px;font-size:13px;color:var(--amber);margin:10px 0;}
  .err{background:#FCEBEB;border:1px solid #E24B4A;border-radius:8px;padding:10px 14px;font-size:14px;color:var(--red);}
  .err code{font-size:12px;}
  table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px;}
  th{background:#eef4ef;color:var(--brand);text-align:left;padding:7px 10px;border:1px solid var(--line);}
  td{padding:7px 10px;border:1px solid var(--line);}
  .audit{font-size:12px;color:var(--muted);margin-top:12px;border-top:1px solid var(--line);padding-top:10px;}
  .foot{font-size:12px;color:var(--muted);margin-top:8px;}
  .tag{display:inline-block;background:#eef4ef;border-radius:5px;padding:1px 7px;font-size:11px;color:#0F6E56;margin-right:5px;}
</style>
</head>
<body>
<div class="wrap">
  <h1>招聘需求简报 · 最小集查询 Demo</h1>
  <div class="sub">任务：林亦舟查当前简报「必备条件 / 偏好条件」｜输出：简短答案 + 来源原文（版本号 + 字段）｜合成演练数据</div>

  <div class="card">
    <div class="row">
      <div>
        <label>身份（模拟）</label>
        <select id="user">
          <option value="E001">E001 · 林亦舟（招聘与用工服务顾问）</option>
          <option value="E002">E002 · 同事甲（招聘与用工服务顾问）</option>
        </select>
      </div>
      <div>
        <label>岗位代号</label>
        <input type="text" id="job" value="J-2026-001" style="width:150px">
      </div>
      <div>
        <label>&nbsp;</label>
        <button onclick="doQuery()">查必备 / 偏好</button>
      </div>
    </div>
    <div style="margin-top:8px">
      <span class="chip" onclick="setJob('J-2026-001')">J-2026-001 数据工程师（主场景）</span>
      <span class="chip" onclick="setJob('J-2026-002')">J-2026-002 Java开发（同事批次）</span>
      <span class="chip" onclick="setJob('J-2026-003')">J-2026-003 测试（已作废）</span>
      <span class="chip" onclick="setJob('J-2026-004')">J-2026-004 产品（未确认）</span>
    </div>
    <div class="row" style="margin-top:12px">
      <div>
        <label>字段试探（试试输入：财务预算）</label>
        <input type="text" id="field" placeholder="字段名" style="width:150px">
      </div>
      <div>
        <label>&nbsp;</label>
        <button class="ghost" onclick="doField()">试探该字段</button>
      </div>
      <div>
        <label>&nbsp;</label>
        <button class="ghost" onclick="doStatus()">我的批次状态（只读）</button>
      </div>
      <div>
        <label>&nbsp;</label>
        <button class="ghost" onclick="doRaci()">角色分工</button>
      </div>
    </div>
  </div>

  <div class="card" id="result">
    <h2>结果</h2>
    <div class="foot">点上面任意按钮开始。建议顺序：查必备/偏好 → 试探「财务预算」→ 我的批次状态 → 换 E002 再查一次状态。</div>
  </div>

  <div class="foot">验收四条：来源支持答案（每条带版本号+字段）· 权限正确（不开放字段/他人批次拦截）· 失败可解释（错误码+原因）· 能按手册维护（CLI：<code>python3 brief_demo.py manual</code>）</div>
</div>

<script>
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function setJob(j){document.getElementById('job').value=j;doQuery();}
async function call(url){const r=await fetch(url);return r.json();}
function itemHTML(c){return '<div class="item"><div class="req">'+esc(c['要求'])+'</div><div class="src">来源：<b>'+esc(c['来源'])+'</b></div></div>';}
function auditHTML(d){var a=d.audit||{};var ex=(a.excluded_versions||[]).map(function(e){return esc(e.version)+'（'+esc(e.reason)+'）';}).join('；');var h='<div class="audit">采用版本：'+esc(a.used_version||'-')+' · 确认状态：'+(a.confirmed?'已确认':'未确认')+' · 写回：'+(a.write_back?'是':'否')+' · 外部消息：'+(a.external_message?'是':'否');if(ex){h+='；排除轨迹：'+ex;}h+='</div>';return h;}
function showQuery(d){
  var el=document.getElementById('result');
  if(d.error){el.innerHTML='<h2>查询失败（可解释）</h2><div class="err"><code>'+esc(d.error)+'</code><br>'+esc(d.reason)+'</div>';return;}
  var h='<h2>'+esc(d.job.code)+' · '+esc(d.job.title)+'</h2><div class="ans">'+esc(d.answer_text)+'</div>';
  if(d.warning){h+='<div class="warn">'+esc(d.warning)+'</div>';}
  h+='<div class="cols"><div class="col must"><h3>必备条件</h3>'+(d.answer['必备条件'].map(itemHTML).join('')||'<div class="note">（空）</div>')+'</div>'
   +'<div class="col pref"><h3>偏好条件</h3>'+(d.answer['偏好条件'].map(itemHTML).join('')||'<div class="note">（空）</div>')+'</div></div>';
  if(d.not_open&&d.not_open.length){h+='<div class="note">不开放字段（资料边界）：'+d.not_open.map(esc).join('、')+'</div>';}
  h+=auditHTML(d);
  el.innerHTML=h;
}
function showStatus(d){
  var el=document.getElementById('result');
  if(d.error){el.innerHTML='<div class="err"><code>'+esc(d.error)+'</code><br>'+esc(d.reason)+'</div>';return;}
  var rows=d.batches.map(function(b){return '<tr><td>'+esc(b.job_code)+'</td><td>'+esc(b.title)+'</td><td>'+esc(b['当前版本']||'-（无有效版本）')+'</td><td>'+esc(b['确认状态'])+'</td><td>'+esc(b['有效期至']||'-')+'</td></tr>';}).join('');
  el.innerHTML='<h2>我的批次状态（只读）</h2><div class="note" style="margin:0 0 6px">'+esc(d.as_user)+' · '+esc(d.note)+'</div>'
   +'<table><tr><th>岗位代号</th><th>岗位</th><th>当前版本</th><th>确认状态</th><th>有效期至</th></tr>'+(rows||'<tr><td colspan=5>（无负责批次）</td></tr>')+'</table>';
}
function showRaci(d){
  var el=document.getElementById('result');
  var rows=Object.keys(d['角色分工']).map(function(k){return '<tr><td><b>'+esc(k)+'</b></td><td>'+esc(d['角色分工'][k])+'</td></tr>';}).join('');
  el.innerHTML='<h2>角色分工</h2><table>'+rows+'</table>';
}
function doQuery(){call('/api/query?job='+encodeURIComponent(document.getElementById('job').value)+'&as_user='+document.getElementById('user').value).then(showQuery);}
function doField(){var f=document.getElementById('field').value.trim();if(!f){alert('请输入字段名，例如：财务预算');return;}call('/api/query?job='+encodeURIComponent(document.getElementById('job').value)+'&as_user='+document.getElementById('user').value+'&field='+encodeURIComponent(f)).then(showQuery);}
function doStatus(){call('/api/status?as_user='+document.getElementById('user').value).then(showStatus);}
function doRaci(){call('/api/raci').then(showRaci);}
</script>
</body>
</html>"""


def cmd_serve(port=8010):
    """起本地页面版：浏览器打开 http://127.0.0.1:<port>"""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse, parse_qs

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                self._send(200, PAGE, "text/html; charset=utf-8")
                return
            q = parse_qs(u.query)
            if u.path == "/api/query":
                job = q.get("job", [""])[0].strip()
                field = (q.get("field", [""])[0].strip() or None)
                user = q.get("as_user", ["E001"])[0]
                self._send(200, json.dumps(cmd_query(job, user, field), ensure_ascii=False))
            elif u.path == "/api/status":
                self._send(200, json.dumps(cmd_status(q.get("as_user", ["E001"])[0]), ensure_ascii=False))
            elif u.path == "/api/raci":
                self._send(200, json.dumps({"角色分工": RACI}, ensure_ascii=False))
            elif u.path == "/api/jobs":
                self._send(200, json.dumps(
                    [{"code": b["job_code"], "title": b["title"]} for b in BRIEFS], ensure_ascii=False))
            else:
                self._send(404, json.dumps({"error": "not_found"}, ensure_ascii=False))

        def log_message(self, *args):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("页面版已启动：http://127.0.0.1:%d  （Ctrl+C 停止）" % port)
    srv.serve_forever()


# ---------------------------------------------------------------- CLI

def main():
    p = argparse.ArgumentParser(description="招聘需求简报最小集查询 Demo")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="查当前有效简报的必备/偏好条件")
    q.add_argument("job_code")
    q.add_argument("--as-user", default="E001")
    q.add_argument("--field", default=None, help="只看某个字段（可用于试探不开放字段）")

    s = sub.add_parser("status", help="只读查本人批次确认状态与版本")
    s.add_argument("--as-user", default="E001")

    v = sub.add_parser("serve", help="启动页面版（浏览器访问）")
    v.add_argument("--port", type=int, default=8010)

    sub.add_parser("raci", help="角色分工")
    sub.add_parser("manual", help="维护手册")
    sub.add_parser("demo", help="一键跑全部场景")

    a = p.parse_args()

    if a.cmd == "query":
        result = cmd_query(a.job_code, a.as_user, a.field)
    elif a.cmd == "status":
        result = cmd_status(a.as_user)
    elif a.cmd == "serve":
        cmd_serve(a.port)
        return
    elif a.cmd == "raci":
        result = {"项目": "招聘需求澄清与面试协同 · 最小集", "角色分工": RACI}
    elif a.cmd == "manual":
        print(MANUAL)
        return
    elif a.cmd == "demo":
        scenarios = [
            ("场景1 主任务：林亦舟查 J-2026-001 必备/偏好", lambda: cmd_query("J-2026-001", "E001")),
            ("场景2 旧版本被排除、来源带版本号+字段", lambda: cmd_query("J-2026-001", "E001")["audit"]),
            ("场景3 试探不开放字段（失败可解释）", lambda: cmd_query("J-2026-001", "E001", field="财务预算")),
            ("场景4 只读查本人批次（J-2026-002 是同事的，不可见）", lambda: cmd_status("E001")),
            ("场景5 换同事查（只能看到自己的）", lambda: cmd_status("E002")),
            ("场景6 只有作废版本（失败可解释）", lambda: cmd_query("J-2026-003", "E001")),
            ("场景7 有效版本但未确认（预警不静默）", lambda: cmd_query("J-2026-004", "E001")),
        ]
        for title, fn in scenarios:
            print("===== %s =====" % title)
            print(json.dumps(fn(), ensure_ascii=False, indent=2))
            print()
        return
    else:
        result = {}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if isinstance(result, dict) and "error" in result else 0)


if __name__ == "__main__":
    main()
