from pathlib import Path

import pytest
from common import TestWithTmpDir
from engi_helpful_scripts.request import download_file, is_patch_file


class TestDownload(TestWithTmpDir):
    @pytest.mark.asyncio
    async def test_should_be_able_to_download_file(self, tmpdir, csharp_patch_url):
        filename = await download_file(csharp_patch_url, tmpdir)
        assert Path(filename).exists()


def test_should_be_able_to_detect_patch(csharp_repo_url, csharp_patch_url):
    assert not is_patch_file(csharp_repo_url)
    assert is_patch_file(csharp_patch_url)
