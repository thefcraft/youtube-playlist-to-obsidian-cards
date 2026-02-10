import os
from requests import Session

USER_AGENT: str = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0"

def change_dir_to_root():
    basedir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(basedir, "..")
    os.chdir(root)


def create_session(cached: bool = False) -> Session:
    if not cached:
        session = Session()
    else:
        from cached_requests import CacheSession, CacheConfig
        from cached_requests.backend import FileCacheBackend
        from datetime import timedelta

        config = CacheConfig(
            cache_backend=FileCacheBackend(cache_dir=".http_cache"),
            refresh_after=timedelta(days=1),
        )
        session = CacheSession(config=config)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Priority": "u=0, i",
            "TE": "trailers",
        }
    )
    return session
