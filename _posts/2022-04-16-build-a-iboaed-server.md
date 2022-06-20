---
layout: post
title: "Build a iboard server"
date: 2022-04-16 09:00:00 -0500
categories: [homelab,howto's,linux,security]
tags: [homelab,linux,howto's,security]
---

Install apache2.

```bash
sudo apt install apache2
```

Install make.

```bash
sudo apt install make
```

Download the iboard repo.

```bash
git clone https://github.com/Harrison-S1/iboard.git
```

Move into the iboard dir and install the required perl mods.

```bash
cd CGI-4.51/; perl Makefile.PL; make; make install
cd Date-EzDate-1.16/; perl Makefile.PL; make; make install
```

Enable CGI on apache.

```bash
cd /etc/apache2/mods-enabled
sudo ln -s ../mods-available/cgi.load
```

or

```bash
sudo a2enmod cgi
```

Copy the following files to /usr/lib/cgi-bin/ryansiob .

```bash
-rwxr-xr-x 3 root www-data   914 Oct 29 15:38 envelope.gif*
-rwxr-xr-x 1 root root     30900 Oct 29 16:26 ryansiob.config.pl*
-rwxr-xr-x 1 root root      8223 Oct 29 15:38 ryansiob.pl*
-rwxr-xr-x 1 root root      2274 Oct 29 15:38 ryansiob.search.pl*
```

Change the group of envelope.gif.

```bash
chown root:www-data envelope.gif
```

Make .pl exacutable.

```bash
chmod +x /usr/lib/cgi-bin/ryansiob/*
```

Copy the following files to /usr/local/ryansiob.

```bash
-rwxrwx---  1 root     www-data 2229 Oct 29 09:26 allout.pl*
-rwxrwx---  1 root     www-data 1100 Oct 29 16:14 datafile*
-rwxrwx---  1 www-data www-data 1100 Oct 29 17:40 datafile.bak*
```

Change the group of the perant folder - apache needs to be able to read and write here so change there permissions as well.

```bash
chown -R root:www-data /usr/local/ryansiob/
chmod -R 770 /usr/local/ryansiob/
```

Create a link for the envelope.gif in the root of the /var/www/html.

```bash
ln /usr/lib/cgi-bin/ryansiob/envelope.gif /var/www/html/
```

Check permission have followed.

```bash
-rwxr-xr-x 3 root www-data   914 Oct 29 15:38 envelope.gif*
-rw-r--r-- 1 root root     10918 Oct 29 17:28 index.html.og
```

The site refreshes every 30 seconds, but does this based on the URL. Change the url with:

```bash
sed -i "s|localhost/|$HOSTNAME.domain.com|g"
```

Allow port 80 on the firewall.

```bash
sudo ufw allow 80
```

Restart apache.

```bash
sudo systemctl restart apache2
```

In the web browser go to:

[http://FQDN/cgi-bin/ryansiob/ryansiob.pl](http://fqdn/cgi-bin/ryansiob/ryansiob.pl)

Software source. [
Ryansiob](https://sourceforge.net/projects/ryansiob/files/latest/download) [
CGI-4.51](https://cpan.metacpan.org/authors/id/L/LE/LEEJO/CGI-4.51.tar.gz) [
Date-EzDate-1.16](https://cpan.metacpan.org/authors/id/M/MI/MIKO/Date-EzDate-1.16.tar.gz)