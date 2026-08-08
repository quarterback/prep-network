"""
standard.site records must be publishable as written, or the failure is silent.

A malformed record is rejected by the PDS at publish time, which is fine. The
dangerous case is a record that publishes cleanly and points nowhere: a <link>
tag carrying an AT-URI no consumer can resolve, or a document whose `path`
doesn't match the page it claims to describe. Both look correct in a diff.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


news = _load("fh_news", "site/news.py")


@pytest.fixture
def unpublished(monkeypatch):
    monkeypatch.setenv("FH_PUB_URI", "")
    return _load("fh_stdsite_unpub", "site/standardsite.py")


@pytest.fixture
def published(monkeypatch):
    monkeypatch.setenv("FH_PUB_URI", "at://did:plc:test/site.standard.publication/self")
    return _load("fh_stdsite_pub", "site/standardsite.py")


def test_publication_carries_the_lexicon_required_fields(unpublished):
    pub = unpublished.publication()
    assert pub["$type"] == "site.standard.publication"
    assert pub["name"] and pub["description"]
    assert pub["url"].startswith("https://") and not pub["url"].endswith("/")


def test_theme_channels_are_bytes(unpublished):
    """RGB out of range publishes fine and renders wrong in every consumer."""
    theme = unpublished.publication()["basicTheme"]
    assert theme["$type"] == "site.standard.theme.basic"
    for slot in ("background", "foreground", "accent", "accentForeground"):
        for channel in "rgb":
            assert 0 <= theme[slot][channel] <= 255


def test_document_path_matches_the_page_the_build_emits(unpublished):
    """`path` is the whole point of the record — it's how a reader gets back."""
    for st in news.STORIES:
        assert unpublished.document(st)["path"] == f"/news/{st['slug']}/"


def test_published_at_is_rfc3339(unpublished):
    for st in news.STORIES:
        stamp = unpublished.document(st)["publishedAt"]
        assert stamp.endswith("Z") and stamp[10] == "T" and len(stamp) == 20


def test_rkeys_are_unique_so_stories_do_not_overwrite_each_other(unpublished):
    keys = [unpublished.rkey(st) for st in news.STORIES]
    assert len(keys) == len(set(keys))


def test_no_link_tags_until_the_publication_record_exists(unpublished):
    """An unresolvable AT-URI in a rel tag is worse than none: a consumer
    fetches it and fails, rather than concluding the site doesn't participate."""
    assert unpublished.head_links() == ""
    assert unpublished.head_links(news.STORIES[0]) == ""


def test_link_tags_resolve_to_the_same_repo(published):
    """The document URI is derived from the publication's DID; if they diverge,
    verification fails against a repo that doesn't hold the record."""
    st = news.STORIES[0]
    tags = published.head_links(st)
    assert f'rel="site.standard.publication" href="{published.PUB_URI}"' in tags
    did = published.PUB_URI.split("/")[2]
    assert f'href="at://{did}/site.standard.document/{published.rkey(st)}"' in tags


def test_ordinary_pages_claim_the_publication_but_not_a_document(published):
    assert "site.standard.publication" in published.head_links()
    assert "site.standard.document" not in published.head_links()
