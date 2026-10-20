import json
import unittest

from petnova.content import load_config
from scripts.verificar_configuracao import collect_report, format_report


class TestConfigurationReport(unittest.TestCase):
    def test_credentials_never_appear_in_diagnostics(self):
        private = "private-value-should-never-appear"
        env = {name: private for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET",
            "YOUTUBE_REFRESH_TOKEN", "IG_USER_ID", "IG_ACCESS_TOKEN")}
        report = collect_report(load_config(), env)
        self.assertTrue(report["publishing"]["youtube_credentials_present"])
        self.assertTrue(report["publishing"]["instagram_credentials_present"])
        self.assertNotIn(private, json.dumps(report))
        self.assertNotIn(private, format_report(report))

    def test_missing_authorization_does_not_claim_accounts_are_missing(self):
        report = collect_report(load_config(), {})
        self.assertFalse(report["publishing"]["youtube_credentials_present"])
        self.assertFalse(report["publishing"]["enabled"])
        self.assertEqual(report["store"]["mode"], "demonstracao")
        self.assertFalse(report["store"]["checkout_enabled"])
        self.assertIn("validade das autorizações não são verificadas", report["note"])


if __name__ == "__main__":
    unittest.main()
