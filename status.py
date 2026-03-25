"""查看群数据库状态"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "group_db.json")

if not os.path.isfile(DB):
    print("  群数据库不存在，请先扫码进群。")
else:
    with open(DB, "r", encoding="utf-8") as f:
        db = json.load(f)
    gs = db.get("groups", [])
    active = [g for g in gs if g.get("status") == "active"]
    skipped = [g for g in gs if g.get("status") == "skipped"]
    print(f"  群总数: {len(gs)}")
    print(f"  活跃群: {len(active)}")
    print(f"  已跳过: {len(skipped)}")
    print()
    for g in active[:20]:
        name = g.get("group_name", "?")
        ns = g.get("next_send", "未设定")
        sc = g.get("send_count", 0)
        print(f"    {name}  |  下次发送: {ns}  |  已发: {sc}次")
    if len(active) > 20:
        print(f"    ... 共 {len(active)} 个活跃群")
