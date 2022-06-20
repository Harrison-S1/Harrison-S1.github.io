---
layout: post
title: "Converting with ffmpeg"
date: 2022-06-17 09:00:00 -0500
categories: [homelab,howto's,linux]
tags: [homelab,linux,howto's]
---

###  Convert mp4 to mkv

```bash
ffmpeg -i input.mp4 -codec copy output.mkv
```

> Tip: To convert all MP4 files in the current directory, run a simple loop in terminal:
{: .prompt-tip }

```bash
for i in *.mp4; do
    ffmpeg -i "$i" -codec copy "${i%.*}.mkv"
done
```

### Cut using a specific time

```bash
ffmpeg -i input.mp4 -ss 00:05:10 -to 00:15:30 -c:v copy -c:a copy output2.mp4
```
