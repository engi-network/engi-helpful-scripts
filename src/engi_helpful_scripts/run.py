import asyncio
import os
import tempfile
from asyncio.subprocess import PIPE
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from time import perf_counter

from .log import log

SUBPROCESS_TIMEOUT_SECS = 3600

@contextmanager
def set_directory(path):
    origin = Path().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)


@contextmanager
def set_tmpdir():
    with tempfile.TemporaryDirectory() as tmpdir:
        with set_directory(tmpdir):
            yield tmpdir


@asynccontextmanager
async def set_docker_tmp_volume(
    prefix=None, working_dir_env_var="ENGI_WORKING_DIR", volume_env_var="ENGI_WORKING_VOL"
):
    with tempfile.TemporaryDirectory(prefix=prefix) as tmpdir:
        # the volume name is the tmp dir basename
        tmpdir_p = Path(tmpdir)
        # create the external volume
        await run(
            f"docker volume create --driver local -o o=bind -o type=none -o device='{tmpdir}' {tmpdir_p.name}"
        )
        # set the environment variables for use in a docker-compose.yml
        os.environ[working_dir_env_var] = tmpdir
        os.environ[volume_env_var] = tmpdir_p.name
        # do your thing in docker
        yield tmpdir_p
        # remove the volume and delete the environment variables
        await run(f"docker volume rm {tmpdir_p.name}")
        del os.environ[working_dir_env_var]
        del os.environ[volume_env_var]


class CmdExit(object):
    def __init__(self, returncode=None, stdout=None, stderr=None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class CmdError(Exception):
    def __init__(self, cmd, cmd_exit):
        self.cmd = cmd
        self.cmd_exit = cmd_exit

    def __repr__(self):
        return (
            f"{self.cmd!r} exited with return code {self.cmd_exit.returncode}\n"
            f"stdout: {self.cmd_exit.stdout}\n"
            f"stderr: {self.cmd_exit.stderr}"
        )


async def log_stream(stream):
    result = ""
    async for line in stream:
        decoded = line.decode()
        result += decoded
        log.info(decoded.strip())
    return result


async def timeout_task(cmd, log_cmd=None, raise_code=0, input=None):
    t1_start = perf_counter()
    proc = await asyncio.create_subprocess_shell(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdin, stdout, stderr = await asyncio.gather(
        proc._noop() if input is None else proc._feed_stdin(input),
        log_stream(proc.stdout),
        log_stream(proc.stderr),
    )
    await proc.wait()
    t1_stop = perf_counter()

    log.info(
        f"{log_cmd!r} exited with code {proc.returncode} elapsed {t1_stop - t1_start} seconds"
    )
    cmd_exit = CmdExit(proc.returncode, stdout, stderr)
    if raise_code is not None and proc.returncode != raise_code:
        log.error(stderr)
        raise CmdError(log_cmd, cmd_exit)

    return cmd_exit


async def run(cmd, log_cmd=None, raise_code=0, input=None):
    """log and run `cmd` optionally log `log_cmd` rather than `cmd` for when `cmd` contains secrets"""
    if log_cmd is None:
        log_cmd = cmd
    # don't log env vars
    # log_cmd = re.subn(r"\S+=\S+ ", "", log_cmd)[0]
    log.info(log_cmd)
    cmd_exit = await asyncio.wait_for(timeout_task(cmd, log_cmd, raise_code, input), SUBPROCESS_TIMEOUT_SECS)

    return cmd_exit
