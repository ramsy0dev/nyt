import Link from 'next/link';

// MUI Components
import Box from '@mui/material/Box';
import Avatar from '@mui/material/Avatar';
import { Card, CardActionArea, CardContent, CardMedia, Typography }  from '@mui/material';

type VideoCardProps = {
  video_title: string;
  video_id: string;
  thumbnail_url: string;
  channel_handle: string;
  channel_avatar_url: string;
};

export default function VideoCard(props: VideoCardProps) {
  const { video_title, video_id, thumbnail_url, channel_handle, channel_avatar_url } = props;

  const redirectUrl = `/watch/${video_id}`;

  return (
    <Card sx={{ display: 'flex', width: "300px", height: "290px", borderRadius: 3 }}>
      <Link href={redirectUrl}>
        <CardActionArea>
          <CardMedia image={thumbnail_url} sx={{ width: "300px", height: "200px"}}/> 
          <CardContent>
            { /* Alignment for the Avatar and the video title*/}
            <Box sx={{ display: "flex", flexDirection: "column", alignItems: "start" }}>
              <Box sx={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 1 }}>
              <Avatar src={channel_avatar_url} />
              <Typography variant="subtitle1">{video_title}</Typography>
            </Box>
            { /* Alignment for the channel handle and the avatar and the video title*/}
            <Box sx={{ display: "flex", flexDirection: "row", justifyContent: "space-between", alignItems: "center", width: "200px" }}>
              <Typography variant="subtitle2">{channel_handle}</Typography>
            </Box>
          </Box> 
          </CardContent> 
        </CardActionArea>
      </Link>
    </Card>
  )
}

