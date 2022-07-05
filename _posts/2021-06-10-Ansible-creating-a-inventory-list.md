---
layout: post
title: "Ansible creating a inventory list"
date: 2021-06-10 09:00:00 -0500
categories: [Ansible,howto's,linux]
tags: [ansible,linux,howto's,sysops]
---

Create a inventory.yml file in your users ansible file

```bash
vim inventory.yml
```

And use the layout below.

- All yaml files start with ---
- all: -- All server will be in this group.
- children: --Is saying that there a another group within all:
- linux: -- This is the group name that you want to call your group.
- host: -- Is the hosts that belong to this group.

In the example below:

- All server are in the all: group.
- The all: group has a group inside it called linux.
- The group linux also have it's own groups call ubuntu and centos.
- www is another group that is sits in line with the linux group

```yaml
---
all:
  children:
    linux:
      children:
        debian:
          hosts:
            example1.domain.com:
            example2.domain.com:
            
        rhel:
          hosts:
            example3.vog.com
    www:
     hosts:
       example2.domain.com:
       example3.domain.com:
```

To view the host user the following command

```bash
ansible linux --list-hosts -i inventory.yml
```
[Further reading](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html)