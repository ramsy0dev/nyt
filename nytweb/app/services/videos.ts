
import { API_ROOT_ROUTE, HEADERS } from '../constant';
 
export interface Video {
  video_title: string;
  video_id: string;
  thumbnail_url: string;
  channel_handle: string;
  is_watched: boolean;
  publish_date: string;
  channel_avatar_url_default: string;
  timestamp: string | null
}

export interface VideosResponse {
  status_code: number;
  videos_info: Video[];
}

export async function FetchVideos(): Promise<VideosResponse>{
  const url = `${API_ROOT_ROUTE}/videos/list/`;
  const response = await fetch(
    url,
    {
      method: 'GET',
      headers: HEADERS
    }
  );

  if (!response.ok) {
    console.log(`Faild to request videos data from '${url}'`);
  }

  const videosData = await response.json();
  
  console.log(videosData);

  return videosData as VideosResponse; 
}

export function getWatchUrl(video_id: string): string {
  return `${API_ROOT_ROUTE}/videos/${video_id}`;
}
export async function checkVideo(video_id: string): Promise<boolean> {
  // Checks if the video exists or not
  const url = `${API_ROOT_ROUTE}/videos/${video_id}`;
  const response = await fetch(
    url,
    {
      method: 'GET',
      headers: HEADERS
    }
  );
  if (!response.ok) {  
    console.log(`Faild to request videos data from '${url}'`);
  }

  const json_response = await response.json();
  
  return json_response["video_status"]["is_present"];
}
