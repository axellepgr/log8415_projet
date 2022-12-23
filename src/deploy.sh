#!/bin/bash
yes | sudo apt update
yes | sudo apt-get install python3-pip
python3 -m venv venv
source venv/bin/activate
pip3 install --upgrade pip
pip3 install pythonping==1.1.4
pip3 install sshtunnel==0.4.0
pip3 install pymysql==1.0.2
pip3 install pyopenssl --upgrade
touch new_key.pem
sudo setcap cap_net_raw+ep $(which python3.6)
# adding private ssh key 
echo "-----BEGIN RSA PRIVATE KEY-----
-----END RSA PRIVATE KEY-----" > /home/ubuntu/new_key.pem
chmod 400 /home/ubuntu/new_key.pem
