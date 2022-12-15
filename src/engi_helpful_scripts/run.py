import asyncio
import os
import tempfile
from asyncio.subprocess import PIPE
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter

from .log import log


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


async def run(cmd, log_cmd=None, raise_code=0, input=None):
    """log and run `cmd` optionally log `log_cmd` rather than `cmd` for when `cmd` contains secrets"""
    if log_cmd is None:
        log_cmd = cmd
    # don't log env vars
    # log_cmd = re.subn(r"\S+=\S+ ", "", log_cmd)[0]
    log.info(log_cmd)
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
