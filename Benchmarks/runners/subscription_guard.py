"""Fail-closed checks for the user's subscription-only, zero-money experiment."""
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import time


def validate(snapshot, max_usage_percent=80, allow_edu_allocation=False):
    if type(max_usage_percent) not in (int, float) or not math.isfinite(max_usage_percent) or not 0 < max_usage_percent <= 100:
        raise ValueError('Usage stop threshold must be above zero and at most 100%')
    if snapshot.get('ordinaryUsageAllowed') is not True:
        raise ValueError('Ordinary subscription usage is not verified')
    limits = snapshot.get('rateLimits') or {}
    authorized_edu = allow_edu_allocation is True and limits.get('planType') in {'edu', 'edu_plus', 'edu_pro'}
    if not authorized_edu and limits.get('planType') not in {'plus', 'pro', 'prolite', 'promax'}:
        raise ValueError('A personal included-usage subscription is required')
    credits = limits.get('credits') or {}
    if authorized_edu:
        # Explicit user-selected existing institutional allocation, not a zero-credit guarantee.
        # ordinaryUsageAllowed above remains mandatory; purchases, resets and API fallback never occur here.
        if type(credits.get('hasCredits')) is not bool or credits.get('unlimited') is not False:
            raise ValueError('Education allocation status is unavailable or unbounded')
        if not limits.get('primary') or not limits.get('secondary'):
            raise ValueError('Both Education allocation usage windows are required')
    elif credits.get('hasCredits') is not False or credits.get('unlimited') is not False or credits.get('balance') not in {'0', '0.0', '0.00'}:
        raise ValueError('Zero available paid credits could not be verified')
    if limits.get('rateLimitReachedType') is not None or limits.get('spendControlReached') is True:
        raise ValueError('Usage/spend limit reached')
    windows = [limits.get('primary'), limits.get('secondary')]
    if not any(windows): raise ValueError('Subscription usage windows unavailable')
    for window in windows:
        if window is None: continue
        percent = window.get('usedPercent')
        if type(percent) not in (int, float) or not math.isfinite(percent) or not 0 <= percent < max_usage_percent:
            raise ValueError(f'Stop at {max_usage_percent:g}% usage or unavailable usage')
    return limits


def environment():
    env = dict(os.environ)
    for key in ['OPENAI_API_KEY', 'CODEX_API_KEY', 'OPENAI_BASE_URL', 'CODEX_ACCESS_TOKEN']:
        env.pop(key, None)
    return env


def read_status():
    env = environment()
    # No auth contents or credential tokens are copied to reports.
    status = subprocess.run(['codex', 'login', 'status'], env=env, capture_output=True, text=True, timeout=10)
    if status.returncode or 'Logged in using ChatGPT' not in status.stdout + status.stderr:
        raise ValueError('ChatGPT authentication is required; API fallback prohibited')
    proc = subprocess.Popen(['codex', 'app-server', '--listen', 'stdio://'], env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    selector = selectors.DefaultSelector(); selector.register(proc.stdout, selectors.EVENT_READ)
    def send(value): proc.stdin.write(json.dumps(value)+'\n'); proc.stdin.flush()
    send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'contextlens_subscription_guard','version':'1.0'}}})
    snapshot = None; start = time.monotonic()
    try:
        while time.monotonic()-start < 25:
            if not selector.select(1): continue
            line = proc.stdout.readline()
            if not line: break
            message = json.loads(line)
            if message.get('id') == 1:
                send({'method':'initialized','params':{}})
                send({'id':2,'method':'account/rateLimits/read'})
            elif message.get('id') == 2:
                snapshot = message.get('result'); break
    finally:
        selector.close(); proc.terminate()
        try: proc.wait(timeout=3)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    if not isinstance(snapshot, dict): raise ValueError('Subscription/credit status unavailable')
    # Read-only observation never starts a model turn, consumes a reset or exposes identity/credentials.
    return {'ordinaryUsageAllowed': snapshot.get('ordinaryUsageAllowed'), 'rateLimits': snapshot.get('rateLimits')}


def check(max_usage_percent=80, allow_edu_allocation=False):
    snapshot = read_status()
    validate(snapshot, max_usage_percent=max_usage_percent, allow_edu_allocation=allow_edu_allocation)
    return snapshot


def command():
    return ['codex', 'exec', '--json', '--ephemeral', '--ignore-user-config', '--sandbox', 'workspace-write',
            '--strict-config', '--model', 'gpt-6.1-sol', '-c', 'model_reasoning_effort="high"', '-c', 'forced_login_method="chatgpt"',
            '-c', 'model_provider="openai"', '-c', 'service_tier="default"', '-c', 'features.fast_mode=false',
            '-c', 'web_search="disabled"', '-']
