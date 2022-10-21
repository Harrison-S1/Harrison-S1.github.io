---
layout: post
title: "Create a systemd service to monitor Cloudwatch agent"
date: 2021-10-21 16:30:00 -0500
categories: [aws,howto's,linux,cloudwatch]
tags: [aws,linux,howto's,sysops,cloudwatch]
---

### The problem to solve

If you are monitoring an AWS instance that is busy and has other programs accessing the same logs as the Cloudwatch agent then you may run into this error in the agents logs "too many open files" which stops any further information or metrics being sent to Cloudwatch. Not a huge problem, but what happens when everyone has gone home and know one is there to restarts the agent, or worse....what happens if you had a security breach and you need those logs.

### Part of the Solution

Is to create a small script to monitor the cloudwatch agent log file for that error "too many open files" as done below. The script looks for that error as new logs are entered in to the log file and if that line is seen stop the agent, then start it up and write a log message to say the agent has been restarted. 


```bash
#!/bin/bash

  

tail -fn0 /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log | while read line ; do

echo "${line}" | grep -i "too many open files" > /dev/null

if [ $? = 0 ] ; then

sudo amazon-cloudwatch-agent-ctl -a stop

sleep 5

sudo amazon-cloudwatch-agent-ctl -a start

sleep 5

sudo echo Agent restarted-$(date +"%d_%m_%y__%I_%M_%p") >> /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log

fi

done
```

But I dont want to have to put that into a cron job and monitor that as well, with other scenarios that can interfere with it. It just becomes messy. 

### The other part of the Solution

Lets create a Systemd service to manage it for us as done below.


```bash
vi /etc/systemd/system/monitor-cloudwatch.service
```

```bash
[Unit]

Description=Monitors Amazon CloudWatch agent and restart it if error of to many files are open

  

[Service]

User=root

WorkingDirectory=/root

ExecStart=/root/restartcw.sh

Restart=always

  

[Install]

WantedBy=multi-user.target
```

Once you have saved the service file we need to reload the daemon so our new service file gets included. 

```bash 
systemctl daemon-reload
```

Now lets start our new service.

```bash
system start monitor-cloudwatch.service
```

If you want the service to come up at boot dont forget to enable it. 

```bash
system enable monitor-cloudwatch.service
```

Check the stauts, everything should be happy.

```bash
system status monitor-cloudwatch.service
```


Grab yourself two terminals and you can test it out.

```bash
tail -f /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
```

```bash
echo "too many open files" >> /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
```

You should have seen the error message showing up, the agent restarting and a log message to stay your agent has been restarted.
Know you will also want to look at getting a notification/email that the agent has been restarted. Im not going to cover it here but you will want to create a metric filter that monitors your log group for specific patterns. AWS has this well [documented](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringPolicyExamples.html)