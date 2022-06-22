---
layout: post
title: "Ansible Adding a new servers"
date: 2021-06-01 09:00:00 -0500
categories: [Ansible,howto's,linux]
tags: [ansible,linux,howto's]
---

#### Copying SSH-key

On your new server, create the management user. Password for this user is in Keepass.
Once done, log into the management server as the management user. You need to copy over the ssh key for this user to the new server.

```bash
cd .ssh
ssh-copy-id -i id_ed25519.pub USER@SERVER
```

Test the key is working by logging onto the new server from the management server.

#### Append the ssh conf

Back on the management server in the .ssh folder edit the config file

```bash
vim config
```

And add in the following syntax

```bash
Host WHAT-YOU-CALLED-THE-HOST
 Hostname HOSTNAME-OF-SERVER
 Port SSH-PORT-NUMBER-BEING-USED
 User MANAGMENT-USERNAME
```

By added the server into this file you will not be prompted for a username or need to give the port number that is being used for ssh

#### Adding to the inventory

```bash
cd ansible/
```

Edit the inventory file

```bash
vim inventory.yml
```
Add the host according to the syntax showing in this file. Once saved you can now test that the host is responding with:

```bash
ansible webservers -m ping
```

Note that "webservers" needs to be replaced with the parent of where you have placed the new server in the inventory.yml file