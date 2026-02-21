from __future__ import annotations

import os
import shlex
import subprocess


class RunnerError(RuntimeError):
    pass


def run_with_env(command: list[str], injected_env: dict[str, str]) -> int:
    if not command:
        raise RunnerError("No command provided")

    env = os.environ.copy()
    env.update(injected_env)

    result = subprocess.run(command, env=env, check=False)
    return result.returncode


def parse_command(raw: str) -> list[str]:
    parts = shlex.split(raw)
    if not parts:
        raise RunnerError("Command parsing produced no arguments")
    return parts
