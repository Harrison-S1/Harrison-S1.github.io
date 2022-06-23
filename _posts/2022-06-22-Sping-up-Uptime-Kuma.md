---
layout: post
title: "Sping up Uptime Kuma"
date: 2022-06-22 09:00:00 -0500
categories: [docker,howto's,monitoring]
tags: [monitoring,docker,howto's]
---

For a person who comes from a world of Zabbix and Nagios, Uptime Kuma is wicked, a light weight monitoring tool that gets out of your way to do basics, ie HTTP(S), TCP Ports, DNS & SQL.  Lets spin it up:

> You will need a Linux distro of choice and docker installed
{: .prompt-tip }

```bash
mkdir uptime_kuma
cd uptime_kuma
touch docker-compose.yml
vim docker-compose.yml
```

```yaml;
---
version: "3.1"

services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    volumes:
      - /home/serveradmin/docker_volumes/uptime-kuma/data:/app/data
    ports:
      - 3001:3001
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
```

```bash
mkdir data
docker-compose up -d
```

Done, go to http://IP/FQDM:3001 and create your account. 

If you forget your password

```bash
docker exec -it <container name> npm run reset-password
```

[Docs](https://uptime.kuma.pet/docs/README)