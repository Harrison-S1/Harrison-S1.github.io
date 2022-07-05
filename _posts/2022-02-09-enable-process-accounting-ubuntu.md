---
layout: post
title: "How to Enable Process Accounting in Ubuntu"
date: 2022-02-09 09:00:00 -0500
categories: [ubuntu,howto's,linux,security]
tags: [security,ubuntu,howto's]
---


### Acct will log user process
If you Enable process accounting in your system, it will help you to keep track of your user processes. It is very useful for System administrators for keeping log of your users. In Ubuntu Process accounting can be done by installing utility called Acct

```bash
sudo apt-get install acct 
```

Make a log file for process accounting

```bash
sudo touch /var/log/pacct
```
Enable process accounting on

```bash
sudo accton /var/log/pacct
```

**or**

```bash
/etc/init.d/acct start
```

##### For viewing the Process Information Use the following command:

**Display details about users' connect time**
```bash
ac
```

- ac command displays a report of connect time in hours based on the logins/logouts.
- ac - Print total connection time.
- ac -dp - display daily (-d) connection totals by person (-p)

##### Display information about previously executed user commands

The below command will display the commands executed by user john

```bash
sudo lastcomm john
```

Search and display log by command rm

```bash
sudo lastcomm rm
```

Search and display log by terminal name
```bash
sudo lastcomm pts/1 
```

##### Print Accounting statistics

```bash
 sudo sa
```
sa command will display information about previously executed commands, The information can also be summarized on a per-user basis The output fields are labelled as follows:

- cpu sum of system and user time in cpu seconds 
- re “real time” in cpu seconds 
- k cpu-time averaged core usage, in 1k units 
- avio average number of I/O operations per execution 
t- io total number of I/O operations 
- k*sec cpu storage integral (kilo-core seconds) 
u user cpu time in cpu seconds 
s system time in cpu seconds

**Display ouput per user**

```bash
sudo sa -u 
```
**Display the number of processes and number of CPU minutes on a per-user basis**

```bash
sudo sa -m
```
By using sa command and looking at re, k, cp/cpu time you can find out suspicious activity or user and command who is eating your CPU and Memory . An increase in CPU/memory usage is indication of problem.