<div align="center">

<img src="assets/nyt-high-resolution-logo.png" width=600 />

**nyt** is short for **No YouTube**

</div>

# Table of content

- [Table of content](#table-of-content)
- [Introduction](#introduction)
- [Why?](#why)
- [Install](#install)
- [How to Use?](#how-to-use)
- [Directories used by nyt](#directories-used-by-nyt)
- [License](#license)

# Introduction

**nyt** is program made for people who are finding themselves stuck at **YouTube** all the time, this will help them keep of YouTube and getting notified when their favorite channel uploaded, this includes downloading the video locally so that you don't get distracted by the recommendation system.

# Why?

If one thing **YouTube** is really good, it will be video recommendations system that keep you hooked on **YouTube** for hours without realising the amount of time you just wasted.

# Install

You can install nyt using `pip`:

``` bash
pip install git+https://github.com/ramsy0dev/nyt.git
```

You will also need `ffmpeg` for video and audio processing, for windows:

``` bash
winget install ffmpeg
```

for Linux you can use your package manager:

* ### Pacman:

``` bash
sudo pacman -S ffmpeg
```

* ### Debian based distros:

``` bash
sudo apt install ffmpeg
```

# How to Use?

You can start by adding the channels that you want to keep track of, for example let say you watch Linus tech tips alot, you can add it like so:

``` bash
nyt track --channel-handle "LinusTechTips"
```

> __NOTE__: we don't add '@' to the channel's handel.

After you are done adding them, you can start the watcher that will be running in loop checking for new videos, of course it has a delay with the default being 30 minute. You can start the watcher like so:

```bash
nyt watch
```

if you want debug mode enabled:

```bash
nyt watch --debug-mode
```

After **nyt** finds that one of the tracked channels has uploaded a video it will send a notification and then it will download the video locally to `$HOME/.nyt/videos` (`$UserProfile\.nyt\videos` for Windows) so that you can watch it without having to open **YouTube**.

# Directories used by nyt

**nyt** creates a dir at `$HOME/.nyt` for linux, and `$UserProfile\\.nyt` for Windows.
this directory is where it keeps the sqlite database and a subdir called `videos` for downloading the **YouTube** videos.

# License

GPL-3.0
