from pathlib import Path

import requests


def check_url(url):
    assert requests.get(url).status_code == 200


async def download_file(url, dir="."):
    r = requests.get(url, stream=True)
    filename = url.split("/")[-1]
    with open(Path(dir) / filename, "wb") as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)
    return filename


def is_patch_file(url):
    """return True if url could be a patch file"""
    try:
        r = requests.head(url)
        return r.ok and "text/plain" in r.headers["Content-Type"]
    except:
        return False
