import reflex as rx

class State(rx.State):
    """Define empty state to allow access to rx.State.router."""
    
    @rx.var
    def video_id(self) -> str:
        return self.router.page.params.get("video_id", None)
