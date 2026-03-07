from requests import Session
from typing import Iterable, TypedDict
from . import config, utils


class VideoInfo(TypedDict):
    playlist_id: str
    index: int
    video_id: str
    title: str


def fetch_continuation(
    session: Session,
    playlist_id: str,
    continuation_token: str,
    video_index: int,
) -> Iterable[VideoInfo]:
    with session.post(
        "https://www.youtube.com/youtubei/v1/browse",
        params={
            "prettyPrint": False,
        },
        json={
            "context": {
                "client": {
                    "userAgent": config.USER_AGENT,
                    "clientName": "WEB",
                    "clientVersion": "2.20260206.08.00",
                    "osName": "X11",
                    "osVersion": "",
                    "originalUrl": f"https://www.youtube.com/playlist?list={playlist_id}",
                    "screenPixelDensity": 2,
                    "platform": "DESKTOP",
                    "clientFormFactor": "UNKNOWN_FORM_FACTOR",
                },
            },
            "continuation": continuation_token,
        },
        headers={
            "referrer": f"https://www.youtube.com/playlist?list={playlist_id}",
        },
    ) as resp:
        resp.raise_for_status()
        content = resp.json()
        continuationItems = utils.get_nested_item(
            content,
            "onResponseReceivedActions",
            utils.ListExactlyOne,
            "appendContinuationItemsAction",
            "continuationItems",
        )

        continuationItemRenderer_found: bool = False
        for video_index, continuationItem in enumerate(
            continuationItems, start=video_index
        ):
            continuationItemRenderer = continuationItem.get("continuationItemRenderer")
            if continuationItemRenderer_found:
                raise ValueError(
                    "continuationItemRenderer can only occure at max 1 time and it should be at last."
                )
            elif continuationItemRenderer is not None:
                continuationItemRenderer_found = True
                yield from fetch_continuation(
                    session,
                    playlist_id,
                    continuation_token=utils.get_nested_item(
                        continuationItemRenderer,
                        "continuationEndpoint",
                        "continuationCommand",
                        "token",
                    ),
                    video_index=video_index,
                )
            else:
                playlistVideoRenderer = continuationItem["playlistVideoRenderer"]
                video_id = playlistVideoRenderer["videoId"]
                yield VideoInfo(
                    playlist_id=playlist_id,
                    index=video_index,
                    video_id=video_id,
                    title=utils.get_nested_item(
                        playlistVideoRenderer,
                        "title",
                        "runs",
                        utils.ListExactlyOne,
                        "text",
                    ),
                )
