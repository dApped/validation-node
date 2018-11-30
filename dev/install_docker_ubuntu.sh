#!/bin/sh

# Uninstall older docker
sudo apt-get -y remove docker docker-engine docker.io

sudo apt-get -y update

# install packages to allow apt to use a repository over HTTPS
sudo apt-get -y install \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common

# add Docker’s official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# set up the stable repository
sudo add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) \
    stable"

sudo apt-get -y update

sudo apt-get -y install docker-ce

# The Docker daemon always runs as the root user.
# If you don’t want to preface the docker command with sudo,
# create a Unix group called docker and add users to it.
# When the Docker daemon starts, it creates a Unix socket accessible by members of the docker group.

# Warning
# The docker group grants privileges equivalent to the root user. For details on how this impacts security in your system, see
sudo usermod -aG docker $USER

sudo systemctl enable docker # Start docker at boot

echo "Log out, log in. Then run: docker run hello-world to test docker instalation"
