---
layout: post
title: "RDP to Debian"
date: 2022-03-15 09:00:00 -0500
categories: [homelab,howto's,linux,security]
tags: [homelab,linux,howto's,security]
---

Install xrdp.

```bash
sudo apt install xrdp
```

Now make sure to automatically start the service at the system startup.

```bash
systemctl enable xrdp
```

Then make sure that the service is running.

```bash
systemctl status xrdp
```

If you are running a firewall make sure you have put a allow rule in for the RDP port.

```bash
ufw allow 3389/tcp
```

**Note**
You have to configure the polkit rule to avoid an authenticate popup after inputting the username and password at the xrdp login screen on windows.

```bash 
vim /etc/polkit-1/localauthority.conf.d/02-allow-colord.conf 
```

```bash
polkit.addRule(function(action, subject) {
if ((action.id == “org.freedesktop.color-manager.create-device” || action.id == “org.freedesktop.color-manager.create-profile” || action.id == “org.freedesktop.color-manager.delete-device” || action.id == 
“org.freedesktop.color-manager.delete-profile” || action.id == “org.freedesktop.color-manager.modify-device” || action.id == “org.freedesktop.color-manager.modify-profile”) && subject.isInGroup(“{group}”))
{
return polkit.Result.YES;
}
});
```
Restart the xrdp service.

```bash
systemctl restart xrdp
``` 