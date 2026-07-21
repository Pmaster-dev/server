from automation import ServerMeshEngine, ServerProtocol


def test_register_server_tracks_id_group_protocols_and_labels():
    engine = ServerMeshEngine()

    node = engine.register_server(
        name="gateway",
        group="edge",
        protocols=[ServerProtocol.HTTPS, ServerProtocol.WSS],
        labels={"tier": "public", "region": "us-east"},
        server_id="srv-gateway",
    )

    assert node.server_id == "srv-gateway"
    assert node.name == "gateway"
    assert node.group == "edge"
    assert node.supports(ServerProtocol.HTTPS)
    assert node.labels["tier"] == "public"
    assert engine.list_group("edge")[0].server_id == "srv-gateway"


def test_connect_and_neighbors_with_navigation_labels():
    engine = ServerMeshEngine()
    edge = engine.register_server("edge", "edge", [ServerProtocol.HTTPS], server_id="srv-edge")
    core = engine.register_server("core", "core", [ServerProtocol.GRPC], server_id="srv-core")

    engine.connect(edge.server_id, core.server_id, label="ingress")

    neighbors = engine.neighbors(edge.server_id, label="ingress")
    assert [server.server_id for server in neighbors] == ["srv-core"]


def test_label_lookup_and_export():
    engine = ServerMeshEngine()
    edge = engine.register_server(
        "edge",
        "edge",
        [ServerProtocol.HTTPS],
        labels={"role": "gateway"},
        server_id="srv-edge",
    )
    core = engine.register_server(
        "core",
        "core",
        [ServerProtocol.GRPC],
        labels={"role": "backend"},
        server_id="srv-core",
    )
    engine.connect(edge.server_id, core.server_id, label="dispatch", bidirectional=True)

    found = engine.find_by_label("role", "backend")
    assert [server.server_id for server in found] == ["srv-core"]

    exported = engine.export()
    assert len(exported["servers"]) == 2
    assert len(exported["navigations"]) == 2
