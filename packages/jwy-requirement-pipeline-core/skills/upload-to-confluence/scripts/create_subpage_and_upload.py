# -*- coding: utf-8 -*-
"""
upload-to-confluence 参考实现：季度页 -> 自动建/复需求子页 -> 上传需求文件。

用法示例：
  python create_subpage_and_upload.py \
      --quarter-id 97124877 \
      --dir "D:/需求/2026/8.27" \
      --prefix "【余萍】【TD-AI】"

说明：
  - 传入的 quarter-id 视为季度页；不在季度页正文上传，而是先在其下创建（或复用）需求子页。
  - 需求子页标题 = 所有（已加前缀的）文件名的「最长公共前缀」再 rstrip(" _-")。
  - 凭据从 ~/.workbuddy/mcp.json 读取，绝不硬编码、不打印 token。
"""
import argparse, json, os, base64, glob, re, warnings, urllib3, requests

warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)

EXTS = (".docx", ".xmind", ".xlsx", ".md", ".pdf", ".png", ".jpg")


def load_creds():
    cfg = json.load(open(os.path.expanduser(r"~/.workbuddy/mcp.json"), encoding="utf-8"))
    env = cfg["mcpServers"]["Confluence"]["env"]
    return env["CONFLUENCE_URL"].rstrip("/"), env["CONFLUENCE_USERNAME"], env["CONFLUENCE_API_TOKEN"]


SUFFIX_STRIP = ["_需求确认", "_分析报告", "_测试用例", "_测试分析", "_含疑问点", "_分析", "_测试脑图", "_接口脑图", "_DMP用例", "_代码分析"]
SEP = " _-."


def _clean(name):
    low = name.lower()
    for ext in EXTS:
        if low.endswith(ext):
            name = name[: -len(ext)]
            break
    for s in SUFFIX_STRIP:
        if name.endswith(s):
            name = name[: -len(s)]
    return name.rstrip(SEP)


def _strip_prefix(name, prefix):
    return name[len(prefix):] if prefix and name.startswith(prefix) else name


def _lcp(strs):
    """多个字符串的最长公共前缀（正确实现，非仅取 min/max）。"""
    if not strs:
        return ""
    s = strs[0]
    for t in strs[1:]:
        i = 0
        while i < len(s) and i < len(t) and s[i] == t[i]:
            i += 1
        s = s[:i]
        if not s:
            break
    return s


def derive_title(names, prefix=""):
    """需求子页标题推导。

    1) 先去掉用户指定的重命名前缀（如 【余萍】【TD-AI】）；
    2) 再去掉每个文件名自身前置的【…】标签（如【泾渭云20260728】），
       对「去标签后的剩余部分」求最长公共前缀并清掉已知后缀/扩展名；
    3) 若所有带标签的文件都含同一个前置【…】标签，则把它补回标题——
       解决「部分文件缺日期标签」导致公共前缀塌缩成空的问题。
    """
    if not names:
        raise SystemExit("没有可上传的文件")
    stripped = [_strip_prefix(n, prefix) for n in names]
    untagged, tags = [], []
    for s in stripped:
        m = re.match(r"^(【[^】]*】)(.*)$", s)
        if m:
            tags.append(m.group(1))
            untagged.append(m.group(2))
        else:
            tags.append(None)
            untagged.append(s)
    core = _clean(_lcp(untagged))
    real = [t for t in tags if t]
    if real and len(set(real)) == 1:
        return (prefix or "") + real[0] + core
    return (prefix or "") + core


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarter-id", type=int, required=True, help="季度页 pageId")
    ap.add_argument("--dir", help="待上传文件所在目录（取其中需求文件）")
    ap.add_argument("--files", nargs="*", help="显式指定文件列表")
    ap.add_argument("--prefix", default="", help="重命名前缀，如 【余萍】【TD-AI】")
    args = ap.parse_args()

    base, user, token = load_creds()
    auth = base64.b64encode(f"{user}:{token}".encode()).decode()
    H = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
    A = {"Authorization": f"Basic {auth}", "X-Atlassian-Token": "no-check"}

    # 1. 收集源文件
    if args.files:
        srcs = [f for f in args.files if os.path.isfile(f)]
    else:
        d = args.dir
        srcs = []
        for ext in EXTS:
            srcs += glob.glob(os.path.join(d, f"*{ext}"))
        # 排除暂存/中间产物
        srcs = [s for s in srcs if "_上传暂存" not in s]
    srcs = sorted(set(srcs))
    if not srcs:
        raise SystemExit("未找到任何待上传文件")
    print("源文件:")
    for s in srcs:
        print("  -", os.path.basename(s))

    # 2. 重命名（加前缀）到暂存目录
    stage = os.path.join(args.dir or os.path.dirname(srcs[0]), "_上传暂存")
    os.makedirs(stage, exist_ok=True)
    staged = []
    for s in srcs:
        name = os.path.basename(s)
        new_name = name if name.startswith(args.prefix) else (args.prefix + name)
        dst = os.path.join(stage, new_name)
        with open(s, "rb") as fsrc, open(dst, "wb") as fdst:
            fdst.write(fsrc.read())
        staged.append(dst)
    print("\n已生成带前缀命名副本:", stage)

    # 3. 推导需求子页标题
    title = derive_title([os.path.basename(f) for f in staged], args.prefix)
    print("需求子页标题:", title)

    # 4. 取季度页 space.key
    q = requests.get(f"{base}/rest/api/content/{args.quarter_id}",
                     params={"expand": "space"}, headers=H, verify=False, timeout=60).json()
    space_key = q["space"]["key"]
    print("space.key:", space_key)

    # 5. 幂等查/建子页
    sub_id = None
    cql = f'space={space_key} AND title="{title}" AND type=page'
    for item in requests.get(f"{base}/rest/api/content/search", params={"cql": cql},
                             headers=H, verify=False, timeout=60).json().get("results", []):
        anc = requests.get(f"{base}/rest/api/content/{item['id']}",
                           params={"expand": "ancestors"}, headers=H, verify=False, timeout=60).json()
        if args.quarter_id in [a["id"] for a in anc.get("ancestors", [])]:
            sub_id = item["id"]
            break
    if sub_id:
        print("复用已有子页 id:", sub_id)
        ver = requests.get(f"{base}/rest/api/content/{sub_id}", params={"expand": "version"},
                           headers=H, verify=False, timeout=60).json()["version"]["number"]
    else:
        init = "<p>本页由流水线 step5 自动创建，归档需求确认文档与测试用例脑图。</p>"
        res = requests.post(f"{base}/rest/api/content", headers=H, json={
            "type": "page", "title": title, "space": {"key": space_key},
            "ancestors": [{"id": args.quarter_id}],
            "body": {"storage": {"value": init, "representation": "storage"}},
        }, verify=False, timeout=120)
        res.raise_for_status()
        sub_id = res.json()["id"]
        ver = res.json()["version"]["number"]
        print("新建子页 id:", sub_id)

    # 6. 上传附件
    for f in staged:
        fn = os.path.basename(f)
        with open(f, "rb") as fh:
            r = requests.post(f"{base}/rest/api/content/{sub_id}/child/attachment",
                              headers=A, files={"file": (fn, fh, "application/octet-stream")},
                              verify=False, timeout=300)
        print(f"上传 {fn} -> HTTP {r.status_code}")
        r.raise_for_status()

    # 7. 更新子页正文（追加 ac:link）
    body = requests.get(f"{base}/rest/api/content/{sub_id}", params={"expand": "body.storage"},
                        headers=H, verify=False, timeout=60).json()["body"]["storage"]["value"]
    links = "<h2>附件</h2><ul>"
    for f in staged:
        fn = os.path.basename(f)
        links += (f'<li><ac:link><ri:attachment ri:filename="{fn}" />'
                  f'<ac:link-body>{fn}</ac:link-body></ac:link></li>')
    links += "</ul>"
    new_body = body + links
    upd = {"id": str(sub_id), "type": "page", "title": title,
           "version": {"number": ver + 1},
           "body": {"storage": {"value": new_body, "representation": "storage"}}}
    u = requests.put(f"{base}/rest/api/content/{sub_id}", headers=H, json=upd,
                     verify=False, timeout=120)
    print("更新子页正文 HTTP", u.status_code)
    u.raise_for_status()

    print("\n=== 完成 ===")
    print("子页 id:", sub_id)
    print("子页链接:", f"{base}/pages/viewpage.action?pageId={sub_id}")
    print("附件数:", len(staged))


if __name__ == "__main__":
    main()
