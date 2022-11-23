import paramiko
import time
import sys
import boto3
import json

AWS_REGION = 'us-east-1'
DESTINATION_PATH = '~'


with open('collected_data.json', 'r') as openfile:
    # Reading from json file
    json_object = json.load(openfile)
    openfile.close()

ip_standalone = json_object["ip_standalone"]


def mysql_setup_commands():
    """
    This function sets up the environment for mysql.
    """
    return """
#!/bin/bash
yes | sudo apt update
yes | sudo apt-get install mysql-server
# Sakila database
wget https://downloads.mysql.com/docs/sakila-db.tar.gz
tar -xf sakila-db.tar.gz
rm sakila-db.tar.gz
sudo mysql -e "SOURCE sakila-db/sakila-schema.sql;
sudo mysql -e "SOURCE sakila-db/sakila-data.sql;"
sudo mysql -e "USE sakila;"
EOF
"""


def ssh_connect_with_retry(ssh, ip_address, retries):
    """
    This function connects via ssh on the instance.
    ssh : ssh
    ip_address : the ip address of the instance
    retries : the number of tries before it fails.
    """
    if retries > 3:
        return False
    privkey = paramiko.RSAKey.from_private_key_file(
        'labsuser.pem')
    interval = 2
    try:
        retries += 1
        print('SSH into the instance: {}'.format(ip_address))
        ssh.connect(hostname=ip_address,
                    username="ubuntu", pkey=privkey)
        return True
    except Exception as e:
        print(e)
        time.sleep(interval)
        print('Retrying SSH connection to {}'.format(ip_address))
        ssh_connect_with_retry(ssh, ip_address, retries)
    
def install_mysql(ip):
    """
    This function install mysql on the selected instance.
    ip : the ip of the instance
    """
    # Setting Up SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_connect_with_retry(ssh, ip, 0)
    print("Connected through SSH!")

    # Installing Mysql
    print("Installing Mysql...")
    stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands())
    old_stdout = sys.stdout
    log_file = open("logfile.log", "w")
    print('env setup done \n stdout:', stdout.read(), file=log_file)
    log_file.close()
    print("Mysql installed!")

    ssh.close()
        
print("\n############### Installing Mysql ###############\n")

print(ip_standalone)
install_mysql(ip_standalone)

print("Mysql App Deployed On EC2 Instance!")
