---
layout: post
title: "Create a systemd service to monitor Cloudwatch agent"
date: 2022-10-23 09:00:00 -0500
categories: [aws,howto's,linux,cloud,cloudwatch]
tags: [aws,linux,howto's,sysops,cloud,cloudwatch]
---


> Prerequisite
> - The [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/download-cloudwatch-agent-commandline.html) agent is installed
> - You have set up a [IAM Role](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/create-iam-roles-for-cloudwatch-agent.html) for the CloudWatch agent


## Set up a service to monitor
At the moment CloudWatch does not monitor services as we would normally expect a monitoring system to do with a agent, **is it up or down**. So we need to create the metric ourselves.

Systemctl can help us there with:

```bash
systemctl -q is-active httpd.service
```


>**is-active** _PATTERN_**...**
Check whether any of the specified units are active (i.e.
running). Returns an exit code **0** if at least one is active,
or non-zero otherwise. Unless **--quiet** is specified, this will
also print the current unit state to standard output.

Using ```&& echo "Running:1" || echo "Warning:0" ```section is using the OR operator, so echo either 1 if systemctl command returns its exit code, the service is up  **echo "1"'** OR **||** ...**echo "0"**, which indicates the service is down. 

## Adding the metric to a log file
Now we want the metric going to a logfile to pull into CloudWatch. In this example I'm using the apache package htpd. Change the log file folder and .log file name to what ever service you are wanting to monitor.

```bash
mkdir -p /var/log/services/ && touch /var/log/services/httpd_service.log
```

Now the command will look like this

> Remember to change the service folder and log name to what service you are using

```bash
systemctl -q is-active httpd.service  && echo "Running:1" > /var/log/services/httpd_service.log || echo "Warning:0" > /var/log/services/httpd_service.log
```

So let check, we should either have a 1 (Running) or 0 (Warning)

```bash
cat /var/log/services/httpd_service.log
```

> If nothing is showing, you need to go back and figure out if the path is bad or the directory name is there

## Adding this to CRON 
Now we have data going to the log file, we need to automate it with CRON.

**As root**

```bash
crontab -e
```

and add the following:

```bash
*/1 * * * * systemctl -q is-active httpd.service  && echo "Running:1" >> /var/log/services/httpd_service.log || echo "Warning:0" >> /var/log/services/httpd_service.log
```

This will run every minute for testing purposes, but feel free to adjust it to what you need. 
> Do not forget to change the log file path. The above example is for httpd

## Edit the CloudWatch agent config

Now we need to configure the CloudWatch agent. Edit the CloudWatch agent configuration file.

```bash
vim /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent.json 
```

> This is an example of pulling the log metric only

```json
{
    "agent": {
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
    "metrics_collection_interval": 60,
    "run_as_user": "root",
 .  "debug": false
    },
    "logs": {
        "logs_collected": {
            "files": {
         .      "collect_list": [
                    {
                        "file_path": "/var/log/services/httpd_service.log",
                        "log_group_name": "/ec2/CloudWatchAgentServiceLog/",
                        "log_stream_name": "{instance_id}_{hostname}",
                        "timezone": "Local"

                     }
                ]
            }
        }
    }
}
```

Now tell the agent to use the new config and restart the agent.

```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent.json
```

Now wait a minute and you would not have logs being pulled into CloudWatch

> if there are error it will show in the output of the previous command

You can check the agents status with:

```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a status
```


## Set up logrotate

Now we have logs being created and ingested into CloudWatch we need to do some house keeping on the system with logrotate. 

Create a logrotate config for not just this one service, but all that we may create in the future.

```bash
touch /etc/logrotate.d/monitored_services
```

Now lets edit the config

```bash
vim /etc/logrotate.d/monitored_services
```

```bash
/var/log/services/*log {
    weekly
    missingok
    copytruncate
    rotate 12
    compress
    delaycompress
    notifempty
}  
```

This is a good starting point. it will keep 12 weeks (3 months) worth of logs and compress them. These rules will apply to everything in `/var/log/servicess` If you need to isolate a service and have a different rule then just separate the log into its own directory. such as `/var/log/servicess/httpd/`

## Further reading
I would highly recommend going through the docs for [Manually create or edit the CloudWatch agent configuration file](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html#CloudWatch-Agent-Configuration-File-Complete-Example) 

## Setting up the CloudWatch Metric and Alarm

### Metric 
OK so now we want to get alerts from CloudWatch if our service goes down.
We need to create a "filter" in CloudWatch and then create a alarm based on the filters status. 

In the AWS console, navigate to

CloudWatch > CloudWatch Logs> Log groups > **NAMEOFLOG**
> If you are following along with the example the log name would be ** /ec2/CloudWatchAgentServiceLog/** 


Then under the **Actions** menu select **Create metric filter**

Now we need to fill out the requirements for the **Define pattern**
**Filter pattern** enter Warning
> This is the key word that is is our log file for a service going down

Click next

**Filter name** enter Apache down
**Metric namespace** enter Services
> We can add other services to the namespace - its just a grouping

**Metric name** enter httpd down
**Metric value** enter 1 
**Default value – _optional_** enter 0
> This will allow us to see when the service goes down on a lined graph, with a 1 indicating the service is down and the indicating normal operations

Click Next.

### Review and confirm

Now when you look at the metric httpd down, you will see when the service has gone down. Set you **Period** to 1 min and  **Statistic** to max in a line graph view. 


### Alarm

To create our alarm we need to navigate to **All alarms** on the left hand side panel, then click the orange **Create alarm**. 

On the new page select **Select Metric **

Now select our Group name that we created earlier, **Services**

 and select **Metric with no dimensions** and select **httpd down**
 > The metric name will change for whatever you have named the metric name to be.
 
#### Specify metric and conditions

Now we need to set the conditions for the alarm. You can change the metric name here if you wanted to.

- **Statistic** select Maximum
> You want this to be the Maximum, so its either a 1 or a 0, its up or down

- **Period** select 1 minutes
> Change this to meet your needs

- **Threshold type** select Static
- **Define the alarm condition** select Greater/Equal
- **Define the threshold value** enter 1

Click Next

### Configure actions
- **Alarm state trigger** set to In alarm
- **Send a notification to the following SNS topic**
> If you have not already set up a SNS topic you will need to create a new topic.
- You can also create a **OK** alert but clicking **Add notification** and adding the same SNS topic you created. You will then get an alert when the service goes down and comes back up.

Click Next

#### Add name and description
- Give the alarm a name and description.

Click Next

#### Preview and create
Review the alarm setting and click **Create alarm**.

















