"""Generate a plate drawing with the local Codex CLI's built-in image_gen tool.

Usage:
  python codex_gen.py --prompt-file prompt.txt --out work/raw.png [--count 3] [--ref old_plate.png]

Each run starts one non-interactive `codex exec` session (ChatGPT login, no API key needed),
asks it to call image_gen exactly once, then copies the new image out of
$CODEX_HOME/generated_images/<thread id>/ to --out. With --count N the files are
raw-1.png, raw-2.png, ... next to --out.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
GEN_DIR = CODEX_HOME / "generated_images"
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}

INSTRUCTION = """Use the built-in image_gen tool exactly once to generate ONE new image from the prompt below.
- Portrait orientation, as close to 3:4 as the tool allows.
- If reference images are attached, use them only as style references (line quality, palette, layout), not as an edit target.
- Do not run shell commands, do not write or edit any files, do not generate extra variants.
- After the image is generated, reply with the single word: done

PROMPT:
{prompt}
"""


def find_codex():
    exe = shutil.which("codex")
    if not exe:
        sys.exit("codex CLI not found on PATH")
    return exe


def new_images(since, thread_id, event_paths):
    # 1. paths mentioned in the JSON events, 2. the thread's folder, 3. anything newer than `since`
    hits = [p for p in event_paths if p.is_file() and p.suffix.lower() in IMG_EXT]
    if not hits and thread_id and (GEN_DIR / thread_id).is_dir():
        hits = [p for p in (GEN_DIR / thread_id).iterdir() if p.suffix.lower() in IMG_EXT]
    if not hits and GEN_DIR.is_dir():
        hits = [p for p in GEN_DIR.rglob("*") if p.suffix.lower() in IMG_EXT and p.stat().st_mtime >= since]
    return sorted(set(hits), key=lambda p: p.stat().st_mtime)


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)


def run_once(codex, prompt, refs, workdir, timeout):
    cmd = [codex, "exec", "--skip-git-repo-check", "--json", "-s", "read-only", "-C", str(workdir)]
    for r in refs:
        cmd += ["-i", str(r)]
    since = time.time() - 1
    proc = subprocess.run(cmd, input=INSTRUCTION.format(prompt=prompt).encode("utf-8"),
                          capture_output=True, timeout=timeout)
    out = proc.stdout.decode("utf-8", "replace")
    thread_id, event_paths = None, []
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "thread.started":
            thread_id = ev.get("thread_id")
        event_paths += [Path(s) for s in walk_strings(ev) if Path(s).suffix.lower() in IMG_EXT and len(s) < 400]
    imgs = new_images(since, thread_id, event_paths)
    if proc.returncode != 0 or not imgs:
        tail = "\n".join((out + proc.stderr.decode("utf-8", "replace")).splitlines()[-25:])
        raise RuntimeError(f"codex exec returned {proc.returncode}, images found: {len(imgs)}\n{tail}")
    return imgs[-1], thread_id


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prompt", help="English image prompt")
    g.add_argument("--prompt-file", type=Path, help="UTF-8 text file holding the prompt")
    ap.add_argument("--out", type=Path, required=True, help="output image path, e.g. work/raw.png")
    ap.add_argument("--count", type=int, default=1, help="number of candidates (one codex session each)")
    ap.add_argument("--ref", type=Path, action="append", default=[], help="style reference image (repeatable)")
    ap.add_argument("--timeout", type=int, default=900, help="seconds per codex session")
    a = ap.parse_args()

    prompt = a.prompt if a.prompt else a.prompt_file.read_text(encoding="utf-8")
    for r in a.ref:
        if not r.is_file():
            sys.exit(f"reference image not found: {r}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    codex = find_codex()

    for i in range(1, a.count + 1):
        dst = a.out if a.count == 1 else a.out.with_name(f"{a.out.stem}-{i}{a.out.suffix}")
        t0 = time.time()
        src, tid = run_once(codex, prompt, a.ref, a.out.parent.resolve(), a.timeout)
        dst = dst.with_suffix(src.suffix)
        shutil.copy2(src, dst)
        print(f"[{i}/{a.count}] {dst}  <- {src}  ({time.time() - t0:.0f}s, thread {tid})")


if __name__ == "__main__":
    main()
