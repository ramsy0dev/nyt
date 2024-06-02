# Videos service
from nyt_ui.services.videos import Videos

# Channels service
# from nyt_ui.services.channels import Channels

class Classes:
    """
    Handle the initilization of all the used classes
    """
    def __init__(self) -> None:
        self.videos = Videos()
        # self.channels = Channels()
    

classes = Classes()
