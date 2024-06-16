import notifypy
import functools

def send_notification(app_name: str, summary_text: str, message: str, icon_path: str) -> None:
    """
    Sends a notification to the desktop.

    Args:
        summary_text (str): The text summary that will be placed as the title.
        message (str): The message body.
    
    Returns:
        None.
    """
    notify = notifypy.Notify()
    
    notify.application_name = app_name
    notify.title = summary_text
    notify.message = message
    notify.icon = icon_path 
    
    notify.send()

