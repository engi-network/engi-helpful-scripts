import csv
import json
import os
import re
import shutil
from io import StringIO
from pathlib import Path
from shlex import quote as sh_quote

import requests

from .log import log
from .request import download_file
from .run import run


def get_github_cmd(github_token, github_cmd="gh"):
    # get a GitHub CLI command
    github_token = sh_quote(github_token)
    # don't ask 😆
    github_cmd = f"GITHUB_TOKEN='{github_token}' {github_cmd}"
    github_opts = (
        f"-- -c url.'https://{github_token}:@github.com/'.insteadOf='https://github.com/'"
    )
    # oh, alright then -- the -c option lets us use the GitHub personal access
    # token as the Git credential helper
    return (github_cmd, github_opts)


async def run_github(log_cmd, github_token=None, opts=True):
    (github_cmd, github_opts) = get_github_cmd(github_token)
    if not opts:
        github_opts = ""
    return await run(f"{github_cmd} {log_cmd} {github_opts}", log_cmd=f"gh {log_cmd}")


async def git_sync(branch, commit, no_clean=False):
    if no_clean:
        log.warning("no_clean, skipping git sync")
        return
    await run("git stash")
    if commit:
        await run(f"git checkout {commit}")
    elif branch:
        await run(f"git checkout {branch}")


async def git_apply_patch(url, dir="."):
    filename = await download_file(url, dir=dir)
    return await run(f"git apply {filename}")


async def git_diff(commit1, commit2, extra_args=""):
    """create a patch file"""
    return await run(f"git diff {commit1} {commit2}{extra_args}")


def all_one_char(string, char):
    return char * len(string) == string


class StatString(object):
    def __init__(self, filename, added, deleted):
        self.filename = filename
        self.added = filename in added
        self.deleted = filename in deleted

    @property
    def is_edit(self):
        return not (self.added or self.deleted)

    @property
    def is_add(self):
        return self.added

    @property
    def is_delet(self):
        return self.deleted

    def __repr__(self):
        return f"{self.filename=} {self.is_add=} {self.is_edit=} {self.is_delet=}"


def parse_git_diff_stat(cmd_output, cmd_added, cmd_deleted):
    added_set = set(cmd_added.splitlines())
    deleted_set = set(cmd_deleted.splitlines())
    stats = []
    for s in cmd_output.splitlines():
        ss = StatString(s, added_set, deleted_set)
        if ss is not None:
            stats.append(ss)

    return stats


async def get_git_branch():
    cmd_exit = await run("git rev-parse --abbrev-ref HEAD")
    return cmd_exit.stdout.strip()


async def get_git_commit(commit="HEAD"):
    cmd_exit = await run(f"git rev-parse --short {commit}")
    return cmd_exit.stdout.strip()


async def get_git_url():
    """crude function to get the remote URL"""
    cmd_exit = await run("git remote -v")
    url = cmd_exit.stdout.split()[1]
    # switch ssh for https
    if url.startswith("git@"):
        url = url.replace(":", "/").replace("git@", "https://")
    # remove credentials
    return re.subn(r"://\S+@", "://", url)[0]


async def git_diff_stat(commit1, commit2):
    """run git diff --stat and parse the output"""
    cmd_added = await git_diff(commit1, commit2, extra_args=" --name-only --diff-filter=A")
    cmd_deleted = await git_diff(commit1, commit2, extra_args=" --name-only --diff-filter=D")
    cmd_changed = await git_diff(commit1, commit2, extra_args=" --name-only")
    return parse_git_diff_stat(cmd_changed.stdout, cmd_added.stdout, cmd_deleted.stdout)


def get_github_token(github_token):
    if github_token is not None:
        return github_token
    else:
        return os.environ.get("GITHUB_TOKEN")


async def github_checkout(url, dest, github_token=None, no_clean=False):
    """check out code at GitHub URL <url> to local path <dest>"""
    url_ = "/".join(url.split("/")[-2:]).replace(".git", "")
    dest_path = Path(dest)
    if (dest_path / ".git").exists():
        if no_clean:
            log.warning(f"{dest} exists, skipping GitHub checkout")
            return False
        else:
            log.warning(f"{dest} exists, deleting")
            shutil.rmtree(dest)
            os.makedirs(dest_path)

    github_token = get_github_token(github_token)
    if github_token is not None:
        await run_github(f"repo clone {url_} {dest_path}", github_token=github_token)
    else:
        # no PAT, assume the repo under analysis is public
        await run(f"git clone {url} {dest_path}")
    return True


async def is_git_secrets():
    cmd_exit = await run("git secret list", raise_code=None)
    return cmd_exit.returncode == 0


async def get_git_secrets():
    try:
        private_key = "private_key.gpg"
        open(private_key, "w").write(os.environ["GPG_PRIVATE_KEY"].replace(",", "\n"))
        # import PGP private key from environment variable
        await run(f"gpg --batch --yes --pinentry-mode loopback --import {private_key}")
        passphrase = os.environ["GPG_PASSPHRASE"]
        # reveal secrets
        cmd = "git secret reveal"
        await run(f"{cmd} -p '{passphrase}'", log_cmd=cmd)
    except Exception as e:
        # the repo contains secret files that we failed to reveal
        # likely the calling process doesn't have access to the Engi private key
        log.exception(e)
        log.error(f"this repo contains the following secret files:")
        await is_git_secrets()
        log.error("you'll need to create these files manually")


async def github_check_url(url, github_token=None):
    github_token = get_github_token(github_token)
    if github_token is not None:
        (github_cmd, _) = get_github_cmd(github_token)
        cmd = f"repo view {url}"
        return await run(f"{github_cmd} {cmd}", log_cmd=cmd)
    else:
        return await run(f"git ls-remote {url}")


async def github_linguist(dest):
    cmd_exit = await run(f"github-linguist -j {dest}")
    return json.loads(cmd_exit.stdout)


def github_gist_raw_url(url, filename=None):
    """get the raw URL from gist URL"""
    r = requests.get(f"https://api.github.com/gists/{url.split('/')[-1]}")
    files = r.json()["files"]
    return (list(files.values())[0] if filename is None else files[filename])["raw_url"]


async def github_gist_create(input, filename=None, desc=None):
    """create a GitHub gist for binary `input` and return URL in `cmd_exit.stdout`"""
    filename = "" if filename is None else f" --filename {filename}"
    desc = "" if desc is None else f" --desc {desc}"
    cmd_exit = await run(f"gh gist create{filename}{desc} -", input=input)
    return cmd_exit


async def github_gist_delete(url):
    """delete a GitHub gist identified by `url`"""
    cmd_exit = await run(f"gh gist delete {url}")
    return cmd_exit


async def get_lizard_metrics(path, exclude=None):
    """run lizard to get the files, source lines of code and cyclomatic complexity of the code in path"""
    exclude_opt = "" if exclude is None else f" --exclude '{path}/{exclude}'"
    cmd_exit = await run(f"lizard {path} --csv --verbose{exclude_opt}")
    rows = list(csv.DictReader(StringIO(cmd_exit.stdout)))
    c = [int(r["CCN"]) for r in rows]
    return {
        "files": list(set([r["file"] for r in rows])),
        "sloc": sum([int(r["NLOC"]) for r in rows]),
        "cyclomatic": sum(c) / len(c),
    }
