import { redirect } from 'next/navigation';

// Components
import VideoPlayer from '../../components/video_player';

// Services
import { getWatchUrl } from '../../services/videos';

// Constants
import { API_ROOT_ROUTE } from '../../constant';

interface Params {
  video_id?: string;
}


export default function watch_video({ params }: { params: Params }) {
  const videoId = params.video_id;

  if (videoId == null || videoId == undefined) {
    return redirect("/");
  }

  const watch_url = getWatchUrl(videoId);
  let video_exists = API_ROOT_ROUTE + "/videos/" + videoId;

   return (
    <div className="div-justify">
      {
        video_exists? (
          <VideoPlayer src={watch_url} />
        ) : (
          <h1> No video with the id {videoId} exists </h1>
        )
      }
    </div>
  )
}
