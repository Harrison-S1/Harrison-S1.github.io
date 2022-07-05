---
layout: post
title: "Ansible basics"
date: 2021-05-25 09:00:00 -0500
categories: [Ansible,howto's,linux]
tags: [ansible,linux,howto's,sysops]
---

#### Example CMD

Command can be run as a user with sudo rights.

```bash
ansible-playbook updateubuntu.yml --ask-sudo-pass
```

By adding the -k the users ssh password will be promoted for. Use if SSH keys are not set up.

```bash
ansible-playbook -k updateubuntu.yml --ask-sudo-pass
```

### Ad-hoc commands

##### Note

**Action**

-a

**Module**

-m

**Escalate privilege**

-b

**Command**

- Doesnt use the shell (Bash/sh)
- Can not use pipes or redirects

```bash
ansible all -b -m command -a 'echo "hello" > /root/hello.txt'
```

**Shell**

- Supports pipes and redirects
- Can get messed up by user settings

```bash
ansible all -b -m shell -a 'echo "hello" > /root/hello.txt'
```

**Raw**

- Just sends a command over ssh
- Doesn't need python

```bash
ansible all -b -m raw -a 'echo "hello" > /root/hello.txt'
```
**To remove a file**

```bash
ansible all -b -m file -a 'path=/root/hello.txt state=abset'
```

##### Syntax

To run an ad hoc command, the command must be framed or have the following syntax.

```bash
ansible &lt;host-pattern&gt; \[options\]
```
for example. the command should be written as follows.

```bash
ansible appserverhostgroup -m &lt;modulename&gt; -a &lt;arguments to the module&gt;
```
A single ansible ad hoc command can have multiple options. **-m** and **-a** are one amongst them and widely used.

##### List hosts

```bash
ansible all --list-hosts
```
#### Ping hosts

if you do not have SSH key-based authentication

```bash
ansible multi -m ping -i ansible_hosts --user=vagrant --ask-pass
```

#### Show host uptime for all

```bash
ansible -m raw -a '/usr/bin/uptime' all
```
or

```bash
ansible all -a 'uptime'
```

#### Restart services

```bash
ansible all -b -m service -a 'name=apache2 state=started'
```

#### Check python verison on all hosts

```bash
ansible -m shell -a 'python -V' all
```

#### Check free memory

```bash
ansible multi -a "free -m" -i inventory.yml
```

#### Create a user

```bash
ansible app -m user -a "name=weblogic group=weblogic createhome=yes" -b
```

#### Create a user group

```bash
ansible app -s -m group -a "name=weblogic state=present"
```
#### Create a Directory with 755 permission

```bash
ansible app -m file -a "path=/opt/oracle state=directory mode=0755" -b
```

#### Create a file with 755 permission

```bash
ansible app -m file -a "path=/tmp/testfile state=touch mode=0755"
```

#### Check free disk space

```bash
ansible multi -a "df -h"
```

#### Start or stop the service

**To Start**

```bash
ansible multi -s -m service -a "name=httod state=started enabled=yes"
```

**To Stop**

```bash
ansible multi -s -m service -a "name=httpd state=stop enabled=yes"
```

#### Install a package using apt command

```bash
ansible -i inventory.yml ubuntu -m raw -a "apt install -y ntp"
```

or

```bash
ansible -i inventory.yml ubuntu -a 'apt install ntp'
```

or

```bash
ansible -i inventory.yml ubuntu -m apt -a 'name=ntp state=present'
```

#### Install a package using yum command

```bash
ansible - ineventory.yml centos -m yum -a "name=httpd state=present"
```

**Note:** Status can = lastest which will update the package to the latest version if it is present, but will also install the package if it is not. To remove the package, the state would = absent

#### Managing Cron Job and Scheduling

**Run the job every 15 minutes**

```bash
ansible multi -s -m cron -a "name='daily-cron-all-servers' minute=*/15 
job='/path/to/minute-script.sh'"
```

**Run the job every four hours**

```bash
ansible multi -s -m cron -a "name='daily-cron-all-servers' hour=4 
job='/path/to/hour-script.sh'"
```

**Enabling a Job to run at system reboot**

```bash
ansible multi -s -m cron -a "name='daily-cron-all-servers' special_time=reboot 
job='/path/to/startup-script.sh'"
```

**Scheduling a Daily job**

```bash
ansible multi -s -m cron -a "name='daily-cron-all-servers' special_time=daily 
job='/path/to/daily-script.sh'"
```

**Scheduling a Weekly job**

```bash
ansible multi -s -m cron -a "name='daily-cron-all-servers' special_time=weekly 
job='/path/to/daily-script.sh
```

**Copy files**

```bash
ansible all -b -m copy -a 'src=/etc/hosts dest=/etc/hosts'
```

Note the source will copy the file on the source client to the servers.

**Fetch files**

```bash
ansible HOST -m fetch -a 'src=/path/to/soruce.txt dest=/home/USER/FOLDER/ flat=yes'
```