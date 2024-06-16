from fastapi import (
    FastAPI,
    Header
)
from fastapi.responses import (
    RedirectResponse,
    ORJSONResponse,
    StreamingResponse
)

from nyt.src.api.classes import classes
from nyt.src.api import constant as api_constant

# Utils
from nyt.src.utils.range_header import parse_range_header

# Init api
api = FastAPI()

@api.get("/", status_code=200)
async def home_route():
    """ Home route """
    return RedirectResponse(
        url=api_constant.ROOT_API_ROUTE
    )

@api.get(api_constant.ROOT_API_ROUTE, status_code=200, response_class=ORJSONResponse)
async def root_route():
    """ Root route """
    return ORJSONResponse(
        [
            {
                "code": 200
            }
        ]
    )

@api.get(f"{api_constant.ROOT_API_ROUTE}/channels", status_code=200, response_class=ORJSONResponse)
async def root_channels_route():
    """ Root channels route """
    return ORJSONResponse(
        [
            {
                "code": 200,
                "message": "root channels route"
            }
        ]
    )

@api.get(f"{api_constant.ROOT_API_ROUTE}/channels/list", status_code=200, response_class=ORJSONResponse)
async def list_channels_route():
    """ List tracked channels route """
    return ORJSONResponse(
        {   
            "status_code": 200,
            "tracked_channels": classes.tracked_channels.list_tracked_channels()
        }
    )

@api.post(f"{api_constant.ROOT_API_ROUTE}/channels/add", status_code=200, response_class=ORJSONResponse)
async def add_channels_route(channel_handle: str):
    """ Add channels route """
    res = classes.tracked_channels.add_channel_to_tracked_list(channel_handle=channel_handle)

    return ORJSONResponse(res)

@api.delete(api_constant.ROOT_API_ROUTE + "/channels/delete/{channel_handle}", status_code=200, response_class=ORJSONResponse)
async def delete_channels_route(channel_handle: str):
    """ Delete a channel from the track channels list """
    res = classes.tracked_channels.remove_channel_from_tracked_list(
        channel_handle=channel_handle
    )

    return ORJSONResponse(res)

@api.get(f"{api_constant.ROOT_API_ROUTE}/videos", status_code=200)
async def videos_root_route():
    """ Videos root route """
    return ORJSONResponse(
        {
            "status_code": 200,
            "message": "videos root route"
        }
    )

@api.get(api_constant.ROOT_API_ROUTE + "/videos/{video_id}", status_code=200, response_class=StreamingResponse)
async def get_videos_route(video_id: str, range_header: str = Header(None)):
    """ Streams a video """
    if video_id == "list":
        return RedirectResponse(f"{api_constant.ROOT_API_ROUTE}/videos/list/")

    if range_header:
        start, end = parse_range_header(range_header)

        return StreamingResponse(
            classes.videos_handler.stream_video(
                video_id=video_id,
                start=start,
                end=end
            ),
            media_type="video/mp4"
        )
    else:
        return StreamingResponse(
            classes.videos_handler.stream_video(
                video_id=video_id,
                start=0,
                end=0
            ),
            media_type="video/mp4"
        )

@api.get(api_constant.ROOT_API_ROUTE + "/videos/{video_id}/status", status_code=200, response_class=ORJSONResponse)
async def video_status_route(video_id: str):
    """
    Video status route
    """
    
    if classes.database_handler.get_video_from_videos(video_id=video_id) is None:
        return ORJSONResponse(
            {
                "status_code": 200,
                "video_status": {
                    "is_present": False
                }
            }
        )

    return ORJSONResponse(
        {
            "status_code": 200,
            "video_status": {
                "is_present": True
            } 
        }
    )

@api.get(api_constant.ROOT_API_ROUTE + "/videos/list/", status_code=200, response_class=ORJSONResponse)
def list_videos_route():
    """ List videos route """
    return ORJSONResponse(
        {
            "status_code": 200,
            "videos_info": classes.videos_handler.list_videos()
        }
    )
