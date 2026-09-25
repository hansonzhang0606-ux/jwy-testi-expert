# -*- coding: utf-8 -*-
"""用例构造器参数预检（生成 .xmind 前先跑一遍）

背景：C2(条件, 预期) 只接受 2 个参数，C3(条件, 数据, 预期) 接受 3 个。
手工写用例树时极易把 3 参数的用例误写成 C2()，直到运行期才报
TypeError: C2() takes 2 positional arguments but 3 were given。

用法
----
    # 只检查（有问题退出码 1）
    python lint_case_args.py gen_xmind.py

    # 自动修复：把 3 参数的 C2( 改写成 C3(
    python lint_case_args.py gen_xmind.py --fix
"""
import ast
import io
import sys


def lint(path, fix=False):
    src = io.open(path, encoding="utf-8").read()
    lines = src.split("\n")
    tree = ast.parse(src)

    expect = {"C2": 2, "C3": 3, "TC": 3}
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = getattr(node.func, "id", "")
            if fn in expect and len(node.args) != expect[fn]:
                bad.append((node.lineno, fn, len(node.args), expect[fn]))

    if not bad:
        print("OK: C2/C3/TC 参数个数全部正确")
        return 0

    for ln, fn, got, want in bad:
        print(f"L{ln}: {fn}() 传入 {got} 个参数，应为 {want} 个")

    if fix:
        fixed = set()
        for ln, fn, got, want in bad:
            if fn == "C2" and got == 3 and ln not in fixed:
                i = ln - 1
                if "C2(" in lines[i]:
                    lines[i] = lines[i].replace("C2(", "C3(", 1)
                    fixed.add(ln)
        io.open(path, "w", encoding="utf-8").write("\n".join(lines))
        print(f"已自动修复 {len(fixed)} 处（C2 三参数 -> C3）")
        # 其余类型（如 2 参数的 C3）需人工判断，保持退出码 1
        remain = [b for b in bad if b[0] not in fixed]
        return 1 if remain else 0
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(lint(sys.argv[1], fix="--fix" in sys.argv))
