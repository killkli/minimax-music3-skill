#!/usr/bin/env python3
"""Run MiniMax Music 3 jobs through the Google Colab CLI."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "assets" / "MiniMax_Music3_Colab.ipynb"
DEFAULT_TIMEOUT = 10_800
MAX_SEED = (1 << 64) - 1
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class RunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class Job:
    job_id: str
    lyrics: str
    music_description: str
    duration_seconds: int
    seed: int

    @property
    def output_name(self) -> str:
        return f"{self.job_id}_seed{self.seed}.wav"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_jobs(manifest_path: Path) -> list[Job]:
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"Cannot read UTF-8 JSON manifest: {manifest_path}") from error

    if not isinstance(document, dict) or not isinstance(document.get("jobs"), list):
        raise RunnerError("The manifest must be a JSON object with a 'jobs' array.")
    if not document["jobs"]:
        raise RunnerError("The manifest must contain at least one job.")

    jobs: list[Job] = []
    seen_ids: set[str] = set()
    for index, raw_job in enumerate(document["jobs"], start=1):
        where = f"jobs[{index - 1}]"
        if not isinstance(raw_job, dict):
            raise RunnerError(f"{where} must be an object.")

        job_id = raw_job.get("id")
        lyrics = raw_job.get("lyrics")
        description = raw_job.get("music_description")
        duration = raw_job.get("duration_seconds", 10)
        seed = raw_job.get("seed", 7)

        if not isinstance(job_id, str) or not ID_PATTERN.fullmatch(job_id) or job_id in {".", ".."}:
            raise RunnerError(
                f"{where}.id must use 1–64 letters, digits, dots, underscores, or hyphens, "
                "and start with a letter or digit."
            )
        if job_id in seen_ids:
            raise RunnerError(f"Duplicate job id: {job_id}")
        seen_ids.add(job_id)
        if not isinstance(lyrics, str) or not lyrics.strip():
            raise RunnerError(f"{where}.lyrics must be non-empty text.")
        if not isinstance(description, str) or not description.strip():
            raise RunnerError(f"{where}.music_description must be non-empty text.")
        if type(duration) is not int or not 1 <= duration <= 300:
            raise RunnerError(f"{where}.duration_seconds must be an integer from 1 to 300 when provided.")
        if type(seed) is not int or not 0 <= seed <= MAX_SEED:
            raise RunnerError(f"{where}.seed must be an integer from 0 to {MAX_SEED}.")

        jobs.append(Job(job_id, lyrics, description, duration, seed))
    return jobs


def notebook_code_cells(path: Path) -> tuple[str, str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"Cannot read notebook: {path}") from error
    if not isinstance(document, dict) or not isinstance(document.get("cells"), list):
        raise RunnerError("The bundled notebook is missing its cell list.")

    found: dict[str, str] = {}
    for cell in document["cells"]:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        cell_id = cell.get("id") or cell.get("metadata", {}).get("id")
        if cell_id in {"music3-setup", "music3-generate"}:
            source = cell.get("source", "")
            found[cell_id] = "".join(source) if isinstance(source, list) else str(source)

    if set(found) != {"music3-setup", "music3-generate"}:
        raise RunnerError(
            "The bundled notebook must contain the 'music3-setup' and 'music3-generate' code cells."
        )
    try:
        ast.parse(found["music3-setup"])
        ast.parse(found["music3-generate"])
    except SyntaxError as error:
        raise RunnerError(f"The bundled notebook contains invalid Python in line {error.lineno}.") from error
    return found["music3-setup"], found["music3-generate"]


def assignment_names(statement: ast.stmt) -> set[str]:
    if isinstance(statement, ast.Assign):
        targets = statement.targets
    elif isinstance(statement, ast.AnnAssign):
        targets = [statement.target]
    else:
        return set()
    return {node.id for target in targets for node in ast.walk(target) if isinstance(node, ast.Name)}


def call_name(node: ast.Call) -> str | None:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
        return f"{function.value.id}.{function.attr}"
    return None


def echoes_prompt(node: ast.Call) -> bool:
    if call_name(node) != "print":
        return False
    return any(
        isinstance(child, ast.Constant)
        and isinstance(child.value, str)
        and ("歌詞" in child.value or "音樂描述" in child.value)
        for child in ast.walk(node)
    )


def job_code(template: str, job: Job) -> str:
    tree = ast.parse(template)
    values: dict[str, Any] = {
        "lyrics": job.lyrics,
        "music_description": job.music_description,
        "duration_seconds": job.duration_seconds,
        "seed": job.seed,
    }
    assignment_counts = {name: 0 for name in values}
    replacements: dict[int, tuple[int, str]] = {}
    removed_lines: set[int] = set()

    for statement in tree.body:
        names = assignment_names(statement)
        assigned = names & values.keys()
        if assigned:
            if len(assigned) != 1 or not hasattr(statement, "end_lineno"):
                raise RunnerError("The generation cell has an unsupported input assignment layout.")
            name = next(iter(assigned))
            assignment_counts[name] += 1
            if assignment_counts[name] > 1:
                raise RunnerError(f"The generation cell assigns '{name}' more than once.")
            literal = json.dumps(values[name], ensure_ascii=True)
            replacements[statement.lineno] = (statement.end_lineno or statement.lineno, f"{name} = {literal}\n")
            continue

        if isinstance(statement, ast.ImportFrom) and statement.module in {"google.colab", "IPython.display"}:
            removed_lines.update(range(statement.lineno, (statement.end_lineno or statement.lineno) + 1))
            continue

        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            if call_name(statement.value) in {"display", "files.download"} or echoes_prompt(statement.value):
                removed_lines.update(range(statement.lineno, (statement.end_lineno or statement.lineno) + 1))

    missing = sorted(name for name, count in assignment_counts.items() if count != 1)
    if missing:
        raise RunnerError(f"The generation cell is missing expected assignments: {', '.join(missing)}")

    source_lines = template.splitlines(keepends=True)
    result: list[str] = []
    line_number = 1
    while line_number <= len(source_lines):
        if line_number in replacements:
            end_line, replacement = replacements[line_number]
            result.append(replacement)
            line_number = end_line + 1
        elif line_number in removed_lines:
            line_number += 1
        else:
            result.append(source_lines[line_number - 1])
            line_number += 1
    rendered = "".join(result)
    try:
        ast.parse(rendered)
    except SyntaxError as error:
        raise RunnerError(f"Could not prepare generation cell at line {error.lineno}.") from error
    return rendered


def run_command(command: list[str], timeout: int, label: str) -> None:
    print(f"\n[{label}] {command[0]} {' '.join(command[1:])}", flush=True)
    try:
        result = subprocess.run(command, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise RunnerError(f"Colab {label} command timed out after {timeout} seconds.") from error
    if result.returncode != 0:
        raise RunnerError(f"Colab {label} command failed with exit code {result.returncode}.")


def inspect_wav(path: Path) -> dict[str, int | float]:
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            sample_rate = audio.getframerate()
            frames = audio.getnframes()
    except (OSError, wave.Error) as error:
        raise RunnerError(f"Downloaded output is not a readable WAV file: {path.name}") from error
    if channels != 2 or sample_width != 2 or sample_rate <= 0 or frames <= 0:
        raise RunnerError(
            f"Downloaded WAV must be non-empty 16-bit stereo audio; got "
            f"{channels} channels, {sample_width * 8}-bit, {sample_rate} Hz, {frames} frames."
        )
    return {"channels": channels, "sample_width_bytes": sample_width, "sample_rate": sample_rate,
            "frames": frames, "duration_seconds": round(frames / sample_rate, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate MiniMax Music 3 WAV files through a temporary Google Colab session."
    )
    parser.add_argument("--manifest", required=True, type=Path, help="UTF-8 JSON file containing a jobs array")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for downloaded WAV files and progress.json")
    parser.add_argument("--gpu", choices=("A100", "L4"), default="A100", help="Colab GPU; the bundled notebook requires BF16 support")
    parser.add_argument("--high-mem", action="store_true", help="Request high system RAM where Colab supports it")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per setup or song execution timeout in seconds")
    parser.add_argument("--provision-timeout", type=int, default=600, help="Colab session provisioning timeout in seconds")
    parser.add_argument("--progress", type=Path, help="Progress JSON path (defaults to OUTPUT_DIR/progress.json)")
    return parser


def run_batch(args: argparse.Namespace) -> int:
    if args.timeout < 1 or args.provision_timeout < 1:
        raise RunnerError("Timeout values must be positive.")

    jobs = load_jobs(args.manifest.expanduser().resolve())
    setup_code, generation_template = notebook_code_cells(NOTEBOOK)
    colab = shutil.which("colab")
    if not colab:
        raise RunnerError("The 'colab' command is not on PATH. Install google-colab-cli and authenticate it first.")

    output_dir = args.output_dir.expanduser().resolve()
    progress_path = (args.progress.expanduser().resolve() if args.progress else output_dir / "progress.json")
    output_paths = [output_dir / job.output_name for job in jobs]
    if progress_path in output_paths:
        raise RunnerError("The progress file path conflicts with a requested WAV output.")
    existing = [path for path in [progress_path, *output_paths] if path.exists() or path.is_symlink()]
    if existing:
        names = ", ".join(str(path) for path in existing)
        raise RunnerError(f"Refusing to overwrite existing outputs: {names}")

    output_dir.mkdir(parents=True, exist_ok=True)
    session = f"m3skill-{uuid.uuid4().hex[:8]}"
    state: dict[str, Any] = {
        "version": 1,
        "status": "preflight",
        "started_at": utc_now(),
        "finished_at": None,
        "gpu": args.gpu,
        "high_mem": bool(args.high_mem),
        "session": session,
        "session_stopped": False,
        "jobs": [
            {"id": job.job_id, "seed": job.seed, "status": "pending", "output": str(path)}
            for job, path in zip(jobs, output_paths)
        ],
    }

    def save_state() -> None:
        state["updated_at"] = utc_now()
        atomic_write_json(progress_path, state)

    save_state()
    session_may_exist = False
    current_error: Exception | None = None
    cleanup_error: Exception | None = None
    interrupted = False
    try:
        run_command([colab, "version"], timeout=60, label="version")
        run_command([colab, "usage"], timeout=args.provision_timeout, label="usage preflight")

        state["status"] = "provisioning"
        state["session_creation_attempted"] = True
        session_may_exist = True
        save_state()
        create_command = [colab, "new", "--session", session, "--gpu", args.gpu]
        if args.high_mem:
            create_command.append("--high-mem")
        run_command(create_command, timeout=args.provision_timeout, label="provision")
        state["session_created"] = True
        state["status"] = "loading_model"
        save_state()

        with tempfile.TemporaryDirectory(prefix="minimax-music3-") as temporary_dir:
            temporary = Path(temporary_dir)
            setup_path = temporary / "setup.py"
            setup_path.write_text(setup_code, encoding="utf-8")
            run_command(
                [colab, "exec", "--session", session, "--file", str(setup_path), "--timeout", str(args.timeout)],
                timeout=args.timeout + 60,
                label="load model",
            )

            for index, (job, output_path, job_state) in enumerate(zip(jobs, output_paths, state["jobs"]), start=1):
                job_state["status"] = "generating"
                save_state()
                code_path = temporary / f"job-{index:03d}.py"
                code_path.write_text(job_code(generation_template, job), encoding="utf-8")
                run_command(
                    [colab, "exec", "--session", session, "--file", str(code_path), "--timeout", str(args.timeout)],
                    timeout=args.timeout + 60,
                    label=f"generate {job.job_id}",
                )

                remote_path = f"/content/minimax_music3_outputs/minimax_music3_take{index:02d}_seed{job.seed}.wav"
                partial_path = output_path.with_name(f".{output_path.name}.partial")
                job_state["status"] = "downloading"
                job_state["remote_path"] = remote_path
                save_state()
                try:
                    run_command(
                        [colab, "download", "--session", session, remote_path, str(partial_path)],
                        timeout=args.provision_timeout,
                        label=f"download {job.job_id}",
                    )
                    audio_info = inspect_wav(partial_path)
                    os.replace(partial_path, output_path)
                finally:
                    partial_path.unlink(missing_ok=True)

                job_state["status"] = "completed"
                job_state["audio"] = audio_info
                save_state()
                print(
                    f"\nSaved {output_path} ({audio_info['sample_rate']} Hz, stereo, "
                    f"{audio_info['duration_seconds']} seconds)",
                    flush=True,
                )
        state["status"] = "complete"
    except KeyboardInterrupt:
        interrupted = True
        current_error = RunnerError("Interrupted by user.")
        state["status"] = "interrupted"
        state["error"] = str(current_error)
        for job_state in state["jobs"]:
            if job_state["status"] in {"generating", "downloading"}:
                job_state["status"] = "interrupted"
                break
    except Exception as error:
        current_error = error
        state["status"] = "failed"
        state["error"] = str(error)
        for job_state in state["jobs"]:
            if job_state["status"] in {"generating", "downloading"}:
                job_state["status"] = "failed"
                break
    finally:
        if session_may_exist:
            try:
                run_command([colab, "stop", "--session", session], timeout=300, label="stop owned session")
                state["session_stopped"] = True
            except Exception as error:
                cleanup_error = error
                state["cleanup_error"] = str(error)
        state["finished_at"] = utc_now()
        if current_error:
            state["status"] = "interrupted" if interrupted else "failed"
        elif cleanup_error:
            state["status"] = "cleanup_failed"
        save_state()

    if current_error:
        if interrupted:
            print(f"Interrupted; see progress file {progress_path}.", file=sys.stderr)
            if cleanup_error:
                print(f"Could not confirm Colab cleanup for {session}; inspect `colab sessions`.", file=sys.stderr)
            return 130
        cleanup_note = (
            f" Cleanup for session {session} could not be confirmed; inspect `colab sessions`."
            if cleanup_error
            else ""
        )
        raise RunnerError(f"Batch failed; see progress file {progress_path}. {current_error}{cleanup_note}") from current_error
    if cleanup_error:
        raise RunnerError(
            f"Music generation completed, but the Colab session may still be active. "
            f"Stop session {session} manually. Progress: {progress_path}"
        ) from cleanup_error
    print(f"\nCompleted {len(jobs)} job(s). Progress: {progress_path}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_batch(args)
    except RunnerError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Check the progress file and Colab sessions before retrying.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
