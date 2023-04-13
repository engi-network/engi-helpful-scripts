from pathlib import Path

import pytest
from common import TestWithTmpDir
from engi_helpful_scripts.git import github_checkout
from engi_helpful_scripts.compose import get_docker_compose_test_service_cmd

class TestCheckout(TestWithTmpDir):
    @pytest.mark.asyncio
    @pytest.mark.dependency()
    async def test_should_get_test_service_cmd(self, tmpdir, csharp_repo_url):
        await github_checkout(csharp_repo_url, tmpdir)
        assert get_docker_compose_test_service_cmd(Path(tmpdir) / "docker-compose.yml") == 'dotnet test --logger "trx;LogFileName=$ENGI_WORKING_DIR/dotnet_test.trx" -r .'

