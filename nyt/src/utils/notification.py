import os
import notifypy
import functools

# NOTE: This is a temporary fix for the UnsupportedPlatform exception being raised
# by notifypy because we are using Python 3.12.
# PR: https://github.com/ms7m/notify-py/pull/55

notifypy.Notify._selected_notification_system = functools.partial(notifypy.Notify._selected_notification_system, override_windows_version_detection=True)

from nyt import constant

def send_notification(summary_text: str, message: str) -> None:
    """
    Sends a notification to the desktop.

    Args:
        summary_text (str): The text summary that will be placed as the title.
        message (str): The message body.
    
    Returns:
        None.
    """
    to_replace = "\\nyt\\src\\utils" if constant.PLATFORM == "win32" else "/nyt/src/utils"
    script_dir_name = os.path.dirname(__file__).replace(to_replace, "")

    notify = notifypy.Notify()
    
    notify.application_name = constant.PACKAGE
    notify.title = summary_text
    notify.message = message

    if constant.PLATFORM == "win32":
        icon_path = script_dir_name + "\\" + constant.NYT_HIGH_RESOLUTION_LOGO.replace("/", "\\")
    else:
        icon_path = script_dir_name + "/" + constant.NYT_HIGH_RESOLUTION_LOGO
    
    notify.icon = icon_path

    notify.send()
