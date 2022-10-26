---
layout: post
title: "Expanding EBS root volume"
date: 2022-09-17 09:00:00 -0500
categories: [aws,howto's,linux,sysops,cloud]
tags: [aws,linux,howto's,sysops,cloud]
---

Expand the root volume. Then, extend the file system using the Amazon EC2 console (new console)
1. From the Amazon EC2 console, choose Instances from the navigation pane.

2. Select the instance that you want to expand. From the Description tab, choose the volume listed for Block devices. Then, choose the EBS ID.

3. Select the volume. For Actions, choose Modify Volume.

4. In the Size field, enter the Size. If you choose an io1 volume, enter the number of IOPS.

5. Choose Modify, and then choose Yes. Refresh the console page. In the Description tab, the State shows the progress of optimization until the modification is complete.

Expand the root volume. Then, extend the file system using the AWS CLI
Run a command similar to the following. Replace the with your values:

```bash
aws ec2 modify-volume --region <regionName> --volume-id <volumeId> --size <newSize> --volume-type <newType> --iops <newIops>
```
Note: To view the progress of your task, run the following command:

```bash
aws ec2 describe-volumes-modifications --volume <volumeId> --region <region>
```

Extend a Linux file system after resizing a volume
Connect to your instance.

To verify the file system and type for each volume, use the <strong>df -hT</strong> command.

```bash
df -hT
```
To check whether the volume has a partition that must be extended, use the <strong>lsblk</strong> command to display information about the NVMe block devices attached to your instance.

```bash
lsblk
[ec2-user@mod-server1 ~]$ lsblk
NAME    MAJ:MIN RM SIZE RO TYPE MOUNTPOINT
xvda    202:0    0  30G  0 disk
└─xvda1 202:1    0  30G  0 part /
```

This example output shows the following
The root volume, <strong>/dev/xvda</strong>, has a partition, <strong>/dev/xvda11</strong>. While the size of the root volume reflects the new size, 16 GB, the size of the partition reflects the original size, 8 GB, and must be extended before you can extend the file system.
For volumes that have a partition, such as the root volume shown in the previous step, use the growpart command to extend the partition. Notice that there is a space between the device name and the partition number.

<em>Optional</em> To verify that the partition reflects the increased volume size, use the <strong>lsblk</strong> command again.

To extend the file system on each volume, use the correct command for your file system, as follows:

<strong>XFS file system</strong> To extend the file system on each volume, use the xfs_growfs command. In this example, /

```bash
sudo xfs_growfs -d /
```

If the XFS tools are not already installed, you can install them as follows.

```bash
sudo yum install xfsprogs
```
<strong>ext4 file system</strong> To extend the file system on each volume, use the resize2fs command.
```bash
sudo resize2fs /dev/nvme0n1p1
```

<strong>Other file system</strong> 
To extend the file system on each volume, refer to the documentation for your file system for instructions.

> Optional, To verify that each file system reflects the increased volume size, use the df -h command again.

Further reading
- https://aws.amazon.com/premiumsupport/knowledge-center/expand-ebs-root-volume-windows/
- https://aws.amazon.com/premiumsupport/knowledge-center/expand-root-ebs-linux/
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/recognize-expanded-volume-linux.html