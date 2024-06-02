""" Video component """

import reflex as rx

    # "width": "1280px",
    # "height": "720px",

thumbnail_style = {
    "width": "300px",
    "height": "200px",
    "border-radius": "20px",
}

def video_comp(video_id: str, video_title: str, channel_handle: str, channel_avatar_url_default: str, thumbnail_url: str) -> rx.Component:
    """
    The video component
    """
    return rx.card(
        rx.vstack(
            rx.image(
                src=thumbnail_url,
                style=thumbnail_style
            ),
            rx.spacer(
                direction="row",
                spacing="9"
            ),
            rx.hstack(
                rx.avatar(
                    src=channel_avatar_url_default,
                    radius="medium"
                ),
                rx.vstack(
                    rx.text(video_title, size="3"),
                    rx.text(channel_handle, size="2")
                )
            ),
        ),
        style={
            "width": thumbnail_style["width"]
        },
        as_child=True,
        variant="surface",
        on_click=rx.redirect(path="/videos/" + video_id)
    )
