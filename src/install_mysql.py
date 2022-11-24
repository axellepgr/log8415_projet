import paramiko
import time
import sys
import boto3
import json

AWS_REGION = 'us-east-1'
DESTINATION_PATH = '~'

# Retrieving the data from the .json file
with open('collected_data.json', 'r') as openfile:
    json_object = json.load(openfile)
    openfile.close()

ip_standalone = json_object["ip_standalone"]
ip_slaves = json_object["ip_slaves"]
ip_master = json_object["ip_master"]
private_dns_slaves = json_object["private_dns_slaves"]

# sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root';" ??
def mysql_setup_commands_server():
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

def mysql_setup_commands_cluster():
    """
    This function sets up the environment for mysql.
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    """
    return """
#!/bin/bash
yes | sudo apt update
sudo mkdir -p /opt/mysqlcluster/home
sudo chmod -R 777 /opt/mysqlcluster
cd /opt/mysqlcluster/home
wget http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
tar xvf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz -C /opt/mysqlcluster/home/
ln -s /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64 /opt/mysqlcluster/home/mysqlc
sudo chmod -R 777 /etc/profile.d/
echo 'export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc' > /etc/profile.d/mysqlc.sh
echo 'export PATH=$MYSQLC_HOME/bin:$PATH' >> /etc/profile.d/mysqlc.sh
source /etc/profile.d/mysqlc.sh
sudo apt-get update && sudo apt-get -y install libncurses5
EOF
"""

def mysql_setup_commands_master(private_dns_slaves):
    """
    This function sets up the environment for mysql.
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    """
    return f"""
#!/bin/bash
sudo mkdir -p /opt/mysqlcluster/deploy
cd /opt/mysqlcluster/deploy
sudo chmod -R 777 /opt/mysqlcluster/deploy
sudo mkdir conf
sudo mkdir mysqld_data
sudo mkdir ndb_data
cd conf

echo "[mysqld]
ndbcluster
datadir=/opt/mysqlcluster/deploy/mysqld_data
basedir=/opt/mysqlcluster/home/mysqlc
port=3306" >> /opt/mysqlcluster/deploy/conf/my.cnf

echo f"[ndb_mgmd]
hostname=domU-12-31-39-04-D6-A3.compute-1.internal
datadir=/opt/mysqlcluster/deploy/ndb_data
nodeid=1

[ndbd default]
noofreplicas=3
datadir=/opt/mysqlcluster/deploy/ndb_data

[ndbd]
hostname={private_dns_slaves[0]}
nodeid=3

[ndbd]
hostname={private_dns_slaves[1]}
nodeid=4

[ndbd]
hostname={private_dns_slaves[2]}
nodeid=5

[mysqld]
nodeid=50" >> /opt/mysqlcluster/deploy/conf/config.ini

cd /opt/mysqlcluster/home/mysqlc
/opt/mysqlcluster/home/mysqlc/scripts/mysql_install_db –no-defaults –datadir=/opt/mysqlcluster/deploy/mysqld_data
/opt/mysqlcluster/home/mysqlc/bin/ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf/
EOF
"""

def mysql_setup_commands_slaves(private_dns):
    """
    This function sets up the environment for mysql.
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    """
    return f"""
#!/bin/bash
sudo mkdir -p /opt/mysqlcluster/deploy/ndb_data
/opt/mysqlcluster/home/mysqlc/bin/ndbd -c {private_dns}:1186
EOF
"""

def mysql_start_commands_master():
    """
    This function starts the environment for the master.
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    """
    return """
#!/bin/bash
/opt/mysqlcluster/home/mysqlc/bin/mysqld –defaults-file=/opt/mysqlcluster/deploy/conf/my.cnf –user=root &
EOF
"""


def mysql_set_up_users_master():
    """
    This function starts the environment for the master.
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    """
    return """
#!/bin/bash
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
        print('\nSSH into the instance: {}'.format(ip_address))
        ssh.connect(hostname=ip_address,
                    username="ubuntu", pkey=privkey)
        return True
    except Exception as e:
        print(e)
        time.sleep(interval)
        print('Retrying SSH connection to {}'.format(ip_address))
        ssh_connect_with_retry(ssh, ip_address, retries)
    
def install_mysql(ip, instance, private_dns):
    """
    This function install mysql on the selected instance.
    ip : the ip of the instance
    """
    # Setting Up SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_connect_with_retry(ssh, ip, 0)

    if (instance=='server'):           
        # Installing Mysql on the server
        print("Installing Mysql on the server...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_server())
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
    elif (instance=='cluster'):
        # Installing Mysql on the clusters
        print("Installing Mysql on the clusters...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_cluster())
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
        # Installing Mysql on the clusters
        print("Setting up Mysql on the master...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_master(private_dns))
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
    elif (instance=='slave'):           
        # Installing Mysql on the slaves
        print("Installing Mysql on the slaves...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_cluster())
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
        print("Binding the slave...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_slaves(private_dns))
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
    elif (instance=='master'):           
        # Initializing Mysql on the master
        print("Initializing Mysql on the master...")
        stdin, stdout, stderr = ssh.exec_command(mysql_start_commands_master())
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
        time.sleep(5)
        # Setting up users
        print("Setting up users...")
        stdin, stdout, stderr = ssh.exec_command(mysql_set_up_users_master())
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")        
    else:
        print("Error in instance name !")
    ssh.close()
        
print("\n############### Installing Mysql ###############\n")

install_mysql(ip_standalone, 'server', None)
install_mysql(ip_master, 'cluster', private_dns_slaves)
for i in range(len(ip_slaves)):
    ip = ip_slaves[i]
    private_dns = private_dns_slaves[i]
    install_mysql(ip, 'slave', private_dns)
install_mysql(ip_master, 'master', None)
print("Mysql App Deployed On EC2 Instances!")
