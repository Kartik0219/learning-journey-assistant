"""The committed React bundle (frontend/dist) that Flask serves at /app/.

Render's Python runtime has no Node, so the deploy ships this pre-built
bundle rather than building it. That makes two failure modes possible that
no other test would catch: the bundle missing from the repo, or an
index.html pointing at asset files that were never committed.
"""

import re

from src.deliver.app import SPA_DIST, create_app


def test_bundle_is_committed_and_self_consistent():
    index = SPA_DIST / "index.html"
    assert index.is_file(), "frontend/dist missing: run `npm run build` in frontend/, commit it"

    html = index.read_text(encoding="utf-8")
    assets = re.findall(r'(?:src|href)="/app/(assets/[^"]+)"', html)
    assert any(a.endswith(".js") for a in assets), "index.html references no JS bundle"
    for asset in assets:
        assert (SPA_DIST / asset).is_file(), f"index.html references missing {asset}"


def test_flask_serves_the_bundle_and_falls_back_for_client_routes():
    client = create_app().test_client()

    root = client.get("/app/")
    assert root.status_code == 200
    assert b'id="root"' in root.data

    js = re.search(rb'src="/app/(assets/[^"]+\.js)"', root.data).group(1).decode()
    assert client.get(f"/app/{js}").status_code == 200

    # A reload on a client-side route must still get the SPA shell.
    assert b'id="root"' in client.get("/app/study-plan").data
