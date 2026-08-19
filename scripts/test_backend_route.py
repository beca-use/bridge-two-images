import unittest

from check_codex_image2_route import RouteError, inspect_route


class BackendRouteTests(unittest.TestCase):
    def test_requires_explicit_configuration_or_allowed_default(self):
        with self.assertRaises(RouteError):
            inspect_route({}, allow_default=False)
        report = inspect_route({}, allow_default=True)
        self.assertEqual((report.scheme, report.hostname), ("https", "apinebula.com"))
        self.assertFalse(report.configured)

    def test_rejects_remote_plain_http_but_allows_loopback(self):
        with self.assertRaises(RouteError):
            inspect_route({"CODEX_API_URL": "http://api.example.com/v1"}, False)

        for url in ("http://localhost:8080/v1", "http://127.0.0.1:8080/v1", "http://[::1]:8080/v1"):
            with self.subTest(url=url):
                self.assertEqual(inspect_route({"CODEX_API_URL": url}, False).scheme, "http")

    def test_rejects_url_credentials_query_fragment_and_invalid_port(self):
        urls = (
            "https://user:secret@example.com/v1",
            "https://example.com/v1?token=secret",
            "https://example.com/v1#private",
            "https://example.com:not-a-port/v1",
            "https://example.com:70000/v1",
            "https://trusted.example\\@evil.example/v1",
            "https://example.com/v1 path",
        )
        for url in urls:
            with self.subTest(url=url), self.assertRaises(RouteError):
                inspect_route({"CODEX_API_URL": url}, False)

    def test_whitespace_key_is_not_reported_as_present(self):
        report = inspect_route(
            {"CODEX_API_URL": "https://example.com/v1", "CODEX_API_KEY": "   "},
            False,
        )
        self.assertFalse(report.key_present)
        self.assertTrue(
            inspect_route(
                {"CODEX_API_URL": "https://example.com/v1", "CODEX_API_KEY": "secret"},
                False,
            ).key_present
        )


if __name__ == "__main__":
    unittest.main()
