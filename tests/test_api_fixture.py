import subprocess
import types
import unittest
from unittest.mock import Mock, patch
import api_e2e


class FixtureCleanupRegressions(unittest.TestCase):
    def fixture(self):
        return types.SimpleNamespace(server=Mock(pid=12345), db_name='hwc_e2e_cleanup_test',
                                     mongo=Mock(), log=Mock(), ini=Mock())

    def assert_resources_closed(self, fixture):
        fixture.mongo.drop_database.assert_called_once_with(fixture.db_name)
        fixture.mongo.close.assert_called_once()
        fixture.log.close.assert_called_once()
        fixture.ini.close.assert_called_once()

    def test_already_exited_server_still_cleans_database(self):
        fixture = self.fixture()
        with patch('api_e2e.os.killpg', side_effect=ProcessLookupError):
            api_e2e.ApiE2E.tearDownClass.__func__(fixture)
        self.assert_resources_closed(fixture)

    def test_server_exits_between_timeout_and_kill(self):
        fixture = self.fixture()
        fixture.server.wait.side_effect = [subprocess.TimeoutExpired('uwsgi', 5), 0]
        with patch('api_e2e.os.killpg', side_effect=[None, ProcessLookupError]):
            api_e2e.ApiE2E.tearDownClass.__func__(fixture)
        self.assert_resources_closed(fixture)

    def test_failed_process_creation_still_cleans_resources(self):
        fixture = self.fixture()
        fixture.server = None
        api_e2e.ApiE2E.tearDownClass.__func__(fixture)
        self.assert_resources_closed(fixture)


if __name__ == '__main__':
    unittest.main(verbosity=2)
