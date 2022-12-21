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
private_ip_standalone = json_object["private_ip_standalone"]
private_ip_slaves = json_object["private_ip_slaves"]
private_ip_master = json_object["private_ip_master"]
private_dns_slaves = json_object["private_dns_slaves"]
private_dns_master = json_object["private_dns_master"]

# sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root';" ??
def mysql_setup_commands_server():
    """
    This function sets up the environment for mysql.
    """
    return """
#!/bin/bash
yes | sudo apt update
yes | sudo apt-get install mysql-server
# Sakila 
wget https://downloads.mysql.com/docs/sakila-db.tar.gz
tar -xf sakila-db.tar.gz
rm sakila-db.tar.gz
sudo mysql -e "
SOURCE sakila-db/sakila-schema.sql;
SOURCE sakila-db/sakila-data.sql;
USE sakila;
"
# Sysbench
yes | sudo apt-get install sysbench
EOF
"""

def mysql_setup_commands_nodes():
    """
    This function sets up the environment for mysql.
    Common Steps on all Nodes
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    """
    return """
#!/bin/bash
yes | sudo apt update
sudo mkdir -p /opt/mysqlcluster/home
sudo chmod -R 777 /opt/mysqlcluster
cd /opt/mysqlcluster/home
wget http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
tar -xvf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz -C /opt/mysqlcluster/home/
rm /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
ln -s /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64 /opt/mysqlcluster/home/mysqlc
sudo chmod -R 777 /etc/profile.d/
echo 'export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc' > /etc/profile.d/mysqlc.sh
echo 'export PATH=$MYSQLC_HOME/bin:$PATH' >> /etc/profile.d/mysqlc.sh
source /etc/profile.d/mysqlc.sh
sudo apt-get update && sudo apt-get -y install libncurses5
sudo apt-get install libaio1 libaio-dev
yes | sudo apt-get install sysbench
EOF
"""

def mysql_setup_commands_master(private_dns_slaves, private_dns_m, private_ips_slaves):
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
sudo chmod -R 777 /opt/mysqlcluster/deploy/conf
sudo chmod -R 777 /opt/mysqlcluster/deploy/mysqld_data
sudo chmod -R 777 /opt/mysqlcluster/deploy/ndb_data

echo "[mysqld]
ndbcluster
datadir=/opt/mysqlcluster/deploy/mysqld_data
basedir=/opt/mysqlcluster/home/mysqlc
port=3306" >> /opt/mysqlcluster/deploy/conf/my.cnf

echo "[ndb_mgmd]
hostname={private_dns_m}
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

sudo chmod 644 /opt/mysqlcluster/deploy/conf/my.cnf
sudo chmod 644 /opt/mysqlcluster/deploy/conf/config.ini
sudo ufw allow from {private_ips_slaves[0]}
sudo ufw allow from {private_ips_slaves[1]}
sudo ufw allow from {private_ips_slaves[2]}
/opt/mysqlcluster/home/mysqlc/scripts/mysql_install_db --no-defaults --datadir=/opt/mysqlcluster/deploy/mysqld_data --basedir=/opt/mysqlcluster/home/mysqlc
/opt/mysqlcluster/home/mysqlc/bin/ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf/
EOF
"""

def mysql_setup_commands_slaves(private_dns, private_ips_slaves, private_ip_m):
    """
    This function sets up the environment for mysql.
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    """
    return f"""
#!/bin/bash
sudo mkdir -p /opt/mysqlcluster/deploy/ndb_data
sudo chmod -R 777 /opt/mysqlcluster/deploy/ndb_data
sudo chmod -R 777 /opt/mysqlcluster/home/mysqlc/bin/
sudo ufw allow from {private_ips_slaves[0]}
sudo ufw allow from {private_ips_slaves[1]}
sudo ufw allow from {private_ips_slaves[2]}
sudo ufw allow from {private_ip_m}
/opt/mysqlcluster/home/mysqlc/bin/ndbd -c {private_dns}
EOF
"""

def mysql_start_commands_master():
    """
    This function starts the environment for the master.
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    """
    return """
#!/bin/bash
/opt/mysqlcluster/home/mysqlc/bin/mysqld --defaults-file=/opt/mysqlcluster/deploy/conf/my.cnf --user=root &
sleep 10s
EOF
"""


def mysql_set_up_users_master():
    """
    This function starts the environment for the master.
    Source : https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/
    https://dev.mysql.com/doc/sakila/en/sakila-installation.html
    """
    return """
#!/bin/bash
wget https://downloads.mysql.com/docs/sakila-db.tar.gz
tar -xf sakila-db.tar.gz
rm sakila-db.tar.gz

sudo /opt/mysqlcluster/home/mysqlc/bin/mysql -e "
CREATE USER 'myapp'@'localhost' IDENTIFIED BY 'testpwd';
GRANT ALL PRIVILEGES ON * . * TO 'myapp'@'localhost' IDENTIFIED BY 'root';"
sudo /opt/mysqlcluster/home/mysqlc/bin/mysql -e "
USE mysql; 
UPDATE user SET plugin='mysql_native_password' WHERE User='root';
FLUSH PRIVILEGES;SET PASSWORD FOR 'root'@'localhost' = PASSWORD('root');"

sudo /opt/mysqlcluster/home/mysqlc/bin/mysql -u root -proot "
SOURCE sakila-db/sakila-schema.sql;
SOURCE sakila-db/sakila-data.sql;
USE sakila;
"

/opt/mysqlcluster/home/mysqlc/bin/mysql -h 127.0.0.1 -e "SOURCE sakila-db/sakila-schema.sql;" -u root -proot
/opt/mysqlcluster/home/mysqlc/bin/mysql -h 127.0.0.1 -e "SOURCE sakila-db/sakila-data.sql;" -u root -proot
/opt/mysqlcluster/home/mysqlc/bin/mysql -h 127.0.0.1 -e "USE sakila;" -u root -proot
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
    
def install_mysql(ip, instance, private_dns, private_dns_master, private_ips_slaves, private_ip_m):
    """
    This function install mysql on the selected instance.
    ip : the ip of the instance
    instance : role of the instance
    private_dns, private_dns_master, private_ips_slaves, private_ip_m : data from the .json file
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
    elif (instance=='master1'):
        # Installing Mysql on the clusters
        print("Installing Mysql on the master...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_nodes())
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
        # Installing Mysql on the clusters
        print("Setting up Mysql on the master...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_master(private_dns, private_dns_master, private_ips_slaves))
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
    elif (instance=='slave'):           
        # Installing Mysql on the slaves
        print("Installing Mysql on the slaves...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_nodes())
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
        print("Binding the slave...")
        stdin, stdout, stderr = ssh.exec_command(mysql_setup_commands_slaves(private_dns_master, private_ips_slaves, private_ip_m))
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
    elif (instance=='master2'):           
        # Initializing Mysql on the master
        print("Starting Mysql on the master...")
        stdin, stdout, stderr = ssh.exec_command(mysql_start_commands_master())
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
    elif (instance=='master3'):               
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

install_mysql(ip_standalone, 'server', None, None, None, None)
install_mysql(ip_master, 'master1', private_dns_slaves, private_dns_master, private_ip_slaves, None)
for i in range(len(ip_slaves)):
    ip = ip_slaves[i]
    install_mysql(ip, 'slave', None, private_dns_master, private_ip_slaves, private_ip_master)
    print('Slave ' + str(i+1) + ' set up.')
time.sleep(10)
install_mysql(ip_master, 'master2', None, None, None, None)
time.sleep(40)
install_mysql(ip_master, 'master3', None, None, None, None)
print("Mysql App Deployed On EC2 Instances!")
