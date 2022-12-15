import pytest
from engi_helpful_scripts.run import set_tmpdir


class TestWithTmpDir:
    @pytest.fixture(scope="class")
    def tmpdir(self):
        with set_tmpdir() as tmpdir:
            yield tmpdir
