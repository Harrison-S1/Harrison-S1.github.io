---
layout: post
title: "Create a bind server with Ubuntu"
date: 2022-06-19 09:00:00 -0500
categories: [homelab, howto's, linux ]
tags: [homelab,linux,howto's]
---

### Install Bind

*This guide assumes you are using Ubuntu 20.04 and have already install and setup the server.*

Install the require packages:

```bash
sudo apt-get install bind9 bind9utils bind9-doc
```

If you are only using IPV4 it is best practice to set bind to IPV4 mode. This is done by editing /etc/default/named file. Add “-4” to the end of the OPTIONS parameter. It should look like the following:

 startup options for the server

```bash
OPTIONS="-u bind -4"
```

Restart bind to apply the change with:

```bash
sudo systemctl restart bind9
```
### Configuration for named.conf.option

```bash
sudo vim /etc/bind/named.conf.options
```

Add a ACL (access control list). This will be servers that can access the DNS service. In the example below the example, the ACL is called "trusted". You can call this list anything you want.
```bash
acl "trusted" {
        localhost;         # This is your main host that your on
        10.130.55.0/24;    # This is a subnet that you will be allowing 
        10.130.55.12;      # You can also add a host be host basis (more secure)
};

```

Under directory "/var/cache/bind";

add the following:
```bash
        recursion yes;                 # enables resursive queries
        allow-recursion { trusted; };  # allows recursive queries from "trusted" acl
        listen-on { hostip; };         # Private IP address of your host- listen on private network only
        allow-transfer { none; };      # disable zone transfers by default

        forwarders {
                1.1.1.1;
                8.8.8.8;
        };
```

Not that the forwarders IP will be needed if the DNS host does not have the recorder requested and needs to look to another DNS server. You config will look something like this:
```bash
acl "trusted" {
        localhost;         # This is your main host that your on
        10.131.55.0/24;    # This is a subnet that you will be allowing
        10.131.55.120;     # Secondary DNS server IP (if using a second)
        10.131.55.110;     # You can also add a host be host basis (more secure)
};

options {
        directory "/var/cache/bind";

        recursion yes;                 # enables resursive queries
        allow-recursion { trusted; };  # allows recursive queries from "trusted" acl
        listen-on { hostip; };         # Private IP address of your host- listen on private network only
        allow-transfer { none; };      # disable zone transfers by default
 
        forwarders {
                1.1.1.1;
                8.8.8.8;
        };


        // If there is a firewall between you and nameservers you want
        // to talk to, you may need to fix the firewall to allow multiple
        // ports to talk.  See http://www.kb.cert.org/vuls/id/800113 

        // If your ISP provided one or more IP addresses for stable
        // nameservers, you probably want to use them as forwarders.
        // Uncomment the following block, and insert the addresses replacing
        // the all-0's placeholder.

        // forwarders {
        //      0.0.0.0;
        // };

       //========================================================================
       // If BIND logs error messages about the root key being expired,
       // you will need to update your keys.  See https://www.isc.org/bind-keys
       //========================================================================
       dnssec-validation auto;

       listen-on-v6 { any; };
};
```
Save and exit the file. The configuration specifies that only your servers (defined in the acl) will be able to query the DNS server for outside domains.

### Configuration for named.conf.local

```bash
sudo vim /etc/bind/named.conf.local
```

Note that domain.com is being used as the example domain. you need to change this to your domain.
Add the forward look up zone:
```bash
zone "domain.com" {
    type master;
    file "/etc/bind/zones/db.domain.com";       # zone file path
    allow-transfer { dns2ip; };                 # Private IP address for secondary DNS server
};
```

Now add the revers lookup zone
```bash
zone "55.130.10.in-addr.arpa" {
    type master;
    file "/etc/bind/zones/db.10.130.55";  # 10.130.55.0/24 subnet
    allow-transfer { dns2ip; };           # Private IP address for secondary DNS server
};
```

Save and exit the file.

The zone configuration is now set, but we need to create the file for /etc/bind/zones/db.10.130.55 and /etc/bind/zones/db.domain.com

```bash
sudo mkdir /etc/bind/zones
sudo cp /etc/bind/db.local /etc/bind/zones/db.domain.com
sudo vim /etc/bind/zones/db.domain.com
```

edit the following:

```bash
$TTL    604800
@       IN      SOA     localhost. root.localhost. (
                              2         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
;
@       IN      NS      localhost.      ; delete this line
@       IN      A       127.0.0.1       ; delete this line
@       IN      AAAA    ::1             ; delete this line
```

Now you need to add your NS servers:

```bash
; name servers - A records
ns1.domain.com.          IN      A       10.130.55.10
ns2.domain.com.          IN      A       10.130.55.11
```

And then A records for your servers

```bash
; 10.130.55.0/24 - A records
host1.domain.com.        IN      A      10.130.55.100
host2.domain.com.        IN      A      10.130.55.101
```
Save and exit the file.
Now lets create the revers lookup zone.

```bash
sudo cp /etc/bind/db.127 /etc/bind/zones/db.10.130.55
sudo vim /etc/bind/zones/db.10.130.55
```
edit the following: $TTL 604800 @ IN SOA localhost. root.localhost. (
```bash
                             1         ; Serial
                        604800         ; Refresh
                         86400         ; Retry
                       2419200         ; Expire
                        604800 )       ; Negative Cache TTL

@ IN NS localhost. ; delete this line 1.0.0 IN PTR localhost. ; delete this line Add the NS servers

; name servers - NS records
      IN      NS      ns1.domain.com.
      IN      NS      ns2.domain.com.

And then the PTR records

; PTR Records
11  IN      PTR     ns1.domain.com.    ; 10.130.55.10
12  IN      PTR     ns2.domain.com.    ; 10.130.55.11
100 IN      PTR     host1.domain.com.  ; 10.130.55.100
101 IN      PTR     host2.domain.com.  ; 10.130.55.101
```
Save and exit.

### Configuration check

Check the zone for syntax errors with:

```bash
sudo named-checkconf
```

Now check the correctness of the zone against the domain with:

```bash
sudo named-checkzone domain.com db.domain.com
sudo named-checkzone 55.130.10.in-addr.arpa /etc/bind/zones/db.10.130.55
```

If the report no errors you can now restart the bind service with

```bash
sudo systemctl restart bind9
```

Allow bind traffic on the firewall with

```bash
sudo ufw allow Bind9
```

### Configuring the secondary DNS serve

On the second DNS host install the require packages

```bash
sudo apt-get install bind9 bind9utils bind9-doc
```

Now edit the bind config and add:

```bash
sudo vim /etc/bind/named.conf.options
```
```bash
acl "trusted" {

       10.130.55.10;    # ns1
       localhost;       # ns2 - can be set to localhost
       10.130.55.100;   # single host1
       10.130.55.0/24;  # subnet
};
```
Then as before add:
```bash
        recursion yes;
        allow-recursion { trusted; };
        listen-on { 10.130.55.11; };      # ns2 private IP address
        allow-transfer { none; };          # disable zone transfers by default

        forwarders {
                1.1.1.1;
                8.8.8.8;
        };
```

Save and exit. Now edit options.local

```bash
sudo vim /etc/bind/named.conf.local
```

And add the following:

```bash
zone "domain.com" {
    type slave;
    file "domain.com";
    masters { 10.130.55.10; };  # ns1 private IP
};

zone "55.130.10.in-addr.arpa" {
    type slave;
    file "db.10.130.55.";
    masters { 10.130.55.10; };  # ns1 private IP
};
```

### Configuration check on secondary server

Check the zone for syntax errors with:

```bash
sudo named-checkconf
```

If the report no errors you can now restart the bind service with

```bash
sudo systemctl restart bind9
```

Allow bind traffic on the firewall with

```bash
sudo ufw allow Bind9
```

Now you can configure your host to check the server are working.Use tools such as nslookup and dig.