"""
TV platform keyboard shortcut CLI links with DAO-voting broadcast queue.

Supported targets
-----------------
* ``android_pie``   — Android TV (Pie / Android 9), addressed via ADB keyevent
* ``amlogic``       — Amlogic-based Android TV, same ADB interface
* ``amazon_firetv`` — Amazon Fire TV / Fire TV Stick, ADB keyevent
* ``linux_av``      — Linux audio-visual stack (amixer / playerctl / FFmpeg)

Architecture
------------
Shortcut command requests travel through a :class:`BroadcastQueue`.  DAO
participants call :meth:`BroadcastQueue.vote` to approve or reject each
request.  Once the configured *quorum* of approve-votes is reached,
:class:`TVCmdComponent` executes the linked shell command and
:class:`PinkSyncFeedbackComponent` reports the result back to PinkSync /
PinkFlow.

Pipeline::

    submit → (broadcast queue) → DAO vote → tv_cmd_execute → pinksync_feedback

Typical usage::

    from automation.tv_cmd import (
        TVPlatform, BroadcastQueue, FeedbackMode, build_tv_pipeline
    )

    queue = BroadcastQueue(quorum=2)
    req = queue.submit(TVPlatform.AMAZON_FIRETV, "Enter", requester="alice")
    queue.vote(req.request_id, voter="bob",   approve=True)
    queue.vote(req.request_id, voter="carol", approve=True)  # quorum reached

    engine = build_tv_pipeline(queue, device="192.168.1.10:5555")
    approved = queue.pop_next_approved()
    if approved:
        results = engine.trigger_type("shortcut.process_queue", payload=approved)

CLI::

    python -m automation.tv_cmd list
    python -m automation.tv_cmd preview [--output shortcuts.html]
"""

from __future__ import annotations

import html as _html
import json
import logging
import subprocess
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from .components import Component, ComponentInput, ComponentOutput
from .engine import AutomationDefinition, AutomationEngine
from .firetv import KEYBOARD_SHORTCUTS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TVPlatform(str, Enum):
    """Supported TV / media platform targets."""
    ANDROID_PIE = "android_pie"
    AMLOGIC = "amlogic"
    AMAZON_FIRETV = "amazon_firetv"
    LINUX_AV = "linux_av"


class RequestStatus(str, Enum):
    """Lifecycle state of a :class:`ShortcutRequest`."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"


class FeedbackMode(str, Enum):
    """Operating mode for :class:`PinkSyncFeedbackComponent`."""
    DEV = "dev"              # log only – no HTTP calls
    PREVIEW = "preview"      # log only – no HTTP calls
    PRODUCTION = "production"  # HTTP POST to PinkSync webhook URL


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CmdLink:
    """
    Links a platform + keyboard key name to an executable shell command.

    For ADB platforms *keycode* is required; for Linux AV *linux_cmd* is
    required.
    """
    platform: TVPlatform
    key_name: str
    description: str
    keycode: Optional[int] = None           # ADB keycode (Android platforms)
    linux_cmd: Optional[tuple] = None       # Command tuple (Linux AV platform)


@dataclass
class ShortcutRequest:
    """A shortcut execution request in the broadcast queue."""
    request_id: str
    platform: TVPlatform
    key_name: str
    requester: str
    timestamp: datetime
    status: RequestStatus = RequestStatus.PENDING


@dataclass(frozen=True)
class DAOVote:
    """A single DAO participant vote on a :class:`ShortcutRequest`."""
    voter: str
    approve: bool
    timestamp: datetime


# ---------------------------------------------------------------------------
# Platform shortcut tables
# ---------------------------------------------------------------------------

#: Platforms that use ``adb shell input keyevent`` to send key events.
ADB_PLATFORMS: frozenset = frozenset({
    TVPlatform.ANDROID_PIE,
    TVPlatform.AMLOGIC,
    TVPlatform.AMAZON_FIRETV,
})


def _adb_links(platform: TVPlatform) -> Dict[str, CmdLink]:
    """Build ADB CmdLinks for *platform* from the existing KEYBOARD_SHORTCUTS table."""
    return {
        key: CmdLink(
            platform=platform,
            key_name=key,
            description=f"ADB keyevent {firetv_key.name} ({int(firetv_key)})",
            keycode=int(firetv_key),
        )
        for key, firetv_key in KEYBOARD_SHORTCUTS.items()
    }


#: Linux AV shortcut table (amixer / playerctl / FFmpeg).
LINUX_AV_SHORTCUTS: Dict[str, CmdLink] = {
    "ArrowUp":            CmdLink(TVPlatform.LINUX_AV, "ArrowUp",            "Volume up (ALSA)",              linux_cmd=("amixer", "set", "Master", "5%+")),
    "ArrowDown":          CmdLink(TVPlatform.LINUX_AV, "ArrowDown",          "Volume down (ALSA)",            linux_cmd=("amixer", "set", "Master", "5%-")),
    "AudioVolumeMute":    CmdLink(TVPlatform.LINUX_AV, "AudioVolumeMute",    "Mute toggle (ALSA)",            linux_cmd=("amixer", "set", "Master", "toggle")),
    " ":                  CmdLink(TVPlatform.LINUX_AV, " ",                  "Play / pause (playerctl)",      linux_cmd=("playerctl", "play-pause")),
    "MediaPlayPause":     CmdLink(TVPlatform.LINUX_AV, "MediaPlayPause",     "Play / pause (playerctl)",      linux_cmd=("playerctl", "play-pause")),
    "MediaRewind":        CmdLink(TVPlatform.LINUX_AV, "MediaRewind",        "Rewind 10 s (playerctl)",       linux_cmd=("playerctl", "position", "10-")),
    "MediaFastForward":   CmdLink(TVPlatform.LINUX_AV, "MediaFastForward",   "Fast-forward 10 s (playerctl)", linux_cmd=("playerctl", "position", "10+")),
    "MediaTrackNext":     CmdLink(TVPlatform.LINUX_AV, "MediaTrackNext",     "Next track (playerctl)",        linux_cmd=("playerctl", "next")),
    "MediaTrackPrevious": CmdLink(TVPlatform.LINUX_AV, "MediaTrackPrevious", "Previous track (playerctl)",    linux_cmd=("playerctl", "previous")),
    "ArrowRight":         CmdLink(TVPlatform.LINUX_AV, "ArrowRight",         "Seek forward 5 s (playerctl)",  linux_cmd=("playerctl", "position", "5+")),
    "ArrowLeft":          CmdLink(TVPlatform.LINUX_AV, "ArrowLeft",          "Seek back 5 s (playerctl)",     linux_cmd=("playerctl", "position", "5-")),
}

#: Full per-platform shortcut registry.
PLATFORM_SHORTCUTS: Dict[TVPlatform, Dict[str, CmdLink]] = {
    TVPlatform.ANDROID_PIE:   _adb_links(TVPlatform.ANDROID_PIE),
    TVPlatform.AMLOGIC:       _adb_links(TVPlatform.AMLOGIC),
    TVPlatform.AMAZON_FIRETV: _adb_links(TVPlatform.AMAZON_FIRETV),
    TVPlatform.LINUX_AV:      LINUX_AV_SHORTCUTS,
}


def get_cmd_link(platform: TVPlatform, key_name: str) -> Optional[CmdLink]:
    """Return the :class:`CmdLink` for *platform* + *key_name*, or ``None``."""
    return PLATFORM_SHORTCUTS.get(platform, {}).get(key_name)


def build_cmd(link: CmdLink, device: Optional[str] = None) -> List[str]:
    """
    Construct the shell command list for *link*.

    For ADB platforms *device* is the optional ``-s <addr>`` target.

    Raises:
        ValueError: When the link has no executable command configured.
    """
    if link.platform in ADB_PLATFORMS:
        cmd = ["adb"]
        if device:
            cmd += ["-s", device]
        cmd += ["shell", "input", "keyevent", str(link.keycode)]
        return cmd
    if link.platform == TVPlatform.LINUX_AV and link.linux_cmd:
        return list(link.linux_cmd)
    raise ValueError(
        f"No executable command configured for platform={link.platform.value!r} "
        f"key={link.key_name!r}"
    )


# ---------------------------------------------------------------------------
# Broadcast queue
# ---------------------------------------------------------------------------

class BroadcastQueue:
    """
    In-memory broadcast queue for shortcut requests with DAO voting.

    Requests are submitted by any caller.  DAO participants call
    :meth:`vote` until a *quorum* of approve or reject votes is reached,
    which transitions the request to ``APPROVED`` or ``REJECTED``.
    Approved requests can then be popped with :meth:`pop_next_approved`
    and handed to the automation pipeline for execution.
    """

    def __init__(self, quorum: int = 1) -> None:
        """
        Args:
            quorum: Number of approve (or reject) votes required to change
                    a request's status from ``PENDING``.
        """
        if quorum < 1:
            raise ValueError("quorum must be >= 1")
        self._quorum = quorum
        self._requests: Dict[str, ShortcutRequest] = {}
        self._votes: Dict[str, List[DAOVote]] = {}

    @property
    def quorum(self) -> int:
        return self._quorum

    def submit(
        self,
        platform: TVPlatform,
        key_name: str,
        requester: str,
    ) -> ShortcutRequest:
        """Add a new shortcut request to the queue. Returns the new request."""
        req_id = uuid.uuid4().hex[:12]
        req = ShortcutRequest(
            request_id=req_id,
            platform=platform,
            key_name=key_name,
            requester=requester,
            timestamp=datetime.now(),
        )
        self._requests[req_id] = req
        self._votes[req_id] = []
        return req

    def vote(self, request_id: str, voter: str, approve: bool) -> ShortcutRequest:
        """
        Cast a vote on *request_id*.

        Returns the (possibly updated) :class:`ShortcutRequest`.

        Raises:
            KeyError: Request does not exist.
            ValueError: Request is not in ``PENDING`` status.
        """
        if request_id not in self._requests:
            raise KeyError(f"Request '{request_id}' not found in queue")
        req = self._requests[request_id]
        if req.status != RequestStatus.PENDING:
            raise ValueError(
                f"Request '{request_id}' is not pending "
                f"(current status: {req.status.value!r})"
            )
        self._votes[request_id].append(
            DAOVote(voter=voter, approve=approve, timestamp=datetime.now())
        )
        votes = self._votes[request_id]
        approve_count = sum(1 for v in votes if v.approve)
        reject_count = sum(1 for v in votes if not v.approve)
        if approve_count >= self._quorum:
            req.status = RequestStatus.APPROVED
        elif reject_count >= self._quorum:
            req.status = RequestStatus.REJECTED
        return req

    def pop_next_approved(self) -> Optional[ShortcutRequest]:
        """Return and mark-as-executing the oldest approved request, or ``None``."""
        for req in self._requests.values():
            if req.status == RequestStatus.APPROVED:
                req.status = RequestStatus.EXECUTING
                return req
        return None

    def mark_executed(self, request_id: str) -> None:
        """Mark *request_id* as successfully executed."""
        if request_id in self._requests:
            self._requests[request_id].status = RequestStatus.EXECUTED

    def mark_failed(self, request_id: str) -> None:
        """Mark *request_id* as failed."""
        if request_id in self._requests:
            self._requests[request_id].status = RequestStatus.FAILED

    def pending(self) -> List[ShortcutRequest]:
        """Return all requests in ``PENDING`` status."""
        return [r for r in self._requests.values() if r.status == RequestStatus.PENDING]

    def approved(self) -> List[ShortcutRequest]:
        """Return all requests in ``APPROVED`` status."""
        return [r for r in self._requests.values() if r.status == RequestStatus.APPROVED]

    def votes_for(self, request_id: str) -> List[DAOVote]:
        """Return all votes cast for *request_id*."""
        return list(self._votes.get(request_id, []))

    def __len__(self) -> int:
        return len(self._requests)

    def __repr__(self) -> str:
        return (
            f"BroadcastQueue(quorum={self._quorum}, "
            f"total={len(self)}, pending={len(self.pending())})"
        )


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

class DAOVotingComponent(Component):
    """
    Gate component that passes a request through only if it is DAO-approved.

    Input payload
        A :class:`ShortcutRequest` instance.

    Output result
        The same :class:`ShortcutRequest` when approved or executing;
        an error output otherwise.
    """

    name = "dao_vote_check"
    description = "Passes a ShortcutRequest through only when DAO quorum is met."

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        req: ShortcutRequest = input_.payload
        if req.status in (RequestStatus.APPROVED, RequestStatus.EXECUTING):
            return self._ok(req)
        if req.status == RequestStatus.REJECTED:
            return self._err(
                f"Request '{req.request_id}' was rejected by DAO vote"
            )
        return self._err(
            f"Request '{req.request_id}' has not yet reached DAO quorum "
            f"(status: {req.status.value!r})"
        )


class TVCmdComponent(Component):
    """
    Executes the shell command linked to a :class:`ShortcutRequest`.

    Supports all four platforms: Android Pie, Amlogic, Amazon Fire TV and
    Linux AV (amixer / playerctl / FFmpeg).

    Input payload
        A :class:`ShortcutRequest` with status ``APPROVED`` or ``EXECUTING``.

    Metadata
        ``"device"`` (str) — ADB device address; overrides the constructor
        default for Android/Fire TV targets.

    Output result
        ``{"request_id", "platform", "key", "cmd", "stdout"}`` on success.
    """

    name = "tv_cmd_execute"
    description = "Executes the platform command linked to an approved ShortcutRequest."

    def __init__(self, device: Optional[str] = None) -> None:
        self._device = device

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        req: ShortcutRequest = input_.payload
        device: Optional[str] = input_.metadata.get("device") or self._device

        link = get_cmd_link(req.platform, req.key_name)
        if link is None:
            return self._err(
                f"No command link for platform={req.platform.value!r} "
                f"key={req.key_name!r}"
            )

        try:
            cmd = build_cmd(link, device=device)
        except ValueError as exc:
            return self._err(str(exc))

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except FileNotFoundError:
            return self._err(f"Command not found: {cmd[0]!r}; ensure it is on PATH")
        except subprocess.TimeoutExpired:
            return self._err(f"Command timed out: {' '.join(cmd)}")

        if proc.returncode != 0:
            return self._err(
                f"Command exited with code {proc.returncode}: {proc.stderr.strip()}"
            )

        return self._ok({
            "request_id": req.request_id,
            "platform": req.platform.value,
            "key": req.key_name,
            "cmd": cmd,
            "stdout": proc.stdout.strip(),
        })


class PinkSyncFeedbackComponent(Component):
    """
    Reports execution results back to PinkSync / PinkFlow.

    In ``DEV`` and ``PREVIEW`` modes the payload is logged only (no HTTP).
    In ``PRODUCTION`` mode it is HTTP-POSTed as JSON to *webhook_url*.

    Input payload
        Execution result dict as produced by :class:`TVCmdComponent`.

    Output result
        The same dict on success (pass-through), optionally extended with
        ``"pinksync_response"`` in production mode.
    """

    name = "pinksync_feedback"
    description = "Sends execution feedback to PinkSync / PinkFlow."

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        mode: FeedbackMode = FeedbackMode.DEV,
        timeout: int = 5,
    ) -> None:
        self._webhook_url = webhook_url
        self._mode = mode
        self._timeout = timeout

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        result = input_.payload

        if self._mode in (FeedbackMode.DEV, FeedbackMode.PREVIEW):
            logger.info("[PinkSync %s] feedback: %s", self._mode.value, result)
            return self._ok(result)

        # Production: POST to PinkSync webhook
        if not self._webhook_url:
            return self._err(
                "PinkSync webhook_url is not configured for production mode"
            )

        body = json.dumps({"event": "shortcut.executed", "data": result}).encode()
        http_req = urllib.request.Request(
            self._webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_req, timeout=self._timeout) as resp:
                response_body = resp.read().decode()
        except urllib.error.URLError as exc:
            return self._err(f"PinkSync webhook request failed: {exc}")

        return self._ok({**result, "pinksync_response": response_body})


# ---------------------------------------------------------------------------
# HTML preview (nTouch / browser)
# ---------------------------------------------------------------------------

def render_shortcuts_html(
    platforms: Optional[List[TVPlatform]] = None,
    queue: Optional[BroadcastQueue] = None,
) -> str:
    """
    Render an HTML page previewing shortcut tables and the broadcast queue.

    The output is a self-contained HTML document suitable for browser preview
    or nTouch display in the PinkFlow dev / preview environment.

    Args:
        platforms: Platforms to include.  Defaults to all four platforms.
        queue:     Optional :class:`BroadcastQueue` to render pending requests.
    """
    if platforms is None:
        platforms = list(TVPlatform)

    platform_sections = ""
    for platform in platforms:
        shortcuts = PLATFORM_SHORTCUTS.get(platform, {})
        rows = ""
        for key, link in sorted(shortcuts.items()):
            try:
                cmd_str = " ".join(build_cmd(link))
            except ValueError:
                cmd_str = "(no command)"
            rows += (
                f"<tr><td>{_html.escape(key)}</td>"
                f"<td>{_html.escape(link.description)}</td>"
                f"<td><code>{_html.escape(cmd_str)}</code></td></tr>"
            )
        platform_sections += (
            f"<h2>{_html.escape(platform.value)}</h2>"
            "<table><thead><tr><th>Key</th><th>Description</th>"
            "<th>Command</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    queue_section = ""
    if queue:
        queue_rows = ""
        for req in queue.pending():
            queue_rows += (
                f"<tr><td>{_html.escape(req.request_id)}</td>"
                f"<td>{_html.escape(req.platform.value)}</td>"
                f"<td>{_html.escape(req.key_name)}</td>"
                f"<td>{_html.escape(req.requester)}</td>"
                f"<td>{_html.escape(req.status.value)}</td></tr>"
            )
        if queue_rows:
            queue_section = (
                "<h2>Broadcast Queue — pending</h2>"
                "<table><thead><tr><th>ID</th><th>Platform</th><th>Key</th>"
                "<th>Requester</th><th>Status</th></tr></thead>"
                f"<tbody>{queue_rows}</tbody></table>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TV Shortcut Preview – PinkFlow</title>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 1rem 2rem; }}
  h1   {{ color: #c0047a; }}
  h2   {{ color: #333; border-bottom: 1px solid #ccc; padding-bottom: .2rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
  th, td {{ border: 1px solid #ddd; padding: .35rem .65rem; text-align: left; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  code {{ font-size: .88em; background: #f0f0f0; padding: 1px 4px; border-radius: 3px; }}
</style>
</head>
<body>
<h1>TV Platform Keyboard Shortcuts — PinkFlow</h1>
{platform_sections}
{queue_section}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------

def build_tv_pipeline(
    queue: BroadcastQueue,
    device: Optional[str] = None,
    webhook_url: Optional[str] = None,
    mode: FeedbackMode = FeedbackMode.DEV,
) -> AutomationEngine:
    """
    Create and return a pre-wired :class:`~automation.engine.AutomationEngine`
    for the TV shortcut broadcast pipeline.

    The engine listens for the ``"shortcut.process_queue"`` event.  The
    caller is responsible for popping an approved request from *queue* and
    passing it as the event payload::

        approved = queue.pop_next_approved()
        if approved:
            results = engine.trigger_type("shortcut.process_queue", payload=approved)
            if results[0].status == RunStatus.SUCCESS:
                queue.mark_executed(approved.request_id)
            else:
                queue.mark_failed(approved.request_id)

    Args:
        queue:       The :class:`BroadcastQueue` holding pending requests.
        device:      Default ADB device address for Android/Fire TV targets.
        webhook_url: PinkSync webhook URL (required in production mode).
        mode:        Feedback operating mode (dev / preview / production).
    """
    engine = AutomationEngine()
    engine.components.register("dao_vote_check", DAOVotingComponent())
    engine.components.register("tv_cmd_execute", TVCmdComponent(device=device))
    engine.components.register(
        "pinksync_feedback",
        PinkSyncFeedbackComponent(webhook_url=webhook_url, mode=mode),
    )
    engine.define(AutomationDefinition(
        name="process_shortcut_queue",
        triggers=["shortcut.process_queue"],
        steps=["dao_vote_check", "tv_cmd_execute", "pinksync_feedback"],
        description=(
            "Execute the next DAO-approved shortcut request from the "
            "broadcast queue and report feedback to PinkSync / PinkFlow."
        ),
    ))
    return engine


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli_main(argv: Optional[List[str]] = None) -> int:  # pragma: no cover
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="python -m automation.tv_cmd",
        description=(
            "TV platform keyboard shortcut CLI — "
            "Android Pie / Amlogic / Amazon Fire TV / Linux AV"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List shortcuts for all (or specific) platforms")
    p_list.add_argument(
        "--platform",
        choices=[p.value for p in TVPlatform],
        help="Filter to a single platform",
    )

    # preview
    p_prev = sub.add_parser("preview", help="Output HTML preview (nTouch / browser)")
    p_prev.add_argument("--output", default="-", help="File path or '-' for stdout")
    p_prev.add_argument(
        "--platform",
        choices=[p.value for p in TVPlatform],
        action="append",
        dest="platforms",
        help="Include this platform (repeatable; default: all)",
    )

    args = parser.parse_args(argv)

    if args.command == "list":
        platforms = (
            [TVPlatform(args.platform)] if args.platform else list(TVPlatform)
        )
        for platform in platforms:
            shortcuts = PLATFORM_SHORTCUTS[platform]
            print(f"\n=== {platform.value} ===")
            for key, link in sorted(shortcuts.items()):
                try:
                    cmd_str = " ".join(build_cmd(link))
                except ValueError:
                    cmd_str = "(no command)"
                print(f"  {key!r:30s}  {link.description:45s}  {cmd_str}")
        return 0

    if args.command == "preview":
        platforms = (
            [TVPlatform(p) for p in args.platforms]
            if args.platforms
            else None
        )
        output = render_shortcuts_html(platforms=platforms)
        if args.output == "-":
            print(output)
        else:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(output)
            print(f"Preview written to {args.output}", file=sys.stderr)
        return 0

    return 1  # unreachable; argparse enforces subcommand


if __name__ == "__main__":
    import sys
    sys.exit(_cli_main())
