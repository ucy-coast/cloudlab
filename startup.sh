#!/bin/bash

# Adapted from https://github.com/cstlee/cloudlab-profile

USERS="root `ls /users`"

# Install packages
echo "Installing common utilities"
apt-get update
apt-get -yq install vim gawk numactl ansible
# apt-get -yq install ccache htop mosh vim tmux pdsh tree axel

# echo "Installing performance tools"
# kernel_release=`uname -r`
# apt-get -yq install linux-tools-common linux-tools-${kernel_release} \
#         hugepages cpuset msr-tools i7z numactl tuned

# Install Go
echo "Installing Go"
GO_TARBALL=go1.24.5.linux-amd64.tar.gz
wget https://go.dev/dl/$GO_TARBALL -P /local/downloads
rm -rf /usr/local/go && tar -C /usr/local -xzf /local/downloads/$GO_TARBALL
grep -qxF 'export PATH=$PATH:/usr/local/go/bin' /etc/profile || echo 'export PATH=$PATH:/usr/local/go/bin' >> /etc/profile

# Install Go packages
GOBIN=/usr/local/bin /usr/local/go/bin/go install github.com/rakyll/hey@latest

# Install Protocol Buffers compiler
apt-get -yq install protobuf-compiler
apt-get -yq install golang-goprotobuf-dev

# Install Docker
echo "Installing Docker"
apt-get -yq install docker docker-compose

# Manage Docker as a non-root user
groupadd docker
for user in $USERS; do
    usermod -aG docker $user
done

# Setup password-less ssh between nodes
for user in $USERS; do
    if [ "$user" = "root" ]; then
        ssh_dir=/root/.ssh
    else
        ssh_dir=/users/$user/.ssh
    fi
    /usr/bin/geni-get key > $ssh_dir/id_rsa
    chmod 600 $ssh_dir/id_rsa
    chown $user: $ssh_dir/id_rsa
    ssh-keygen -y -f $ssh_dir/id_rsa > $ssh_dir/id_rsa.pub
    cat $ssh_dir/id_rsa.pub >> $ssh_dir/authorized_keys2
    chmod 644 $ssh_dir/authorized_keys2
    cat >>$ssh_dir/config <<EOL
    Host *
         StrictHostKeyChecking no
EOL
    chmod 644 $ssh_dir/config
done

# Change user login shell to Bash
for user in $USERS; do
    chsh -s `which bash` $user
done
