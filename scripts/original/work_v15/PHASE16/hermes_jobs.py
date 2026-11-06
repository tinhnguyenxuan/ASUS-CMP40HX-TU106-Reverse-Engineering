#!/usr/bin/env python3
"""Start/status a directly instructed Hermes job from the Hermes MCP host.

No /goal, no --resume, no config changes. Invoke start/status through the MCP
worker's terminal so process liveness is checked in the correct PID namespace.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent / 'JOBS'
CLI = '/home/REDACTED_USER/.local/bin/hermes'


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def save(path, obj):
    tmp = path.with_suffix(f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
    os.replace(tmp, path)


def process(pid, expected_start=None):
    try:
        raw = Path(f'/proc/{int(pid)}/stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        ticks = fields[19]
        live = fields[0] not in ('Z', 'X') and (expected_start is None or ticks == str(expected_start))
        return dict(pid=int(pid), live=live, start_ticks=ticks, process_state=fields[0])
    except (OSError, ValueError, TypeError, IndexError):
        return dict(pid=pid, live=False)


def status(job):
    launch, state = read(job / 'launch.json'), read(job / 'state.json')
    wrapper = process(launch.get('wrapper_pid'), launch.get('wrapper_start_ticks'))
    child = process(state.get('hermes_pid'), state.get('hermes_start_ticks'))
    log = job / 'output.log'
    return dict(job=job.name, observed_at=now(), launch=launch, state=state,
                wrapper_process=wrapper, hermes_process=child,
                terminal=state.get('stage') in ('completed', 'failed'),
                output_bytes=log.stat().st_size if log.exists() else 0)


def worker(job):
    state = dict(job=job.name, stage='starting', started_at=now(), wrapper_pid=os.getpid())
    save(job / 'state.json', state)
    try:
        prompt = (job / 'task.txt').read_text()
        state['task_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
        with (job / 'output.log').open('ab', buffering=0) as log:
            child = subprocess.Popen([CLI, '-z', prompt], cwd=str(BASE.parent.parent.parent),
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     env={**os.environ, 'PYTHONUNBUFFERED': '1'})
            child_info = process(child.pid)
            state.update(stage='running', hermes_pid=child.pid,
                         hermes_start_ticks=child_info.get('start_ticks'))
            save(job / 'state.json', state)
            while child.poll() is None:
                state['heartbeat_at'] = now()
                save(job / 'state.json', state)
                time.sleep(2)
            state.update(stage='completed' if child.returncode == 0 else 'failed',
                         exit_code=child.returncode, ended_at=now())
    except Exception as exc:
        state.update(stage='failed', error=f'{type(exc).__name__}: {exc}', ended_at=now())
    save(job / 'state.json', state)


def start(job):
    if not (job / 'task.txt').is_file():
        raise ValueError('task.txt must exist before dispatch')
    with (job / 'dispatch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = status(job)
        if previous['terminal'] or previous['wrapper_process']['live'] or previous['hermes_process']['live']:
            return dict(dispatched=False, reason='existing job; inspect status before any replacement', **previous)
        with (job / 'wrapper.log').open('ab', buffering=0) as log:
            child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), 'worker', job.name],
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True, cwd=str(BASE.parent.parent.parent))
        info = process(child.pid)
        save(job / 'launch.json', dict(dispatched_at=now(), wrapper_pid=child.pid,
                                     wrapper_start_ticks=info.get('start_ticks'),
                                     requested_model_override=False,
                                     task_sha256=hashlib.sha256((job / 'task.txt').read_bytes()).hexdigest()))
    time.sleep(3)
    return dict(dispatched=True, **status(job))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('start', 'status', 'worker'))
    parser.add_argument('job')
    args = parser.parse_args()
    if not args.job or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in args.job):
        parser.error('job name must be a lowercase identifier')
    job = BASE / args.job
    job.mkdir(parents=True, exist_ok=True)
    if args.command == 'worker':
        worker(job)
    else:
        print(json.dumps(start(job) if args.command == 'start' else status(job), indent=2, ensure_ascii=False))
