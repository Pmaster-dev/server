"""Tests for TV platform keyboard shortcut CLI links with DAO voting."""

import subprocess
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from automation.components import ComponentInput
from automation.engine import RunStatus
from automation.tv_cmd import (
    ADB_PLATFORMS,
    LINUX_AV_SHORTCUTS,
    PLATFORM_SHORTCUTS,
    BroadcastQueue,
    CmdLink,
    DAOVote,
    DAOVotingComponent,
    FeedbackMode,
    PinkSyncFeedbackComponent,
    RequestStatus,
    ShortcutRequest,
    TVCmdComponent,
    TVPlatform,
    build_cmd,
    build_tv_pipeline,
    get_cmd_link,
    render_shortcuts_html,
)


def _inp(payload, name="test", metadata=None):
    return ComponentInput(name=name, payload=payload, metadata=metadata or {})


def _make_request(
    platform=TVPlatform.AMAZON_FIRETV,
    key_name="Enter",
    requester="alice",
    status=RequestStatus.APPROVED,
) -> ShortcutRequest:
    from datetime import datetime
    import uuid
    return ShortcutRequest(
        request_id=uuid.uuid4().hex[:12],
        platform=platform,
        key_name=key_name,
        requester=requester,
        timestamp=datetime.now(),
        status=status,
    )


# ---------------------------------------------------------------------------
# TVPlatform
# ---------------------------------------------------------------------------

class TestTVPlatform:
    def test_all_platforms_defined(self):
        values = {p.value for p in TVPlatform}
        assert values == {"android_pie", "amlogic", "amazon_firetv", "linux_av"}

    def test_adb_platforms_are_subset_of_all(self):
        assert ADB_PLATFORMS.issubset(set(TVPlatform))

    def test_linux_av_not_in_adb_platforms(self):
        assert TVPlatform.LINUX_AV not in ADB_PLATFORMS


# ---------------------------------------------------------------------------
# PLATFORM_SHORTCUTS
# ---------------------------------------------------------------------------

class TestPlatformShortcuts:
    def test_all_platforms_have_entries(self):
        for platform in TVPlatform:
            assert PLATFORM_SHORTCUTS[platform], f"No shortcuts for {platform}"

    def test_adb_platforms_share_same_keyset(self):
        keys = [set(PLATFORM_SHORTCUTS[p].keys()) for p in ADB_PLATFORMS]
        assert keys[0] == keys[1] == keys[2]

    def test_adb_links_have_keycodes(self):
        for platform in ADB_PLATFORMS:
            for link in PLATFORM_SHORTCUTS[platform].values():
                assert link.keycode is not None
                assert isinstance(link.keycode, int)

    def test_linux_av_links_have_linux_cmd(self):
        for link in PLATFORM_SHORTCUTS[TVPlatform.LINUX_AV].values():
            assert link.linux_cmd is not None
            assert len(link.linux_cmd) >= 1

    def test_get_cmd_link_returns_none_for_unknown(self):
        assert get_cmd_link(TVPlatform.AMAZON_FIRETV, "F13") is None

    def test_get_cmd_link_returns_link_for_known(self):
        link = get_cmd_link(TVPlatform.AMAZON_FIRETV, "Enter")
        assert link is not None
        assert link.platform == TVPlatform.AMAZON_FIRETV
        assert link.key_name == "Enter"


# ---------------------------------------------------------------------------
# build_cmd
# ---------------------------------------------------------------------------

class TestBuildCmd:
    def test_adb_without_device(self):
        link = get_cmd_link(TVPlatform.AMAZON_FIRETV, "Enter")
        cmd = build_cmd(link)
        assert cmd[:1] == ["adb"]
        assert "shell" in cmd
        assert "keyevent" in cmd
        assert "-s" not in cmd

    def test_adb_with_device(self):
        link = get_cmd_link(TVPlatform.ANDROID_PIE, "ArrowUp")
        cmd = build_cmd(link, device="192.168.1.50:5555")
        assert cmd[1:3] == ["-s", "192.168.1.50:5555"]
        assert "keyevent" in cmd

    def test_adb_keycode_in_command(self):
        link = get_cmd_link(TVPlatform.AMLOGIC, "Enter")
        cmd = build_cmd(link)
        assert str(link.keycode) in cmd

    def test_linux_av_returns_system_cmd(self):
        link = LINUX_AV_SHORTCUTS["ArrowUp"]
        cmd = build_cmd(link)
        assert cmd == list(link.linux_cmd)

    def test_linux_av_play_pause(self):
        link = LINUX_AV_SHORTCUTS[" "]
        cmd = build_cmd(link)
        assert "playerctl" in cmd

    def test_all_default_shortcuts_buildable_for_every_adb_platform(self):
        for platform in ADB_PLATFORMS:
            for key, link in PLATFORM_SHORTCUTS[platform].items():
                cmd = build_cmd(link)
                assert cmd, f"Empty cmd for {platform}/{key}"

    def test_all_linux_av_shortcuts_buildable(self):
        for key, link in LINUX_AV_SHORTCUTS.items():
            cmd = build_cmd(link)
            assert cmd, f"Empty cmd for linux_av/{key}"


# ---------------------------------------------------------------------------
# BroadcastQueue
# ---------------------------------------------------------------------------

class TestBroadcastQueue:
    def test_quorum_must_be_positive(self):
        with pytest.raises(ValueError):
            BroadcastQueue(quorum=0)

    def test_submit_adds_pending_request(self):
        q = BroadcastQueue()
        req = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        assert req.status == RequestStatus.PENDING
        assert len(q.pending()) == 1

    def test_submit_generates_unique_ids(self):
        q = BroadcastQueue()
        ids = {q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "u").request_id for _ in range(10)}
        assert len(ids) == 10

    def test_single_vote_meets_quorum_1(self):
        q = BroadcastQueue(quorum=1)
        req = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        updated = q.vote(req.request_id, voter="bob", approve=True)
        assert updated.status == RequestStatus.APPROVED
        assert len(q.approved()) == 1

    def test_reject_vote_meets_quorum_1(self):
        q = BroadcastQueue(quorum=1)
        req = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        updated = q.vote(req.request_id, voter="bob", approve=False)
        assert updated.status == RequestStatus.REJECTED

    def test_quorum_2_requires_two_approvals(self):
        q = BroadcastQueue(quorum=2)
        req = q.submit(TVPlatform.LINUX_AV, " ", "alice")
        q.vote(req.request_id, voter="bob", approve=True)
        assert req.status == RequestStatus.PENDING
        q.vote(req.request_id, voter="carol", approve=True)
        assert req.status == RequestStatus.APPROVED

    def test_vote_on_nonexistent_request_raises(self):
        q = BroadcastQueue()
        with pytest.raises(KeyError):
            q.vote("doesnotexist", voter="x", approve=True)

    def test_vote_on_non_pending_request_raises(self):
        q = BroadcastQueue(quorum=1)
        req = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        q.vote(req.request_id, voter="bob", approve=True)
        with pytest.raises(ValueError, match="not pending"):
            q.vote(req.request_id, voter="carol", approve=True)

    def test_pop_next_approved_returns_none_when_empty(self):
        q = BroadcastQueue()
        assert q.pop_next_approved() is None

    def test_pop_next_approved_transitions_to_executing(self):
        q = BroadcastQueue(quorum=1)
        req = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        q.vote(req.request_id, voter="bob", approve=True)
        popped = q.pop_next_approved()
        assert popped is req
        assert req.status == RequestStatus.EXECUTING
        # No more approved
        assert q.pop_next_approved() is None

    def test_mark_executed_and_failed(self):
        q = BroadcastQueue(quorum=1)
        r1 = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "a")
        r2 = q.submit(TVPlatform.LINUX_AV, " ", "b")
        q.vote(r1.request_id, voter="x", approve=True)
        q.vote(r2.request_id, voter="x", approve=True)
        q.mark_executed(r1.request_id)
        q.mark_failed(r2.request_id)
        assert r1.status == RequestStatus.EXECUTED
        assert r2.status == RequestStatus.FAILED

    def test_votes_for_returns_all_votes(self):
        q = BroadcastQueue(quorum=3)
        req = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        q.vote(req.request_id, voter="bob", approve=True)
        q.vote(req.request_id, voter="carol", approve=True)
        votes = q.votes_for(req.request_id)
        assert len(votes) == 2
        assert all(isinstance(v, DAOVote) for v in votes)

    def test_len_counts_all_requests(self):
        q = BroadcastQueue()
        assert len(q) == 0
        q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "a")
        q.submit(TVPlatform.LINUX_AV, " ", "b")
        assert len(q) == 2

    def test_repr_contains_quorum_and_pending(self):
        q = BroadcastQueue(quorum=3)
        q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "a")
        r = repr(q)
        assert "quorum=3" in r
        assert "pending=1" in r


# ---------------------------------------------------------------------------
# DAOVotingComponent
# ---------------------------------------------------------------------------

class TestDAOVotingComponent:
    def setup_method(self):
        self.comp = DAOVotingComponent()

    def test_approved_status_passes_through(self):
        req = _make_request(status=RequestStatus.APPROVED)
        out = self.comp.execute(_inp(req))
        assert out.success is True
        assert out.result is req

    def test_executing_status_passes_through(self):
        req = _make_request(status=RequestStatus.EXECUTING)
        out = self.comp.execute(_inp(req))
        assert out.success is True

    def test_pending_status_returns_error(self):
        req = _make_request(status=RequestStatus.PENDING)
        out = self.comp.execute(_inp(req))
        assert out.success is False
        assert "quorum" in out.error.lower()

    def test_rejected_status_returns_error(self):
        req = _make_request(status=RequestStatus.REJECTED)
        out = self.comp.execute(_inp(req))
        assert out.success is False
        assert "rejected" in out.error.lower()


# ---------------------------------------------------------------------------
# TVCmdComponent
# ---------------------------------------------------------------------------

class TestTVCmdComponent:
    def _mock_proc(self, returncode=0, stdout="", stderr=""):
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_adb_command_sent_for_fire_tv(self):
        comp = TVCmdComponent()
        req = _make_request(TVPlatform.AMAZON_FIRETV, "Enter", status=RequestStatus.EXECUTING)
        with patch("automation.tv_cmd.subprocess.run", return_value=self._mock_proc()) as mock_run:
            out = comp.execute(_inp(req))
        assert out.success is True
        cmd = mock_run.call_args[0][0]
        assert "adb" in cmd
        assert "keyevent" in cmd

    def test_device_from_constructor(self):
        comp = TVCmdComponent(device="10.0.0.5:5555")
        req = _make_request(TVPlatform.AMLOGIC, "Enter", status=RequestStatus.EXECUTING)
        with patch("automation.tv_cmd.subprocess.run", return_value=self._mock_proc()) as mock_run:
            out = comp.execute(_inp(req))
        cmd = mock_run.call_args[0][0]
        assert "-s" in cmd
        assert "10.0.0.5:5555" in cmd

    def test_device_from_metadata_overrides_constructor(self):
        comp = TVCmdComponent(device="default:5555")
        req = _make_request(TVPlatform.AMAZON_FIRETV, "Enter", status=RequestStatus.EXECUTING)
        with patch("automation.tv_cmd.subprocess.run", return_value=self._mock_proc()) as mock_run:
            out = comp.execute(_inp(req, metadata={"device": "override:5555"}))
        cmd = mock_run.call_args[0][0]
        assert "override:5555" in cmd
        assert "default:5555" not in cmd

    def test_linux_av_command_sent(self):
        comp = TVCmdComponent()
        req = _make_request(TVPlatform.LINUX_AV, " ", status=RequestStatus.EXECUTING)
        with patch("automation.tv_cmd.subprocess.run", return_value=self._mock_proc()) as mock_run:
            out = comp.execute(_inp(req))
        assert out.success is True
        cmd = mock_run.call_args[0][0]
        assert "playerctl" in cmd

    def test_output_result_contains_expected_keys(self):
        comp = TVCmdComponent()
        req = _make_request(TVPlatform.AMAZON_FIRETV, "ArrowUp", status=RequestStatus.APPROVED)
        with patch("automation.tv_cmd.subprocess.run", return_value=self._mock_proc(stdout="ok")):
            out = comp.execute(_inp(req))
        assert out.result["platform"] == "amazon_firetv"
        assert out.result["key"] == "ArrowUp"
        assert "cmd" in out.result
        assert out.result["stdout"] == "ok"

    def test_unknown_platform_key_returns_error(self):
        comp = TVCmdComponent()
        req = _make_request(TVPlatform.AMAZON_FIRETV, "F99", status=RequestStatus.APPROVED)
        with patch("automation.tv_cmd.subprocess.run"):
            out = comp.execute(_inp(req))
        assert out.success is False
        assert "F99" in out.error

    def test_command_not_found_returns_error(self):
        comp = TVCmdComponent()
        req = _make_request(TVPlatform.AMAZON_FIRETV, "Enter", status=RequestStatus.APPROVED)
        with patch("automation.tv_cmd.subprocess.run", side_effect=FileNotFoundError):
            out = comp.execute(_inp(req))
        assert out.success is False
        assert "not found" in out.error

    def test_timeout_returns_error(self):
        comp = TVCmdComponent()
        req = _make_request(TVPlatform.AMAZON_FIRETV, "Enter", status=RequestStatus.APPROVED)
        with patch("automation.tv_cmd.subprocess.run", side_effect=subprocess.TimeoutExpired("adb", 10)):
            out = comp.execute(_inp(req))
        assert out.success is False
        assert "timed out" in out.error

    def test_nonzero_exit_returns_error(self):
        comp = TVCmdComponent()
        req = _make_request(TVPlatform.AMAZON_FIRETV, "Enter", status=RequestStatus.APPROVED)
        with patch("automation.tv_cmd.subprocess.run", return_value=self._mock_proc(returncode=1, stderr="no device")):
            out = comp.execute(_inp(req))
        assert out.success is False
        assert "code 1" in out.error


# ---------------------------------------------------------------------------
# PinkSyncFeedbackComponent
# ---------------------------------------------------------------------------

class TestPinkSyncFeedbackComponent:
    def _result_payload(self):
        return {"request_id": "abc", "platform": "amazon_firetv", "key": "Enter", "cmd": [], "stdout": ""}

    def test_dev_mode_returns_ok_without_http(self):
        comp = PinkSyncFeedbackComponent(mode=FeedbackMode.DEV)
        with patch("automation.tv_cmd.urllib.request.urlopen") as mock_urlopen:
            out = comp.execute(_inp(self._result_payload()))
        assert out.success is True
        mock_urlopen.assert_not_called()

    def test_preview_mode_returns_ok_without_http(self):
        comp = PinkSyncFeedbackComponent(mode=FeedbackMode.PREVIEW)
        with patch("automation.tv_cmd.urllib.request.urlopen") as mock_urlopen:
            out = comp.execute(_inp(self._result_payload()))
        assert out.success is True
        mock_urlopen.assert_not_called()

    def test_production_without_url_returns_error(self):
        comp = PinkSyncFeedbackComponent(mode=FeedbackMode.PRODUCTION)
        out = comp.execute(_inp(self._result_payload()))
        assert out.success is False
        assert "webhook_url" in out.error

    def test_production_posts_to_webhook(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        comp = PinkSyncFeedbackComponent(
            webhook_url="https://pinksync.example.com/hook",
            mode=FeedbackMode.PRODUCTION,
        )
        with patch("automation.tv_cmd.urllib.request.urlopen", return_value=mock_resp):
            out = comp.execute(_inp(self._result_payload()))
        assert out.success is True
        assert "pinksync_response" in out.result

    def test_production_url_error_returns_error(self):
        comp = PinkSyncFeedbackComponent(
            webhook_url="https://pinksync.example.com/hook",
            mode=FeedbackMode.PRODUCTION,
        )
        with patch(
            "automation.tv_cmd.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            out = comp.execute(_inp(self._result_payload()))
        assert out.success is False
        assert "webhook" in out.error.lower()


# ---------------------------------------------------------------------------
# render_shortcuts_html
# ---------------------------------------------------------------------------

class TestRenderShortcutsHtml:
    def test_returns_valid_html_string(self):
        html = render_shortcuts_html()
        assert "<!DOCTYPE html>" in html
        assert "<table>" in html
        assert "PinkFlow" in html

    def test_all_platforms_included_by_default(self):
        html = render_shortcuts_html()
        for platform in TVPlatform:
            assert platform.value in html

    def test_specific_platform_subset(self):
        html = render_shortcuts_html(platforms=[TVPlatform.LINUX_AV])
        assert "linux_av" in html
        assert "android_pie" not in html

    def test_queue_pending_rows_appear(self):
        q = BroadcastQueue(quorum=2)
        q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        html = render_shortcuts_html(queue=q)
        assert "Broadcast Queue" in html
        assert "alice" in html

    def test_no_queue_section_when_queue_empty(self):
        q = BroadcastQueue()
        html = render_shortcuts_html(queue=q)
        assert "Broadcast Queue" not in html

    def test_html_escaping_in_key_names(self):
        # keys are safe, but description/platform values should be escaped
        html = render_shortcuts_html(platforms=[TVPlatform.AMAZON_FIRETV])
        assert "<script>" not in html


# ---------------------------------------------------------------------------
# build_tv_pipeline
# ---------------------------------------------------------------------------

class TestBuildTvPipeline:
    def test_returns_automation_engine(self):
        from automation.engine import AutomationEngine
        q = BroadcastQueue()
        engine = build_tv_pipeline(q)
        assert isinstance(engine, AutomationEngine)

    def test_pipeline_has_expected_steps(self):
        q = BroadcastQueue()
        engine = build_tv_pipeline(q)
        defn = engine.automations()["process_shortcut_queue"]
        assert defn.steps == ["dao_vote_check", "tv_cmd_execute", "pinksync_feedback"]

    def test_listens_on_process_queue_trigger(self):
        q = BroadcastQueue()
        engine = build_tv_pipeline(q)
        defn = engine.automations()["process_shortcut_queue"]
        assert "shortcut.process_queue" in defn.triggers


# ---------------------------------------------------------------------------
# End-to-end pipeline
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_full_pipeline_success(self):
        q = BroadcastQueue(quorum=2)
        req = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        q.vote(req.request_id, voter="bob", approve=True)
        q.vote(req.request_id, voter="carol", approve=True)

        approved = q.pop_next_approved()
        assert approved is req
        assert req.status == RequestStatus.EXECUTING

        engine = build_tv_pipeline(q, mode=FeedbackMode.DEV)
        mock_proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch("automation.tv_cmd.subprocess.run", return_value=mock_proc):
            results = engine.trigger_type("shortcut.process_queue", payload=approved)

        assert len(results) == 1
        assert results[0].status == RunStatus.SUCCESS
        assert len(results[0].outputs) == 3

    def test_unapproved_request_fails_at_dao_gate(self):
        q = BroadcastQueue(quorum=2)
        req = q.submit(TVPlatform.AMAZON_FIRETV, "Enter", "alice")
        q.vote(req.request_id, voter="bob", approve=True)  # only 1 of 2

        engine = build_tv_pipeline(q, mode=FeedbackMode.DEV)
        with patch("automation.tv_cmd.subprocess.run") as mock_run:
            results = engine.trigger_type("shortcut.process_queue", payload=req)

        assert results[0].status == RunStatus.FAILED
        mock_run.assert_not_called()

    def test_linux_av_pipeline_success(self):
        q = BroadcastQueue(quorum=1)
        req = q.submit(TVPlatform.LINUX_AV, " ", "alice")
        q.vote(req.request_id, voter="bob", approve=True)

        approved = q.pop_next_approved()
        engine = build_tv_pipeline(q, mode=FeedbackMode.DEV)
        mock_proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch("automation.tv_cmd.subprocess.run", return_value=mock_proc) as mock_run:
            results = engine.trigger_type("shortcut.process_queue", payload=approved)

        assert results[0].status == RunStatus.SUCCESS
        cmd = mock_run.call_args[0][0]
        assert "playerctl" in cmd
