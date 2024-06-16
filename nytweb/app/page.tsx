// Costum components
import VideoCard from './components/video_component';

// Services
import {FetchVideos, Video} from './services/videos';

export default async function Home() {
  const videosData = await FetchVideos(); 
  const videos = videosData.videos_info;

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <h1> NYT - No YouTube </h1>
      <div className="columns-2 min-h-screen min-v-screen">
        {videos.length > 0 ?
          videos.map((video: Video) => (
              <VideoCard key={videos.indexOf(video)} video_title={video.video_title} video_id={video.video_id} thumbnail_url={video.thumbnail_url} channel_handle={video.channel_handle} channel_avatar_url={video.channel_avatar_url_default} /> 
            )
          ) : (
            <h2> Loading videos...</h2>
          )
        }
      </div>
    </main>
  );
}

