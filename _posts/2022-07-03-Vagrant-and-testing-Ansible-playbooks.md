---
layout: post
title: "Vagrant and testing Ansible playbooks"
date: 2022-07-03 09:00:00 -0500
categories: [Ansible,howto's,linux]
tags: [ansible,linux,howto's,sysops]
---

## Download Vagrant

You are best going to to the main [site](https://www.vagrantup.com/downloads) BUT

### Debian 
```bash
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install vagrant
```

### Centos

```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
sudo yum -y install vagrant
```

### Ansible

```yaml
- name: Install vagrant
  vars:
    vagrant_version: 2.2.19
  unarchive:
    src: https://releases.hashicorp.com/vagrant/{{ vagrant_version }}/vagrant_{{ vagrant_version }}_linux_amd64.zip
    dest: /usr/local/bin
    remote_src: yes
    mode: 0755
    owner: root
    group: root
```

Create a directory to store your Vagrant configs and move into it. Within this dir create a folder for each Vagrant box you want to create, because Vagrant will create a ***.vagrant*** per box. 

```bash
mkdir vagrant && cd vagrant
```

> [Offical Doc's](https://www.vagrantup.com/docs)

### Setting update Vagrant file

```bash
mkdir ubuntu-22.04-nfs && cd ubuntu-22.04-nfs
```

and create your Vagrant config file

```bash
vim Vagrantfile
```

and paste the following.

```bash
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.hostname = "nfs-s"
  config.vm.provision "ansible", playbook: "playbook.yml"
  config.vm.provider :virtualbox do |v|
    v.name = "nfs-s"
    v.memory = 512
    v.cpus = 1
    v.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    v.customize ["modifyvm", :id, "--ioapic", "on"]
  config.vm.network :private_network, ip: "192.168.56.10"  
  end 
end
```

This basicly builds a [Ubuntu Jammy Jellyfish (22.04)](https://releases.ubuntu.com/22.04/) box with *512M* of RAM, *1 cpu* and names it *nfs-s* . For testing your playbooks line 4 is where it happen. Your setting Ansible as the provision and telling it what playbook to use.

### Playbook

Lets create a playbook to set up a nfs share. 

```bash
vim playbook.yml
```
and paste the below. 

> Change the IP to what you have set up for your Vagrant box

```yaml
---
 - hosts: all
   gather_facts: yes
   become: true
   tasks:
     - name: install nfs kernel server
       package:
        state: latest
        name:
        - nfs-kernel-server
        - apache2

     - name: Create a nfs directory if it does not exist
       ansible.builtin.file:
         path: /srv/nfs
         state: directory
         owner: nobody
         group: nogroup
         mode: '0777'
  
     - name: Add the nfs dir to exports file
       ansible.builtin.lineinfile:
         path: /etc/exports
         line: /srv/nfs  192.168.56.0/24(rw,sync,no_subtree_check)
         create: yes

     - name: NFS apply change configrue
       shell: systemctl reload nfs;exportfs -a
```

Now just run 

```bash
vagrant up
```

Your output will look like this

```bash
sam@msi:~/vagrant/vagrant-ansible/ubuntu-22.04-nfs$ vagrant up
Bringing machine 'default' up with 'virtualbox' provider...
==> default: Importing base box 'ubuntu/jammy64'...
==> default: Matching MAC address for NAT networking...
==> default: Checking if box 'ubuntu/jammy64' version '20220513.0.0' is up to date...
==> default: Setting the name of the VM: nfs-s
==> default: Clearing any previously set network interfaces...
==> default: Preparing network interfaces based on configuration...
    default: Adapter 1: nat
    default: Adapter 2: hostonly
    default: Adapter 3: hostonly
    default: Adapter 4: hostonly
    default: Adapter 5: hostonly
    default: Adapter 6: hostonly
==> default: Forwarding ports...
    default: 22 (guest) => 2222 (host) (adapter 1)
==> default: Running 'pre-boot' VM customizations...
==> default: Booting VM...
==> default: Waiting for machine to boot. This may take a few minutes...
    default: SSH address: 127.0.0.1:2222
    default: SSH username: vagrant
    default: SSH auth method: private key
    default: 
    default: Vagrant insecure key detected. Vagrant will automatically replace
    default: this with a newly generated keypair for better security.
    default: 
    default: Inserting generated public key within guest...
    default: Removing insecure key from the guest if it's present...
    default: Key inserted! Disconnecting and reconnecting using new SSH key...
==> default: Machine booted and ready!
==> default: Checking for guest additions in VM...
    default: The guest additions on this VM do not match the installed version of
    default: VirtualBox! In most cases this is fine, but in rare cases it can
    default: prevent things such as shared folders from working properly. If you see
    default: shared folder errors, please make sure the guest additions within the
    default: virtual machine match the version of VirtualBox you have installed on
    default: your host and reload your VM.
    default: 
    default: Guest Additions Version: 6.0.0 r127566
    default: VirtualBox Version: 6.1
==> default: Setting hostname...
==> default: Configuring and enabling network interfaces...
==> default: Mounting shared folders...
    default: /vagrant => /home/sam/vagrant/vagrant-ansible/ubuntu-22.04-nfs
==> default: Running provisioner: ansible...
    default: Running ansible-playbook...

PLAY [all] *********************************************************************

TASK [Gathering Facts] *********************************************************
ok: [default]

TASK [install nfs kernel server] ***********************************************
changed: [default]

TASK [Create a nfs directory if it does not exist] *****************************
changed: [default]

TASK [Add the nfs dir to exports file] *****************************************
changed: [default]

TASK [NFS apply change configrue] **********************************************
changed: [default]

PLAY RECAP *********************************************************************
default                    : ok=5    changed=4    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   

```

The beginning section is the Vagrant box set up. The end section is where the playbook is deployed.  If there are errors with the playbook they will show up there. Nice and easy. 

Yes you can test your playbooks with [Ansible Molecule](https://molecule.readthedocs.io/en/latest/)  using [Vagrant](https://www.vagrantup.com/), [Podman](https://podman.io/) and [Docker](https://www.docker.com/), but thats for next time.  

