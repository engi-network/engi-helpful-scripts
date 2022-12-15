import pytest
from engi_helpful_scripts.run import run


@pytest.mark.asyncio
async def test_should_be_able_to_run_command_with_stdin():
    cmd_exit = await run("wc -l", input=b"foo\n")
    assert cmd_exit.returncode == 0
    assert int(cmd_exit.stdout.strip()) == 1
