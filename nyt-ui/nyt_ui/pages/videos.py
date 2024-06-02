"""The dashboard page."""

import reflex as rx

from nyt_ui.templates import template

# Classes
from nyt_ui.classes import classes

# Components
from nyt_ui.components.video import video_comp

# State
from nyt_ui.state import State


@template(route="/videos", title="Videos Library")
def videos() -> rx.Component:
    """The videos library page.

    Returns:
        The UI for the videos library page.
    """
    videos_list = classes.videos.get_videos_list()

    videos_components = list()

    for video in videos_list:
        video = video_comp(
            video_id=video.video_id,
            video_title=video.video_title,
            thumbnail_url=video.thumbnail_url,
            channel_avatar_url_default=video.channel_avatar_url_default,
            channel_handle=video.channel_handle
        )

        print(f"{video = }")

        videos_components.append(video)

    return rx.vstack(
        rx.heading("Videos Library", size="8"),
        rx.flex(
            rx.hstack(
                *videos_components
            ),
            direction="row-reverse"
        ),
    )

@template(route="/videos/[video_id]", title="Watch videos")
def watch_video() -> rx.Component:
    """ Watch a video """
    # print(f"{video_id = }")
    video_id = State.video_id

    print(f"WATCH_VIDEO: {dir(video_id) = }")
    return rx.video(
        url=f"http://localhost:8888/api/v1/videos/{video_id}",
        width="1280px",
        height="720px"
    )
