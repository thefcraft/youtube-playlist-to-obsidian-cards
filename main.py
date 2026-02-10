import typer
import json
import os
import re
from textwrap import dedent
from src.config import change_dir_to_root, create_session, USER_AGENT
from src.parser import (
    ParserError,
    parser_url_and_get_playlist_id,
    get_json_from_content,
)
from src import utils
from requests import Session
from typing import Iterable
from pathlib import Path

app = typer.Typer(
    pretty_exceptions_enable=False,
    pretty_exceptions_short=False,
    pretty_exceptions_show_locals=False,
)


def safe_filename(name: str, playlist_id: str) -> str:
    """Make a safe filename from playlist title."""
    name = re.sub(r"[^\w\s.-]", "", name)
    name = re.sub(r"\s+", "_", name).strip("_")
    return name or f"playlist - {playlist_id}"


def make_card(playlist_id: str, index: int, video_id: str, title: str) -> str:
    title = title.replace('"', '\\"')
    # NOTE: fetching description is not necessary for this a todo tracker.
    # NOTE: we can fetch using asyncio if we wanted
    return dedent(f"""
    {index}. [ ] **"{title}"**
    ```cardlink
    url: https://www.youtube.com/watch?v={video_id}&list={playlist_id}&index={index}
    title: "{title}"
    host: www.youtube.com
    favicon: https://m.youtube.com/static/favicon.ico
    image: https://i.ytimg.com/vi/{video_id}/hqdefault.jpg
    ```
    """).strip()


def fetch_continuation(
    session: Session,
    playlist_id: str,
    continuation_token: str,
    video_index: int,
) -> Iterable[str]:
    with session.post(
        "https://www.youtube.com/youtubei/v1/browse",
        params={
            "prettyPrint": False,
        },
        json={
            "context": {
                "client": {
                    "userAgent": USER_AGENT,
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
            if continuationItemRenderer is not None:
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
                continue
            playlistVideoRenderer = continuationItem["playlistVideoRenderer"]
            video_id = playlistVideoRenderer["videoId"]
            yield make_card(
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


@app.command()
def main(
    url: str,
    cached: bool = typer.Option(False, help="Use cached HTTP session"),
    out: Path | None = typer.Option(
        None,
        "--out",
        "-o",
        help="Output markdown file (default: playlist_title.md)",
        exists=False,
        dir_okay=False,
    ),
    chdir: Path | None = typer.Option(
        "output",
        "--chdir",
        "-C",
        help="Change directory before writing output",
        exists=False,
        file_okay=False,
    ),
    stdout: bool = typer.Option(
        False,
        help="Print cards to stdout instead of writing a file",
    ),
    title_as_filename: bool = typer.Option(
        True,
        help="Use playlist title as filename when --out not provided",
    ),
    force: bool = typer.Option(
        False,
        help="Overwrite existing file",
    ),
):
    try:
        playlist_id = parser_url_and_get_playlist_id(url)
    except ParserError as e:
        raise typer.BadParameter(e.msg)
    typer.secho(f"playlist ID: {playlist_id}", fg=typer.colors.GREEN)

    change_dir_to_root()
    if chdir:
        typer.secho(f"cd → {chdir}", fg=typer.colors.BRIGHT_BLUE)
        chdir.mkdir(parents=True, exist_ok=True)
        os.chdir(chdir)

    session = create_session(cached=cached)

    # ---- FETCH INITIAL PAGE ----
    with session.get(
        url=f"https://www.youtube.com/playlist?list={playlist_id}"
    ) as resp:
        resp.raise_for_status()
        ytInitialData = json.loads(
            get_json_from_content(
                resp.content, name=b"var ytInitialData = ", prefix=b"", postfix=b""
            )
        )

        title = utils.get_nested_item(
            ytInitialData,
            "metadata",
            "playlistMetadataRenderer",
            "title",
        )

    typer.secho(f"TITLE: {title}", fg=typer.colors.BRIGHT_YELLOW)

    # ---- DETERMINE OUTPUT PATH ----
    out_path: Path | None = None
    if not stdout:
        if out is None and title_as_filename:
            out = Path(f"{safe_filename(title, playlist_id=playlist_id)}.md")
        elif out is None:
            out = Path(f"playlist - {playlist_id}")

        if out.exists() and not force:
            raise typer.BadParameter(
                f"{out} already exists. Use --force to overwrite."
            )

        out_path = out


    # ---- EXTRACT CONTENTS ----
    contents = utils.get_nested_item(
        ytInitialData,
        "contents",
        "twoColumnBrowseResultsRenderer",
        "tabs",
        utils.ListExactlyOne,
        "tabRenderer",
        "content",
        "sectionListRenderer",
        "contents",
        utils.ListExactlyOneChildDictKey,
        "itemSectionRenderer",
        "contents",
        utils.ListExactlyOneChildDictKey,
        "playlistVideoListRenderer",
        "contents",
    )
    continuationItemRenderer_found: bool = False
    cards: list[str] = []
    for video_index, content in enumerate(contents, start=1):
        continuationItemRenderer = content.get("continuationItemRenderer")
        if continuationItemRenderer_found:
            raise ValueError(
                "continuationItemRenderer can only occure at max 1 time and it should be at last."
            )
        if continuationItemRenderer is not None:
            continuationItemRenderer_found = True
            cards.extend(
                fetch_continuation(
                    session,
                    playlist_id,
                    continuation_token=utils.get_nested_item(
                        continuationItemRenderer,
                        "continuationEndpoint",
                        "commandExecutorCommand",
                        "commands",
                        utils.ListExactlyOneChildDictKey,
                        "continuationCommand",
                        "token",
                    ),
                    video_index=video_index,
                )
            )
            continue
        playlistVideoRenderer = content["playlistVideoRenderer"]
        video_id = playlistVideoRenderer["videoId"]
        card = make_card(
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
        cards.append(card)

    result = "\n".join(cards)

    if stdout:
        typer.echo(result)
    else:
        if out_path is None:
            raise RuntimeError("UNLIKELY.")
        out_path.write_text(result, encoding="utf-8")
        typer.secho(f"Wrote {len(cards)} cards → {out_path}", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
