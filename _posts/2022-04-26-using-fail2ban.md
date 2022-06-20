---
layout: post
title: "Using Fail2Ban"
date: 2022-04-26 09:00:00 -0500
categories: [homelab,howto's,linux,security]
tags: [homelab,linux,howto's,security]
---

Install and enable fail2ban
```bash
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

Edit the jails

```bash
sudo vim /etc/fail2ban/jail.local
```

Restart fail2ban

```bash
sudo systemctl restart fail2ban
```

Check status for all jails

```sudo fail2ban-client status```

Check status for a certain jail

```sudo fail2ban-client status sshd```

Un-ban a IP

```sudo fail2ban-client set sshd unbanip XXX.XXX.XXX.XXX```

