type VideoProps = {
  src: string
}

export default function VideoPlayer(props: VideoProps) {
  return (
    <video width="1280" height="720" controls preload="none">
      <source src={props.src} type="video/mp4" />
      <track
        src="/path/to/captions.vtt"
        kind="subtitles"
        srcLang="en"
        label="English"
      />
      Your browser does not support the video tag.
    </video>
  )
}
