"""Verified data transfer into a freshly migrated, empty CRM PostgreSQL database."""
from datetime import date, datetime, timezone
from decimal import Decimal
from ipaddress import ip_address, ip_network
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import UUID

from psycopg import sql


def convert(value, kind):
    if value is None:
        return None
    if kind == "bool":
        if value not in (0, 1, False, True):
            raise ValueError("Invalid SQLite boolean")
        return bool(value)
    return value


def canonical(value, kind, scale):
    if value is None:
        return None
    if kind in {"json", "jsonb"}:
        return json.loads(value) if isinstance(value, str) else value
    if kind == "uuid":
        return str(UUID(str(value)))
    if kind == "inet":
        return str(ip_address(str(value)))
    if kind == "cidr":
        return str(ip_network(str(value)))
    if kind == "numeric":
        number = Decimal(str(value))
        if scale is not None:
            number = number.quantize(Decimal(1).scaleb(-scale))
        return str(number)
    if kind in {"timestamp", "timestamptz"}:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        if kind == "timestamptz":
            result = result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
        return result.isoformat(timespec="microseconds")
    if kind in {"date", "time"}:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if kind == "bool":
        return convert(value, kind)
    if kind == "bytea":
        return bytes(value).hex()
    return value


def layout(pg):
    rows = pg.execute("""SELECT table_name,column_name,udt_name,numeric_scale
        FROM information_schema.columns WHERE table_schema='public'
        ORDER BY table_name,ordinal_position""").fetchall()
    tables = {}
    for table, column, kind, scale in rows:
        tables.setdefault(table, []).append((column, kind, scale))
    return tables


def digest(rows, columns):
    result = hashlib.sha256()
    count = 0
    for row in rows:
        normalized = [canonical(v, kind, scale) for v, (_, kind, scale) in zip(row, columns)]
        result.update(json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
        count += 1
    return {"rows": count, "sha256": result.hexdigest()}


def primary_keys(pg):
    rows = pg.execute("""SELECT tc.table_name,kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema
        WHERE tc.table_schema='public' AND tc.constraint_type='PRIMARY KEY'
        ORDER BY tc.table_name,kcu.ordinal_position""").fetchall()
    keys = {}
    for table, name in rows:
        keys.setdefault(table, []).append(name)
    return keys


def compare(source, pg):
    result = {}
    keys = primary_keys(pg)
    for table, columns in layout(pg).items():
        names = [c[0] for c in columns]
        query = sql.SQL("SELECT {} FROM {} ORDER BY {}").format(
            sql.SQL(",").join(map(sql.Identifier, names)), sql.Identifier(table),
            sql.SQL(",").join(map(sql.Identifier, keys[table])))
        expected = digest(source.execute(query.as_string(pg)), columns)
        actual = digest(pg.execute(query), columns)
        if expected != actual:
            raise RuntimeError(f"Data mismatch in {table}: source={expected['rows']}, target={actual['rows']}")
        result[table] = expected
    return result


def transfer(source_path, pg):
    source = sqlite3.connect(Path(source_path).resolve().as_uri() + "?mode=ro", uri=True)
    source.execute("PRAGMA query_only=ON")
    source.execute("BEGIN")
    try:
        if source.execute("PRAGMA integrity_check").fetchall() != [("ok",)] or source.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Source SQLite integrity failed")
        tables = layout(pg)
        keys = primary_keys(pg)
        source_tables = {r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if source_tables != set(tables):
            raise RuntimeError("Source and target tables differ")
        for table in ("businesses_business", "accounts_user", "clients_client"):
            if pg.execute(sql.SQL("SELECT EXISTS(SELECT 1 FROM {})").format(sql.Identifier(table))).fetchone()[0]:
                raise RuntimeError("Transfer refuses a populated destination")
        source_migrations = set(source.execute("SELECT app,name FROM django_migrations"))
        if source_migrations != set(pg.execute("SELECT app,name FROM django_migrations").fetchall()):
            raise RuntimeError("Source and target migration histories differ")
        with pg.transaction():
            pg.execute(sql.SQL("TRUNCATE {} RESTART IDENTITY").format(sql.SQL(",").join(map(sql.Identifier, tables))))
            pg.execute("SET CONSTRAINTS ALL DEFERRED")
            for table, columns in tables.items():
                names = [c[0] for c in columns]
                if set(names) != {r[1] for r in source.execute(f'PRAGMA table_info("{table}")')}:
                    raise RuntimeError(f"Columns differ in {table}")
                query = sql.SQL("SELECT {} FROM {}").format(sql.SQL(",").join(map(sql.Identifier, names)), sql.Identifier(table))
                with pg.cursor().copy(sql.SQL("COPY {} ({}) FROM STDIN").format(sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, names)))) as copy:
                    for row in source.execute(query.as_string(pg)):
                        copy.write_row([convert(v, kind) for v, (_, kind, _) in zip(row, columns)])
                for key in keys[table]:
                    sequence = pg.execute("SELECT pg_get_serial_sequence(%s,%s)", (table, key)).fetchone()[0]
                    if sequence:
                        maximum = pg.execute(sql.SQL("SELECT MAX({}) FROM {}").format(sql.Identifier(key), sql.Identifier(table))).fetchone()[0]
                        pg.execute("SELECT setval(%s,%s,%s)", (sequence, maximum or 1, maximum is not None))
            pg.execute("SET CONSTRAINTS ALL IMMEDIATE")
            result = compare(source, pg)
        return result
    finally:
        source.close()
