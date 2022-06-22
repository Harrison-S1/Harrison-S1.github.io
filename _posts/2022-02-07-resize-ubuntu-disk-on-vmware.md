---
layout: post
title: "Resize Ubuntu disk on VMware"
date: 2022-02-07 09:00:00 -0500
categories: [cloud,howto's,linux]
tags: [cloud,vmware,ubuntu,howto's]
---

- Add more storage to the drive in Vmware and reboot the server. 
- SSH into the server once back up, OR use the console. 

> /sda being the disk name/ ;abel given by the system. Note the space between sda & 1 is not a type-o
{: .prompt-tip }

Grow the partition
```bash
sudo growpart /dev/sda 1
```

Rezise the partition
```bash
sudo resize2fs /dev/sda1
```

Check the disk size
```bash
df -h to check
```

This also works with Google Cloud instances. 