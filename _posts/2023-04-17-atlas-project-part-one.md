---
layout: post
title: "Atlas Project - part one"
date: 2023-04-17 09:00:00 -0500
categories: [aws,howto's,linux,cloud,terraform,docker]
tags: [aws,linux,howto's,sysops,cloud,terraform,docker]
---


Often in tech it is hard to see the wood through the trees and stringing what you know and learned together can be difficult. So here is my mini project to learn more about GitHub actions Terraform Cloud and to brush up on some Docker and Terraform skills. 

I'll be walking you though how to deploy a browser based puzzle game called 2048 which by now is a fork, of a fork of a fork, On AWS using Docker, Terraform, Terraform Cloud and GitHub Actions. 

Getting starting, I assume you know enough Linux to be dangerous, how to install Docker, Terraform on your machine, and you have or will create GitHub account and Terraform Cloud account. AWS you can either use your own account or you have access to one through a training provider like A Cloud Guru.

## Docker 

I like to have control over the images, but you can either use mine or create your own and push it up to the docker registry.

### Building the image

This one is nice and straight forward:

Clone the [repo](https://github.com/Harrison-S1/2048)

```bash
cd 2048
```

Check the **Dockerfile**, which will contain the following:

```bash
FROM nginx:latest
COPY 2048 /usr/share/nginx/html
EXPOSE 80
```

Now run the build with:

```bash
docker build .
```

Your output will look something like this

```bash
[+] Building 7.0s (8/8) FINISHED                                                                                                                                                              
 => [internal] load .dockerignore                                                                                                                                                        0.1s
 => => transferring context: 2B                                                                                                                                                          0.0s
 => [internal] load build definition from Dockerfile                                                                                                                                     0.1s
 => => transferring dockerfile: 97B                                                                                                                                                      0.0s
 => [internal] load metadata for docker.io/library/nginx:latest                                                                                                                          1.7s
 => [auth] library/nginx:pull token for registry-1.docker.io                                                                                                                             0.0s
 => [1/2] FROM docker.io/library/nginx:latest@sha256:2ab30d6ac53580a6db8b657abf0f68d75360ff5cc1670a85acb5bd85ba1b19c0                                                                    4.3s
 => => resolve docker.io/library/nginx:latest@sha256:2ab30d6ac53580a6db8b657abf0f68d75360ff5cc1670a85acb5bd85ba1b19c0                                                                    0.0s
 => => sha256:bfb112db4075460ec042ce13e0b9c3ebd982f93ae0be155496d050bb70006750 1.57kB / 1.57kB                                                                                           0.0s
 => => sha256:080ed0ed8312deca92e9a769b518cdfa20f5278359bd156f3469dd8fa532db6b 7.92kB / 7.92kB                                                                                           0.0s
 => => sha256:2ab30d6ac53580a6db8b657abf0f68d75360ff5cc1670a85acb5bd85ba1b19c0 1.86kB / 1.86kB                                                                                           0.0s
 => => sha256:f1f26f5702560b7e591bef5c4d840f76a232bf13fd5aefc4e22077a1ae4440c7 31.41MB / 31.41MB                                                                                         1.2s
 => => sha256:7f7f30930c6b1fa9e421ba5d234c3030a838740a22a42899d3df5f87e00ea94f 25.58MB / 25.58MB                                                                                         1.0s
 => => sha256:2836b727df80c28853d6c505a2c3a5959316e48b1cff42d98e70cb905b166c82 626B / 626B                                                                                               0.3s
 => => sha256:e1eeb0f1c06b25695a5b9df587edf4bf12a5af9432696811dd8d5fcfd01d7949 956B / 956B                                                                                               0.5s
 => => sha256:86b2457cc2b0d68200061e3420623c010de5e6fb184e18328a46ef22dbba490a 772B / 772B                                                                                               0.7s
 => => sha256:9862f2ee2e8cd9dab487d7dc2152a3f76cb503772dfb8e830973264340d6233e 1.40kB / 1.40kB                                                                                           0.9s
 => => extracting sha256:f1f26f5702560b7e591bef5c4d840f76a232bf13fd5aefc4e22077a1ae4440c7                                                                                                0.9s
 => => extracting sha256:7f7f30930c6b1fa9e421ba5d234c3030a838740a22a42899d3df5f87e00ea94f                                                                                                0.5s
 => => extracting sha256:2836b727df80c28853d6c505a2c3a5959316e48b1cff42d98e70cb905b166c82                                                                                                0.0s
 => => extracting sha256:e1eeb0f1c06b25695a5b9df587edf4bf12a5af9432696811dd8d5fcfd01d7949                                                                                                0.0s
 => => extracting sha256:86b2457cc2b0d68200061e3420623c010de5e6fb184e18328a46ef22dbba490a                                                                                                0.0s
 => => extracting sha256:9862f2ee2e8cd9dab487d7dc2152a3f76cb503772dfb8e830973264340d6233e                                                                                                0.0s
 => [internal] load build context                                                                                                                                                        0.1s
 => => transferring context: 600.50kB                                                                                                                                                    0.0s
 => [2/2] COPY 2048 /usr/share/nginx/html                                                                                                                                                0.2s
 => exporting to image                                                                                                                                                                   0.6s
 => => exporting layers                                                                                                                                                                  0.6s
 => => writing image sha256:88c5f79cbf57badc37bfa77578431557d34dd6fef640574ae4646b6f1a2a0eae  
```

Run `docker images` and you will see your newly build image.

```bash
REPOSITORY               TAG       IMAGE ID       CREATED              SIZE
<none>                   <none>    88c5f79cbf57   About a minute ago   143MB
```

You will want to tag your image to make it easier to know what one you are using, etc. Run the following command to do so.

```bash
docker build -t yourusername/repository-name .
```

Run the `docker images`command again, and you will see the image with what you have just tagged it with. 

Now you can also test the image to make sure it's work as it should be. Run the following command:

> Note, change the [MYIMAGE] to what you have tagged the image as

```bash
docker run -p 8089:80 [MYIMAGE]
```

You will now be able to check it in the browser at `http://localhost:8089/`

> From here you can either push that image up to the Docker repository or use the image I created.

To use the image I have created, just run:

```bash
docker pull harrisons1/2048
```

and run

```bash
docker run -p 8089:80 harrisons1/2048 
```

OK, so we have our first part of the puzzle, a web based game inside a container. Part two will be setting up the AWS environment with Terraform. 
