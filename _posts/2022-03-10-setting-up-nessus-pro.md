---
layout: post
title: "Setting up Nessus Pro"
date: 2022-03-10 09:00:00 -0500
categories: [homelab, howto's, linux, security]
tags: [homelab,linux,howto's,security]
---

* Build your server
* Download the package for your server. https://www.tenable.com/downloads/nessus
* For this example a Ubuntu server is being used.
* Copy the package to your service and for Ubuntu run the following command.

```bash
sudo dpkg -i Nessus*.deb
```

and run the following command to start the daemon

```bash
/bin/systemctl start nessusd.service
```

* Navigate to [https://FQDN:8834/](https://fqdn:8834/)
* Run through the set up to complete the build.
* Nessus files are stored in /opt/
* Useful commands for Ubuntu

```bash
/bin/systemctl start nessusd.service
```

Starts the daemon

```bash
/bin/systemctl stop nessusd.service
```

Stops the daemon

```bash
/bin/systemctl restart nessusd.service
```

Restarts the daemon

SSL certs are stored:

```bash
/opt/nessus/com/nessus/CA/servercert.pem
```

and

```bash
/opt/nessus/var/nessus/CA/serverkey.pem
```

Use the following commands to start or stop the service:
Note that you would use these command with these system. The latest Linux distros are using systemctl not init.

##### RedHat, CentOS, and Oracle Linux

Start

```bash
/sbin/service nessusd start
```

Stop

```bash
/sbin/service nessusd stop
```

##### SUSE 

Start

```bash
/etc/rc.d/nessusd start
```

Stop

```bash
etc/rc.d/nessusd stop
```

##### FreeBSD

Start

```bash
vice nessusd start
```

Stop

```bash
vice nessusd stop
```

##### Debian, Kali, and Ubuntu

Start

```bash
etc/init.d/nessusd start
```

Stop

```bash
etc/init.d/nessusd stop
```

## Update or add ssl cert

Back up the original Nessus CA and server certificates and keys:

```bash
cp /opt/nessus/com/nessus/CA/cacert.pem /opt/nessus/com/nessus/CA/cacert.pem.orig
cp /opt/nessus/var/nessus/CA/cakey.pem /opt/nessus/var/nessus/CA/cakey.pem.orig
cp /opt/nessus/com/nessus/CA/servercert.pem /opt/nessus/com/nessus/CA/servercert.pem.orig
cp /opt/nessus/var/nessus/CA/serverkey.pem /opt/nessus/var/nessus/CA/serverkey.pem.orig
```

Replace the original certificates with the new custom certificates:

```bash
cp customCA.pem /opt/nessus/com/nessus/CA/cacert.pem
cp customCA.key /opt/nessus/var/nessus/CA/cakey.pem
cp servercert.pem /opt/nessus/com/nessus/CA/servercert.pem
cp server.key /opt/nessus/var/nessus/CA/serverkey.pem
```

Restart Nessus:

```bash
service nessusd restart
```

If you get stuck: https://docs.tenable.com/nessus/Content/UploadACustomCACertificate.htm