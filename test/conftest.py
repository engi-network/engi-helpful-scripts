import pytest


@pytest.fixture(scope="session")
def csharp_repo_url():
    return "https://github.com/engi-network/demo-csharp.git"


@pytest.fixture(scope="session")
def csharp_patch_url():
    return "https://gist.githubusercontent.com/cck197/2bf955742b70f2599078352027244067/raw/b45b7cdbe84c547f7ef78012deb431600c0eee83/daf1b5b.patch"
