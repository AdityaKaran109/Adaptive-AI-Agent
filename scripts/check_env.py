"""Verify the local stack before building anything on top of it.

Checks, in order: Ollama is up with the chat and embedding models, Oracle accepts
a connection, AI Vector Search works, and SQL property graphs can be created.

    .venv\\Scripts\\python.exe scripts\\check_env.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

OK, BAD = "[ ok ]", "[fail]"
failures: list[str] = []


def report(name: str, ok: bool, detail: str = "") -> None:
    print(f"{OK if ok else BAD} {name}{': ' + detail if detail else ''}")
    if not ok:
        failures.append(name)


def check_ollama() -> None:
    import json
    import urllib.error
    import urllib.request

    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    chat = os.environ.get("OLLAMA_MODEL", "")
    embed = os.environ.get("OLLAMA_EMBED_MODEL", "")

    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=10) as r:
            tags = {m["name"] for m in json.load(r)["models"]}
    except (urllib.error.URLError, OSError) as exc:
        report("ollama reachable", False, f"{host} ({exc})")
        return
    report("ollama reachable", True, host)

    for label, model in (("chat model", chat), ("embed model", embed)):
        # Ollama reports ":latest" explicitly; a bare name should still match.
        found = model in tags or f"{model}:latest" in tags
        report(f"{label} present", found, model or "<unset>")

    if embed in tags or f"{embed}:latest" in tags:
        body = json.dumps({"model": embed, "prompt": "dimension probe"}).encode()
        req = urllib.request.Request(
            f"{host}/api/embeddings", data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                dims = len(json.load(r)["embedding"])
            report("embedding dimension", dims == 768, f"{dims} (expected 768)")
        except (urllib.error.URLError, OSError, KeyError) as exc:
            report("embedding dimension", False, str(exc))


def check_oracle() -> None:
    try:
        import oracledb
    except ImportError:
        report("oracledb installed", False, "pip install oracledb")
        return

    user = os.environ.get("ORACLE_USER", "")
    password = os.environ.get("ORACLE_PASSWORD", "")
    dsn = os.environ.get("ORACLE_DSN", "")
    if not all((user, password, dsn)):
        report("oracle env vars", False, "set ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN")
        return

    try:
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
    except oracledb.Error as exc:
        report("oracle connect", False, f"{dsn} ({exc})")
        return

    with conn:
        cur = conn.cursor()
        version = cur.execute("select banner_full from v$version").fetchone()[0]
        report("oracle connect", True, version.splitlines()[0])

        # AI Vector Search: the VECTOR type and a distance operator.
        try:
            cur.execute("create table vec_probe (id number, v vector(768, float32))")
            cur.execute(
                "insert into vec_probe values (1, to_vector(:v))",
                v="[" + ",".join(["0.1"] * 768) + "]",
            )
            dist = cur.execute(
                "select vector_distance(v, to_vector(:v), cosine) from vec_probe",
                v="[" + ",".join(["0.1"] * 768) + "]",
            ).fetchone()[0]
            report("vector search", abs(dist) < 1e-3, f"cosine distance {dist:.6f}")
        except oracledb.Error as exc:
            report("vector search", False, str(exc))
        finally:
            cur.execute("begin execute immediate 'drop table vec_probe'; exception when others then null; end;")

        # SQL property graphs: the Lesson 5 requirement.
        try:
            cur.execute("create table pg_nodes (id number primary key, name varchar2(64))")
            cur.execute(
                "create table pg_edges (src number, dst number,"
                " constraint pg_e_s foreign key (src) references pg_nodes (id),"
                " constraint pg_e_d foreign key (dst) references pg_nodes (id))"
            )
            cur.execute(
                "create property graph pg_probe"
                " vertex tables (pg_nodes key (id) label n properties (name))"
                " edge tables (pg_edges key (src, dst)"
                "   source key (src) references pg_nodes (id)"
                "   destination key (dst) references pg_nodes (id) label e)"
            )
            report("property graph", True, "CREATE PROPERTY GRAPH accepted")
        except oracledb.Error as exc:
            report("property graph", False, str(exc))
        finally:
            for stmt in ("drop property graph pg_probe", "drop table pg_edges", "drop table pg_nodes"):
                cur.execute(f"begin execute immediate '{stmt}'; exception when others then null; end;")


if __name__ == "__main__":
    print("--- ollama ---")
    check_ollama()
    print("--- oracle ---")
    check_oracle()
    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        sys.exit(1)
    print("environment ready")
