import os

import pytest
from engi_helpful_scripts.run import run, set_docker_tmp_volume


@pytest.mark.asyncio
async def test_should_be_able_to_run_command_with_stdin():
    cmd_exit = await run("wc -l", input=b"foo\n")
    assert cmd_exit.returncode == 0
    assert int(cmd_exit.stdout.strip()) == 1


@pytest.mark.asyncio
async def test_should_be_able_to_create_tmp_docker_volume():
    async with set_docker_tmp_volume(prefix="demo-python-") as tmpdir:
        assert tmpdir.exists()
        assert tmpdir.name in os.environ["ENGI_WORKING_DIR"]
        assert tmpdir.name == os.environ["ENGI_WORKING_VOL"]
    assert not tmpdir.exists()
    assert os.environ.get("ENGI_WORKING_DIR") == None
    assert os.environ.get("ENGI_WORKING_VOL") == None
