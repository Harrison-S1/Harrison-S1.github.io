---
layout: post
title: "Creating a Storage Gateway in AWS"
date: 2022-12-17 09:00:00 -0500
categories: [aws,howto's,linux,cloud,terraform]
tags: [aws,linux,howto's,sysops,cloud,terraform]
---

# So what is a Storge Gateway? 
A Storage Gateway it just a way to connect AWS storage in a traditional way e.g. NFS, SMB etc.

## Lets build one with Terraform
> A fully working envriment with a Storage Gateway can be found [here](https://github.com/Harrison-S1/terraform/tree/master/aws_dev_env_sg)

So a Storage Gateway is built up of the following 
 - A instance with a dedicated 150GB cahce drive
 - A role
 - A security group 
 - S3 bucket (in this example)
 - S3 policy


## The Instance

```terraform

// NOTE: the varable for the instance ami used here will be stored in a datasource.tf file.

  resource "aws_instance" "dev_gateway" {
  instance_type          = "m5.xlarge"
  ami                    = data.aws_ami.server_ami_gw.id
  key_name               = aws_key_pair.clouddev_auth.id
  vpc_security_group_ids = [aws_security_group.main_gateway_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.dev_profile.name
  subnet_id              = aws_subnet.main_public_subnet.id

  root_block_device {
    volume_size = 80
    volume_type = "gp3"
  }

  tags = {
    Name = "dev-gateway"
  }
  }


// NOTE: This is where you will define the disk used for the cache.

resource "aws_ebs_volume" "dev-cache" {
  availability_zone = "eu-west-2a"
  size = 150
  type = "gp3"
  encrypted = true

  tags = {
    Name = "dev-cache"
  }
    depends_on = [
    aws_instance.dev_gateway
  ]
}

// NOTE: This is where you will attck the disk to the new instance. 

resource "aws_volume_attachment" "ebs_att" {
  device_name = "/dev/xvds"
  volume_id   = aws_ebs_volume.dev-cache.id
  instance_id = aws_instance.dev_gateway.id
}

data "aws_storagegateway_local_disk" "example" {
  disk_node   = "/dev/xvds"
  gateway_arn = aws_storagegateway_gateway.g1.arn
}

resource "aws_storagegateway_cache" "dev-cache" {
  disk_id     = data.aws_storagegateway_local_disk.example.id
  gateway_arn = aws_storagegateway_gateway.g1.arn
}
```

The varable for the instance ami will look like this:
> The ami that is being used has been built by AWS

```terraform

data "aws_ami" "server_ami_gw" {
  most_recent = true
  owners      = ["029176880048"]

  filter {
    name   = "name"
    values = ["aws-storage-gateway-*"]
  }
}
```

> If you are building this in one .tf file just add the above data source for it run.

## Security Group

```terraform

// NOTE: Ingress / Egress rules taken from AWS:
// https://docs.aws.amazon.com/storagegateway/latest/userguide/Resource_Ports.html
resource "aws_security_group" "main_gateway_sg" {
  name        = "dev-gateway"
  description = "Security Group for NFS File Gateway."
  vpc_id      = aws_vpc.mainvpc.id

  // Activation
  //////////////
  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  // NFS
  ///////
  ingress {
    protocol    = "tcp"
    from_port   = 20048
    to_port     = 20048
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "udp"
    from_port   = 20048
    to_port     = 20048
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "tcp"
    from_port   = 111
    to_port     = 111
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "udp"
    from_port   = 111
    to_port     = 111
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "tcp"
    from_port   = 2049
    to_port     = 2049
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "udp"
    from_port   = 2049
    to_port     = 2049
    cidr_blocks = ["0.0.0.0/0"]
  }

  // DNS (?)
  ///////////
  ingress {
    protocol    = "tcp"
    from_port   = 53
    to_port     = 53
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "udp"
    from_port   = 53
    to_port     = 53
    cidr_blocks = ["0.0.0.0/0"]
  }

  // Allow all egress
  ////////////////////
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

```

## Lets configure the gateway,NFS share & add the S3 policy. 

```terraform
resource "aws_storagegateway_gateway" "g1" {
  gateway_name       = var.gateway_name
  gateway_timezone   = var.gateway_timezone
  gateway_type       = "FILE_S3"
  gateway_ip_address = aws_instance.dev_gateway.public_ip

  depends_on = [
    aws_instance.dev_gateway
  ]

}

resource "aws_storagegateway_nfs_file_share" "file_share" {
  client_list  = ["0.0.0.0/0"]
  gateway_arn  = aws_storagegateway_gateway.g1.arn
  location_arn = aws_s3_bucket.gate_buc.arn
  role_arn     = aws_iam_role.role.arn
}

resource "aws_iam_policy" "policy" {
  name        = "S3_policy"
  description = "Providing limited S3 powers"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  policy = jsonencode({
      "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "s3:GetAccelerateConfiguration",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning",
                "s3:ListBucket",
                "s3:ListBucketVersions",
                "s3:ListBucketMultipartUploads"
            ],
            "Resource": "arn:aws:s3:::${var.bucket_name}",
            "Effect": "Allow"
        },
        {
            "Action": [
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:DeleteObjectVersion",
                "s3:GetObject",
                "s3:GetObjectAcl",
                "s3:GetObjectVersion",
                "s3:ListMultipartUploadParts",
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::${var.bucket_name}/*",
            "Effect": "Allow"
        }
    ]
  })
}

```

## Finally lets create our S3 butcket

```terraform
resource "aws_s3_bucket" "gate_buc" {
  bucket = var.bucket_name

  tags = {
    Name        = "My bucket"
    Environment = "Dev"
  }
```

And that's it, run your `terraform apply`. You should now have a storage gaetway instance in your EC2 console and your share will be available from the Storage Gateway console with the command you need to mount it. Make sure you read the AWS [Docs](https://docs.aws.amazon.com/storagegateway/index.html) and the Terraform [Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_gateway) 


## Is this the best way to access cloud storage? 

No, I don't think it is for the following reasons:
- This solution will be charging you for the instance, ebs volume, S3 bucket and the pulic IP etc.
- There is a easier way to mount cloud storage on prem and within the cloud environment......[Rclone](https://rclone.org/) 








