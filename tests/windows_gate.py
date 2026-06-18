import importlib
import unittest

_GATE_MODULES = (
    "tests.test_credential_store",
    "tests.test_qt_observer_static_contract",
    "tests.test_evaluation_versions",
    "tests.test_scoring",
    "tests.test_settlement_bundle",
    "tests.test_engine_to_scoring_e2e",
)


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for module_name in _GATE_MODULES:
        module = importlib.import_module(module_name)
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


if __name__ == "__main__":
    unittest.main()
