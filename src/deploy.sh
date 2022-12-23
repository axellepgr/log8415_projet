#!/bin/bash
yes | sudo apt update
yes | sudo apt-get install python3-pip
pip install --upgrade pip
pip install pythonping==1.1.4
pip install sshtunnel==0.4.0
pip install pymysql==1.0.2
touch new_key.pem
sudo setcap cap_net_raw+ep $(which python3.6)
# adding private ssh key 
echo "-----BEGIN RSA PRIVATE KEY-----
-----END RSA PRIVATE KEY-----" > /home/ubuntu/new_key.pem
chmod 400 /home/ubuntu/new_key.pem