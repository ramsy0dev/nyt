""" Channels page """

from nyt_ui import styles
from nyt_ui.templates import template

import reflex as rx

@template(route="/", title="Channels")
def channels() -> rx.Component:
    """The channels page.

    Returns:
        The UI for the channels page.
    """
    with open("README.md", encoding="utf-8") as readme:
        content = readme.read()
    
    return rx.markdown(content, component_map=styles.markdown_style)
