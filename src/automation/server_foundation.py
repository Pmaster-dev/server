"""
Foundational topology engine for "server-of-servers" orchestration.

This module models:
- protocols supported by each server
- stable server names/IDs
- grouping
- navigation links
- label-based lookup
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Set


class ServerProtocol(str, Enum):
    """Supported server protocols."""

    HTTP = "http"
    HTTPS = "https"
    WS = "ws"
    WSS = "wss"
    GRPC = "grpc"
    TCP = "tcp"
    UDP = "udp"
    CUSTOM = "custom"


@dataclass(frozen=True)
class ServerNavigation:
    """Directed navigation edge from one server to another."""

    source_id: str
    target_id: str
    label: str
    navigation_id: str = field(default_factory=lambda: f"nav-{uuid.uuid4().hex[:12]}")


@dataclass
class ServerNode:
    """Core server entity tracked by the topology engine."""

    server_id: str
    name: str
    group: str
    protocols: Set[ServerProtocol] = field(default_factory=set)
    labels: Dict[str, str] = field(default_factory=dict)

    def supports(self, protocol: ServerProtocol) -> bool:
        """Return ``True`` if this server declares support for *protocol*."""
        return protocol in self.protocols


class ServerMeshEngine:
    """
    Minimal topology engine for grouped servers and labeled navigation.

    This intentionally keeps behavior simple so it can serve as a foundation
    for future scheduling/routing features.
    """

    def __init__(self) -> None:
        self._servers: Dict[str, ServerNode] = {}
        self._groups: Dict[str, Set[str]] = {}
        self._navigations: List[ServerNavigation] = []

    def register_server(
        self,
        name: str,
        group: str,
        protocols: Iterable[ServerProtocol],
        labels: Optional[Dict[str, str]] = None,
        server_id: Optional[str] = None,
    ) -> ServerNode:
        """Create and register a server node."""
        if not name.strip():
            raise ValueError("Server name cannot be empty")
        if not group.strip():
            raise ValueError("Server group cannot be empty")

        resolved_id = server_id or f"srv-{uuid.uuid4().hex[:12]}"
        if resolved_id in self._servers:
            raise ValueError(f"Server id '{resolved_id}' already exists")

        protocol_set = set(protocols)
        if not protocol_set:
            raise ValueError("At least one protocol is required")

        server = ServerNode(
            server_id=resolved_id,
            name=name,
            group=group,
            protocols=protocol_set,
            labels=dict(labels or {}),
        )
        self._servers[resolved_id] = server
        self._groups.setdefault(group, set()).add(resolved_id)
        return server

    def server(self, server_id: str) -> ServerNode:
        """Return a server by ID or raise ``KeyError``."""
        return self._servers[server_id]

    def connect(
        self,
        source_id: str,
        target_id: str,
        label: str,
        *,
        bidirectional: bool = False,
    ) -> List[ServerNavigation]:
        """Create one or two labeled navigation links between servers."""
        if source_id not in self._servers:
            raise KeyError(f"Unknown source server '{source_id}'")
        if target_id not in self._servers:
            raise KeyError(f"Unknown target server '{target_id}'")
        if not label.strip():
            raise ValueError("Navigation label cannot be empty")

        created = [ServerNavigation(source_id=source_id, target_id=target_id, label=label)]
        if bidirectional:
            created.append(ServerNavigation(source_id=target_id, target_id=source_id, label=label))

        self._navigations.extend(created)
        return created

    def list_group(self, group: str) -> List[ServerNode]:
        """Return all servers in *group* ordered by server ID."""
        ids = sorted(self._groups.get(group, set()))
        return [self._servers[server_id] for server_id in ids]

    def find_by_label(self, key: str, value: str) -> List[ServerNode]:
        """Return servers where labels[key] == value."""
        matches = [
            server
            for server in self._servers.values()
            if server.labels.get(key) == value
        ]
        return sorted(matches, key=lambda item: item.server_id)

    def neighbors(self, server_id: str, label: Optional[str] = None) -> List[ServerNode]:
        """Return direct target servers navigable from *server_id*."""
        if server_id not in self._servers:
            raise KeyError(f"Unknown server '{server_id}'")

        target_ids: List[str] = []
        for edge in self._navigations:
            if edge.source_id != server_id:
                continue
            if label is not None and edge.label != label:
                continue
            target_ids.append(edge.target_id)

        return [self._servers[target_id] for target_id in target_ids]

    def export(self) -> Dict[str, object]:
        """Export a serializable view of the topology."""
        servers = [
            {
                "server_id": node.server_id,
                "name": node.name,
                "group": node.group,
                "protocols": sorted(protocol.value for protocol in node.protocols),
                "labels": dict(node.labels),
            }
            for node in sorted(self._servers.values(), key=lambda item: item.server_id)
        ]
        navigations = [
            {
                "navigation_id": edge.navigation_id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "label": edge.label,
            }
            for edge in self._navigations
        ]
        return {"servers": servers, "navigations": navigations}
