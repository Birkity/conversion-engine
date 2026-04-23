import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agent.hubspot import client as hubspot_client
from agent.enrichment import jobs_playwright


class TestHubSpotDraftMetadata(unittest.TestCase):
    def test_upsert_contact_sets_tenacious_status_draft(self):
        with patch.object(hubspot_client, "_request", return_value={"id": "123"}) as mock_request:
            result = hubspot_client.upsert_contact(
                email="prospect@sink.trp1.internal",
                first_name="Alex",
                last_name="Rivera",
                company="Kin Analytics",
            )

        self.assertEqual(result["status"], "created")
        args = mock_request.call_args[0]
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[1], "/crm/v3/objects/contacts")
        body = args[2]
        self.assertEqual(body["properties"]["tenacious_status"], "draft")

    def test_update_contact_defaults_tenacious_status_draft(self):
        with patch.object(hubspot_client, "_request", return_value={"id": "123"}) as mock_request:
            hubspot_client.update_contact("123", {"hs_lead_status": "OPEN"})

        args = mock_request.call_args[0]
        self.assertEqual(args[0], "PATCH")
        self.assertEqual(args[1], "/crm/v3/objects/contacts/123")
        body = args[2]
        self.assertEqual(body["properties"]["tenacious_status"], "draft")

    def test_update_contact_preserves_explicit_tenacious_status(self):
        with patch.object(hubspot_client, "_request", return_value={"id": "123"}) as mock_request:
            hubspot_client.update_contact("123", {"tenacious_status": "review"})

        body = mock_request.call_args[0][2]
        self.assertEqual(body["properties"]["tenacious_status"], "review")


class _FakePage:
    def __init__(self):
        self.url = "https://www.linkedin.com/jobs/search/?keywords=acme"

    def goto(self, *_args, **_kwargs):
        raise AssertionError("goto must not be called when robots.txt disallows crawl")


class _FakeContext:
    def new_page(self):
        return _FakePage()


class _FakeBrowser:
    def __init__(self):
        self.closed = False

    def new_context(self, **_kwargs):
        return _FakeContext()

    def close(self):
        self.closed = True


class _FakeChromium:
    def __init__(self, browser):
        self._browser = browser

    def launch(self, headless=True):
        return self._browser


class _FakePlaywrightCM:
    def __init__(self, browser):
        self.chromium = _FakeChromium(browser)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestRobotsGate(unittest.TestCase):
    def test_scrape_job_velocity_blocks_when_robots_disallows(self):
        fake_browser = _FakeBrowser()

        fake_sync_api = SimpleNamespace(sync_playwright=lambda: _FakePlaywrightCM(fake_browser))
        fake_playwright_pkg = SimpleNamespace(sync_api=fake_sync_api)

        with patch.dict("sys.modules", {
            "playwright": fake_playwright_pkg,
            "playwright.sync_api": fake_sync_api,
        }):
            with patch.object(jobs_playwright, "_robots_allows", return_value=False):
                result = jobs_playwright.scrape_job_velocity("Acme")

        self.assertFalse(result["data_available"])
        self.assertEqual(result["source"], "robots_disallowed")
        self.assertTrue(fake_browser.closed)


if __name__ == "__main__":
    unittest.main()
