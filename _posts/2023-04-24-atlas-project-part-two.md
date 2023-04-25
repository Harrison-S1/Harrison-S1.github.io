---
layout: post
title: "Atlas project - part two"
date: 2023-04-24 09:00:00 -0500
categories: [aws,howto's,linux,cloud,terraform,docker]
tags: [aws,linux,howto's,sysops,cloud,terraform,docker]
---

OK, so we have our docker image, and we are storing it in the Docker repository. Now what.
Well we want to create some cloud infrastructure, so we can deploy our game, but we will be using Terraform to code up our infrastructure.

> Note, for this, I'm going to use the cloud playground from my subscription to A Cloud Guru. You can use this project on with the AWS free tier account, so if you need to go and sign up.

### Terraform 

Let's create a new folder, name it whatever and create your `main.tf` file with the following.

> In here we are just defining around AWS instance.

```hcl
resource "aws_instance" "dev_node" {
  instance_type          = "t2.micro"
  ami                    = data.aws_ami.server_ami.id
  vpc_security_group_ids = [aws_security_group.main_aws_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.dev_profile.name
  subnet_id              = aws_subnet.main_public_subnet.id
  user_data              = file("userdata.tpl")

  root_block_device {
    volume_size = 10
  }

  tags = {
    Name = "dev-node"
  }
}
```

From here on out, just create the file name and add the code. 

#### vpc.tf

> Here we are defining everything we need for our network in AWS.

```hcl
resource "aws_vpc" "mainvpc" {
  cidr_block           = "10.123.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "dev"
  }
}

resource "aws_subnet" "main_public_subnet" {
  vpc_id                  = aws_vpc.mainvpc.id
  cidr_block              = "10.123.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1a"

  tags = {
    Name = "dev-public"
  }
}

resource "aws_internet_gateway" "main_internet_gateway" {
  vpc_id = aws_vpc.mainvpc.id

  tags = {
    Name = "dev-igw"
  }
}

resource "aws_route_table" "main_public_rt" {
  vpc_id = aws_vpc.mainvpc.id

  tags = {
    Name = "dev_public_rt"
  }
}

resource "aws_route" "default_route" {
  route_table_id         = aws_route_table.main_public_rt.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main_internet_gateway.id
}

resource "aws_route_table_association" "main_public_assoc" {
  subnet_id      = aws_subnet.main_public_subnet.id
  route_table_id = aws_route_table.main_public_rt.id
}
```

#### variable.tf

> Here, we define any variables being used. In this case, the host OS

```hcl
variable "host_os" {
  type        = string
  default     = "linux"
  description = "default os being used to deploy"
}
```

#### sg.tf

> Here we are creating the security group that will be attacked to our AWS instance. For the sack of the project, it has been left open to all traffic. But we will look at securing it later on.  

```hcl
resource "aws_security_group" "main_aws_sg" {
  name        = "dev_sg"
  description = "dev security group"
  vpc_id      = aws_vpc.mainvpc.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

#### iam.tf

> Here we are creating the IAM role of the instance. `Note that this isnt required for the current interation, but if you where adding a S3 bucket, this will give the ec2 instance access and well as access to CloudWatch`

```hcl
resource "aws_iam_role" "EC2_dev_role" {
  name = "EC2_dev_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

  tags = {
    tag-key = "Cloudwatch"
  }
}

resource "aws_iam_instance_profile" "dev_profile" {
  name = "dev_profile"
  role = aws_iam_role.EC2_dev_role.name
}

resource "aws_iam_role_policy" "s3-dev" {
  name   = "s3-dev"
  role   = aws_iam_role.EC2_dev_role.id
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:*",
                "s3-object-lambda:*"
            ],
            "Resource": "*"
        }
    ]
}
EOF
}
```

#### datasource.tf

> Here we are declaring the data source of our AMI image. 

```hcl
data "aws_ami" "server_ami" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}
```

#### outputs.tf

> Sometimes we need some information about our instance after it has been created, such as its IP or instance ID.

```hcl
output "dev_ip" {
  description = "Output the public IP of the dev node instance"
  value       = aws_instance.dev_node.public_ip
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.dev_node.id
}
```

#### userdata.tpl

> If you have created your own docker reg, you can the script to pull that image inseed. 

```bash
#!/bin/bash
sudo apt-get update -y && 
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
sudo curl -o /opt/aws/amazon-cloudwatch-agent/amazon-cloudwatch-agent.json https://raw.githubusercontent.com/Harrison-S1/terraform/master/cloudwatch-config.json
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/amazon-cloudwatch-agent.json 
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo apt install unzip -y
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/home/ubuntu/awscliv2.zip"
sudo usermod -aG docker ubuntu # && sudo reboot now
sudo docker pull harrisons1/2048
sudo docker run --name 2048 -p 80:80 -d harrisons1/2048
```

#### providers.tf

> OK, so we will need to set up Terraform Cloud to store the state file for this project. Make sure you put your organization and workspaces you have set up in Terraform Cloud into this file.

```hcl
terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.0.1"
    }
  }
  required_version = "~> 1.0"

  backend "remote" {
    organization = "CHANGEME"

    workspaces {
      name = "CHANGEME"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}
```

## Setting up your AWS account

You will need to create a user in AWS to deploy this.

- Log into your AWS account.
- Navigate to IAM and select Users on the left-hand menu
- Select "Add users"
- Create the username
- Select "Access key - Programmatic access" and click next
- Select "Attach existing policies directly" and use the "AdministratorAccess" policy
> Don't do this for productions
- Tags are optional, so just click next, then create user

Now on the next page you need to add the details from user, access key ID and Secret access key to the AWS credentials file.

```bash
~/.aws/credentials
```

> For example
```bash
[terraformuser]

# This key identifies your AWS account.

aws_access_key_id = QKIAUDRQURVLS2JCIV4

# Treat this secret key like a password. Never share it or store it in source

# control. If your secret key is ever disclosed, immediately use IAM to delete

# the key pair and create a new one.

aws_secret_access_key = nBhpjpTCyerter3sdf0l3QZ7zxV78ptCF
```

## Setting up your Terraform Cloud

> Here, I'm assuming you already have an AWS account set up.

> This is part of the backend that is defined in `providers.tf`. You will need to go back to the `providers.tf` file and change the `organization` and `workspaces` name.

In your Terraform Cloud, create a new workspace

-   Select `API-driven workflow` 
-   Name the workspace and select the project (default is fine)
 -   Click on `Create workspace`
 -   In the left-hand menu select `Variables`
 -   Click `Add variable`
 -   Add the `AWS_ACCESS_KEY_ID` key, mark it as a `Environment variable` and also mark it as `Sensitive`
 -   Do the same for the `AWS_SECRET_ACCESS_KEY` variable
 -   Now lets create our `TF_API_TOKEN` for GitHub Actions.
 -   Click on your profile picture at the top left and select `User Settings`
 -   On the left-hand menu select Tokens and click on `Create an API token`
 -   Name it whatever you want, and copy the token to a notepad

Now, in your terminal, run  `terraform init`. Then `terraform fmt` to check the format. Once it is happy, you can run a `terraform plan`. Check you are happy with the output of the plan, then you can apply it with `terraform apply` Congratulations you now have a running game of 2048 in docker on an ec2 instance, with the support of AWS infrastructure, build with Terraform. 

In part 3 we'll look at setting up some CI with GitHub actions. 
