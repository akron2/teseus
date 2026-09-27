"""Command-line bootstrap and local mock dialogue."""

import argparse
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from .engine import MockEngine
from .memory import cycle, propose, restore
from .persona import Persona
from .storage import Store

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "profiles" / "teseus-seed"
PERSONA_ID = "local-owner"


def default_data_dir() -> Path:
    configured = os.environ.get("HARNESS_DATA_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".local" / "share" / "teseus-harness"


def bootstrap(data_dir: Path, seed_teseus: bool = False) -> None:
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        data_dir.chmod(0o700)
    except OSError:
        pass
    persona_path = data_dir / "persona.json"
    if seed_teseus:
        persona = Persona.load(SEED_DIR / "persona.json")
        shutil.copyfile(SEED_DIR / "persona.json", persona_path)
    elif persona_path.exists():
        persona = Persona.load(persona_path)
    else:
        persona = Persona.neutral()
        persona_path.write_text(json.dumps(persona.as_dict(), indent=2) + "\n", encoding="utf-8")
    try:
        persona_path.chmod(0o600)
    except OSError:
        pass
    store = Store(data_dir / "harness.sqlite3")
    try:
        applied = store.migrate()
        store.save_persona(PERSONA_ID, persona)
        if seed_teseus:
            seeded = store.connection.execute(
                "SELECT 1 FROM memory_events WHERE reason='optional public seed installation' LIMIT 1"
            ).fetchone()
            if not seeded:
                items = json.loads((SEED_DIR / "seed-memory.json").read_text(encoding="utf-8"))
                for item in items:
                    memory_id = propose(store, item["body"], int(item["salience"]))
                    store.connection.execute(
                        "UPDATE memory_events SET reason='optional public seed installation' "
                        "WHERE memory_id=? AND action='proposed'",
                        (memory_id,),
                    )
                store.connection.commit()
    finally:
        store.close()
    print(f"Bootstrapped local state; migrations applied: {applied or 'none'}")


def run_dialogue(data_dir: Path, text: str, remember: str | None = None) -> str:
    if not text.strip():
        raise ValueError("dialogue text must not be empty")
    store = Store(data_dir / "harness.sqlite3")
    try:
        persona_data = store.load_persona(PERSONA_ID)
        if persona_data is None:
            raise RuntimeError("local state is not bootstrapped; run the bootstrap command first")
        conversation_id = str(uuid.uuid4())
        store.create_conversation(conversation_id, PERSONA_ID)
        store.add_message(conversation_id, "owner", text)
        reply = MockEngine().generate(text, str(persona_data["name"]))
        response = reply.text + "\n" + reply.initiative
        store.add_message(conversation_id, "assistant", response)
        if remember is not None:
            propose(store, remember)
        return response
    finally:
        store.close()


def run_demo(data_dir: Path) -> None:
    bootstrap(data_dir, seed_teseus=True)
    print(run_dialogue(data_dir, "SYNTHETIC_DIALOGUE_001: explore how a ship keeps a course."))
    store = Store(data_dir / "harness.sqlite3")
    try:
        propose(store, "SYNTHETIC_MEMORY_001: a useful course can be corrected.", 10)
        propose(store, "SYNTHETIC_MEMORY_002: not every passing detail needs to remain.", 2)
        result = cycle(store, limit=3)
        print(f"Memory selection: kept={len(result['kept'])}, forgotten={len(result['forgotten'])}")
        if result["forgotten"]:
            restore(store, result["forgotten"][0])
            print("Reversal journaled: one forgotten item restored.")
    finally:
        store.close()


def remove_seed(data_dir: Path) -> None:
    store = Store(data_dir / "harness.sqlite3")
    try:
        db = store.connection
        ids = [row[0] for row in db.execute(
            "SELECT DISTINCT memory_id FROM memory_events WHERE reason='optional public seed installation'"
        )]
        for memory_id in ids:
            db.execute("DELETE FROM memory_events WHERE memory_id=?", (memory_id,))
            db.execute("DELETE FROM memory_items WHERE id=?", (memory_id,))
        store.save_persona(PERSONA_ID, Persona.neutral())
        db.commit()
        (data_dir / "persona.json").unlink(missing_ok=True)
        (data_dir / "persona.json").write_text(
            json.dumps(Persona.neutral().as_dict(), indent=2) + "\n", encoding="utf-8"
        )
        try:
            (data_dir / "persona.json").chmod(0o600)
        except OSError:
            pass
        print(f"Optional seed removed; {len(ids)} seed memory item(s) deleted and neutral profile restored.")
    finally:
        store.close()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="harness", description="Local personal-agent harness")
    sub = root.add_subparsers(dest="command", required=True)
    boot = sub.add_parser("bootstrap", help="create local persona and SQLite state")
    boot.add_argument("--data-dir", type=Path, default=default_data_dir())
    boot.add_argument("--seed-teseus", action="store_true", help="install the removable public seed profile")
    talk = sub.add_parser("dialogue", help="run one deterministic mock turn")
    talk.add_argument("--data-dir", type=Path, default=default_data_dir())
    talk.add_argument("--text", default="SYNTHETIC_FIRST_DIALOGUE_001")
    talk.add_argument("--remember", help="explicitly propose this text for memory")
    memory = sub.add_parser("memory", help="select or restore memory")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    cycle_parser = memory_sub.add_parser("cycle", help="select active items and journal forgetting")
    cycle_parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    cycle_parser.add_argument("--limit", type=int, default=3)
    restore_parser = memory_sub.add_parser("restore", help="reverse a forgetting decision")
    restore_parser.add_argument("memory_id", type=int)
    restore_parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    demo = sub.add_parser("demo", help="run a synthetic end-to-end example")
    demo.add_argument("--data-dir", type=Path, default=Path(tempfile.gettempdir()) / f"harness-demo-{uuid.uuid4().hex[:8]}")
    seed = sub.add_parser("seed", help="manage the optional public seed profile")
    seed_sub = seed.add_subparsers(dest="seed_command", required=True)
    remove = seed_sub.add_parser("remove", help="remove installed seed memory and restore the neutral persona")
    remove.add_argument("--data-dir", type=Path, default=default_data_dir())
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "bootstrap":
        bootstrap(args.data_dir, args.seed_teseus)
    elif args.command == "dialogue":
        print(run_dialogue(args.data_dir, args.text, args.remember))
    elif args.command == "demo":
        run_demo(args.data_dir)
    elif args.command == "seed":
        remove_seed(args.data_dir)
    elif args.command == "memory":
        store = Store(args.data_dir / "harness.sqlite3")
        try:
            if args.memory_command == "cycle":
                result = cycle(store, args.limit)
                print(f"Selection complete: kept={len(result['kept'])}, forgotten={len(result['forgotten'])}")
            else:
                restore(store, args.memory_id)
                print("Memory item restored and journaled.")
        finally:
            store.close()


if __name__ == "__main__":
    main()
