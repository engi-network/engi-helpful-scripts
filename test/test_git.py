from pathlib import Path

import pytest
from dotenv import dotenv_values
from engi_helpful_scripts.git import (
    get_git_secrets,
    git_apply_patch,
    github_checkout,
    github_gist_create,
    github_gist_delete,
    github_gist_raw_url,
    github_linguist,
    is_git_secrets,
)
from engi_helpful_scripts.request import check_url
from engi_helpful_scripts.run import run, set_tmpdir


class TestWithTmpDir:
    @pytest.fixture(scope="class")
    def tmpdir(self):
        with set_tmpdir() as tmpdir:
            yield tmpdir


class TestGist:
    @pytest.fixture(scope="class", autouse=True)
    def variables(self):
        yield {}

    @pytest.mark.asyncio
    @pytest.mark.dependency()
    async def test_should_be_able_to_create_gist(self, variables):
        cmd_exit = await github_gist_create(input=b"foo")
        assert cmd_exit.returncode == 0
        variables["url"] = cmd_exit.stdout.strip()
        check_url(variables["url"])

    @pytest.mark.asyncio
    @pytest.mark.dependency(depends=["TestGist::test_should_be_able_to_create_gist"])
    async def test_should_be_able_to_get_gist_raw_url(self, variables):
        check_url(github_gist_raw_url(variables["url"]))

    @pytest.mark.asyncio
    @pytest.mark.dependency(depends=["TestGist::test_should_be_able_to_create_gist"])
    async def test_should_be_able_to_get_gist_raw_url(self, variables):
        check_url(github_gist_raw_url(variables["url"]))

    @pytest.mark.asyncio
    @pytest.mark.dependency(depends=["TestGist::test_should_be_able_to_get_gist_raw_url"])
    async def test_should_be_able_to_delete_gist(self, variables):
        cmd_exit = await github_gist_delete(variables["url"])
        assert cmd_exit.returncode == 0


class TestCheckout(TestWithTmpDir):
    @pytest.mark.asyncio
    @pytest.mark.dependency()
    async def test_should_be_able_checkout_repo(self, tmpdir, csharp_repo_url):
        await github_checkout(csharp_repo_url, tmpdir)
        assert Path(tmpdir) / ".git"

    @pytest.mark.asyncio
    @pytest.mark.dependency(depends=["TestCheckout::test_should_be_able_checkout_repo"])
    async def test_should_be_able_to_apply_patch(self, csharp_patch_url):
        await git_apply_patch(csharp_patch_url)

    @pytest.mark.asyncio
    @pytest.mark.dependency(depends=["TestCheckout::test_should_be_able_checkout_repo"])
    async def test_should_be_able_to_run_linguist(self, tmpdir):
        breakdown = await github_linguist(tmpdir)
        print(f"{breakdown=}")
        assert "C#" in breakdown

    @pytest.mark.asyncio
    @pytest.mark.dependency(depends=["TestCheckout::test_should_be_able_checkout_repo"])
    async def test_should_be_able_to_run_git_stash(self):
        cmd_exit = await run("git stash")
        assert cmd_exit.returncode == 0


class TestSecrets(TestWithTmpDir):
    @pytest.mark.asyncio
    @pytest.mark.dependency()
    async def test_should_git_secrets_detect(self, tmpdir):
        await github_checkout("https://github.com/engi-network/demo-secrets.git", tmpdir)
        assert await is_git_secrets()

    @pytest.mark.asyncio
    @pytest.mark.dependency(depends=["TestSecrets::test_should_git_secrets_detect"])
    async def test_should_git_secrets_get(self):
        dotenv = ".env"
        assert not Path(dotenv).exists()
        await get_git_secrets()
        assert dotenv_values(dotenv) == {"KEY": "VAL"}
