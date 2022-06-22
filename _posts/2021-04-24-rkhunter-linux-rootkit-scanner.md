---
layout: post
title: "Rkhunter - A Linux Rootkit Scanner"
date: 2021-04-24 09:00:00 -0500
categories: [security,howto's,linux]
tags: [security,linux,howto's]
---

RKH (RootKit Hunter) is a free, open source, powerful, simple to use and well known tool for scanning backdoors, rootkits and local exploits on POSIX compliant systems such as Linux. As the name implies, it is a rootkit hunter, security monitoring and analyzing tool that is thoroughly inspects a system to detect hidden security holes.

The rkhunter tool can be installed using following command on Ubuntu and CentOS based systems.

Debian base
```bash
sudo apt install rkhunter  
```

Rhel base
```bash
yum install epel-release  
yum install rkhunter
```

To check your server with rkhunter run the following command.

```bash
rkhunter -c
```

To make run rkhunter automatically at every night, add the following cron entry, which will run at 3am night and send reports to your email address.

```bash
0 3 * * * /usr/sbin/rkhunter -c 2>&1 | mail -s "rkhunter Reports of My Server" you@yourdomain.com
```

For more information and options run the following command.

```bash
rkhunter --help
```

[https://en.wikipedia.org/wiki/Rkhunter](https://en.wikipedia.org/wiki/Rkhunter "https://en.wikipedia.org/wiki/Rkhunter")  
[https://sourceforge.net/projects/rkhunter/](https://sourceforge.net/projects/rkhunter/ "https://sourceforge.net/projects/rkhunter/")
[https://wiki.archlinux.org/title/Rkhunter](https://wiki.archlinux.org/title/Rkhunter)