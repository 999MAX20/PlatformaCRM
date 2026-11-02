"""Offline synthetic producer for existing build_mobile_tasks semantics.

No Django/database/live API or host clock. PostgreSQL ascending NULLS LAST is
explicit fixture ordering, not a claim about all deployed database engines.
"""
import datetime as dt
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "contracts/fixtures"
now = dt.datetime.fromisoformat("2026-10-28T00:30:00+00:00")
zone = dt.timezone.utc
today = now.astimezone(zone).date()

def instant(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None

for business in [101, 202]:
    original = json.loads((root / f"tasks-{business}.json").read_text())
    rows = [dict(row, created_at="2026-10-27T00:00:00Z") for row in original["items"]]
    start = 3100 if business == 101 else 4100
    for i in range(65):
        rows.append(dict(id=start+i, title=f"Synthetic source-query Task {business}/{i}", status="open", priority="normal", due_at="2026-10-27T23:30:00Z", client_id=None, lead_id=None, deal_id=None, assignee_id=None, href=f"/app/tasks?task={start+i}", created_at="2026-10-27T00:00:00Z"))
    for offset, status, due in [(65,"open","2026-10-28T00:10:00Z"),(66,"done","2026-10-28T00:05:00Z"),(67,"cancelled","2026-10-28T00:05:00Z"),(68,"in_progress","2026-10-28T23:50:00Z"),(69,"open","2026-10-29T00:05:00Z")]:
        rows.append(dict(id=start+offset,title=f"Synthetic clock edge {offset}",status=status,priority="high",due_at=due,client_id=None,lead_id=None,deal_id=None,assignee_id=None,href=f"/app/tasks?task={start+offset}",created_at="2026-10-27T00:00:00Z"))
    # Stable passes implement the exact source order (priority is string order).
    rows.sort(key=lambda r:r["id"], reverse=True)
    rows.sort(key=lambda r:r["created_at"], reverse=True)
    rows.sort(key=lambda r:r["priority"], reverse=True)
    rows.sort(key=lambda r:(r["due_at"] is None, instant(r["due_at"]) or now))
    def wire(row): return {k:v for k,v in row.items() if k!="created_at"}
    queries = {}
    for status in ["", "open", "in_progress", "done", "cancelled"]+sorted({r["status"] for r in rows}-{"open","in_progress","done","cancelled"}):
        for due in ["", "today", "overdue"]:
            filtered = [r for r in rows if not status or r["status"]==status]
            if due=="today": filtered = [r for r in filtered if r["due_at"] and instant(r["due_at"]).astimezone(zone).date()==today]
            elif due=="overdue": filtered = [r for r in filtered if r["status"] not in ["done","cancelled"] and r["due_at"] and instant(r["due_at"])<now]
            active=[r for r in filtered if r["status"] not in ["done","cancelled"]]
            queries[status+"|"+due] = dict(business=business,generated_at="2026-10-28T00:30:00Z",limit=50,summary=dict(total=len(filtered),open=len(active),overdue=sum(bool(r["due_at"] and instant(r["due_at"])<now) for r in active),today=sum(bool(r["due_at"] and instant(r["due_at"]).astimezone(zone).date()==today) for r in active)),items=[wire(r) for r in filtered[:50]],payload_budget=dict(target_kb=100,max_items=50))
    profiles={}
    for row in rows:
        old=root/f"task-{business}-{row['id']}.json"
        profiles[str(row["id"])]=json.loads(old.read_text()) if old.exists() else dict(business=business,generated_at="2026-10-28T00:30:00Z",task=wire(row),details=dict(description="Synthetic source-query detail; no operation performed",appointment_id=None),comments=[],payload_budget=dict(target_kb=60,max_comments=5))
    data=dict(fixture_only=True,business=business,producer=dict(now="2026-10-28T00:30:00Z",timezone="UTC",database_order="PostgreSQL NULLS LAST ascending",source="apps/mobile/selectors.py372–407; this is a synthetic projection, not CURRENT acceptance"),catalogue=rows,queries=queries,profiles=profiles)
    target=root/f"task-query-source-{business}.json"
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
