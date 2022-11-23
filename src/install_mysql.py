import paramiko
import time
import sys
import boto3

AWS_REGION = 'us-east-1'
DESTINATION_PATH = '~'

def mysql_setup_commands():
    """
    This function sets up the environment for mysql.
    """
    return """
#!/bin/bash
yes | sudo apt update
yes | sudo apt-get install mysql-server
EOF
"""


'''
#!/bin/bash
yes | sudo apt update
yes | sudo apt install default-jdk
wget https://downloads.apache.org/hadoop/common/hadoop-3.3.1/hadoop-3.3.1.tar.gz
tar -xzvf hadoop-3.3.1.tar.gz
rm hadoop-3.3.1.tar.gz
sudo mv hadoop-3.3.1 /usr/local/hadoop
link_to_java=$(readlink -f /usr/bin/java | sed "s:bin/java::")
echo "export JAVA_HOME=$link_to_java" >> /usr/local/hadoop/etc/hadoop/hadoop-env.sh
sed -i -e 's/\\r$//' config_hadoop_file.sh
chmod +x config_hadoop_file.sh
bash config_hadoop_file.sh
EOF
'''


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


def get_id_ips():
    """
    This function ...
    """
    ec2_client = boto3.client("ec2", region_name=AWS_REGION)
    reservations = ec2_client.describe_instances(Filters=[
        {
            "Name": "instance-state-name",
            "Values": ["running"],
        }
    ]).get("Reservations")
    ids = []
    print("Found the following instances: \n")
    for reservation in reservations:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]
            public_ip = instance["PublicIpAddress"]
            private_ip = instance["PrivateIpAddress"]
            ids.append((instance_id, public_ip))
            print(
                f"instance id :{instance_id}, instance type: {instance_type}, public ip:{public_ip}, private ip:{private_ip}")
    print("\n")
    return ids
    
    
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

def deploy_app():
    """
    This function deploys the applications, scripts on the instance.
    """
    running = False
    id_ip = None
    while (not running):
        try:
            instances_IDs_IPs = get_id_ips()
            id_ip = instances_IDs_IPs[0][1]
            running = True
        except:
            print("Waiting for the instance to be running .. (10s)")
            time.sleep(10)
    print(id_ip)
    install_mysql(id_ip)
    
    
print("\n############### Installing Mysql ###############\n")

deploy_app()

print("Mysql App Deployed On EC2 Instance!")
