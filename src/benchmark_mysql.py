import paramiko
import time
import sys
import boto3
import json
import scp
from scp import SCPClient

AWS_REGION = 'us-east-1'

# Retrieving the data from the .json file
with open('collected_data.json', 'r') as openfile:
    json_object = json.load(openfile)
    openfile.close()

ip_standalone = json_object["ip_standalone"]
ip_slaves = json_object["ip_slaves"]
ip_master = json_object["ip_master"]

def benchmark_standalone(threads):
    """
    This function benchmarks the MySQL Cluster.
    Source : https://www.jamescoyle.net/how-to/1131-benchmark-mysql-server-performance-with-sysbench
    """
    return f"""
#!/bin/bash
sudo sysbench oltp_read_write --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root prepare
sudo sysbench oltp_read_write --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root --num-threads={threads} --max-time=60 run >> standalone_rw_{threads}.txt
sudo sysbench oltp_read_write --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root cleanup

sudo sysbench oltp_read_only --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root prepare
sudo sysbench oltp_read_only --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root --num-threads={threads} --max-time=60 run >> standalone_r_{threads}.txt
sudo sysbench oltp_read_only --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root cleanup

sudo sysbench oltp_write_only --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root prepare
sudo sysbench oltp_write_only --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root --num-threads={threads} --max-time=60 run >> standalone_w_{threads}.txt
sudo sysbench oltp_write_only --table-size=1000000 --db-driver=mysql --mysql-db=sakila --mysql-user=root cleanup

EOF
"""

def benchmark_cluster(threads):
    """
    This function benchmarks the MySQL Cluster.
    Source : https://www.jamescoyle.net/how-to/1131-benchmark-mysql-server-performance-with-sysbench
    """
    return f"""
#!/bin/bash
sudo sysbench oltp_read_write --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root prepare
sudo sysbench oltp_read_write --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root --num-threads={threads} --max-time=60 run >> cluster_rw_{threads}.txt
sudo sysbench oltp_read_write --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root cleanup

sudo sysbench oltp_read_only --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root prepare
sudo sysbench oltp_read_only --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root --num-threads={threads} --max-time=60 run >> cluster_r_{threads}.txt
sudo sysbench oltp_read_only --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root cleanup

sudo sysbench oltp_write_only --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root prepare
sudo sysbench oltp_write_only --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root --num-threads={threads} --max-time=60 run >> cluster_w_{threads}.txt
sudo sysbench oltp_write_only --table-size=1000000 --mysql-host=127.0.0.1 --db-driver=mysql --mysql-db=sakila --mysql-user=root --mysql-password=root cleanup
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
    
def execute_commands(ip, instance):
    """
    This function executes the commands on the selected instance.
    ip : the ip of the instance
    instance : standolone or the cluster
    """
    # Setting Up SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_connect_with_retry(ssh, ip, 0)

    if (instance=='standalone'):  
        # Benchmark standalone
        # 3 threads
        print("Benchmarking standalone...")
        stdin, stdout, stderr = ssh.exec_command(benchmark_standalone(3))
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        # 6 threads
        stdin, stdout, stderr = ssh.exec_command(benchmark_standalone(6))
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
        
        print('Retrieving results files')
        scp = SCPClient(ssh.get_transport())
        scp.get('/home/ubuntu/standalone_rw_3.txt', 'results/')
        scp.get('/home/ubuntu/standalone_rw_6.txt', 'results/')
        scp.get('/home/ubuntu/standalone_r_3.txt', 'results/')
        scp.get('/home/ubuntu/standalone_r_6.txt', 'results/')
        scp.get('/home/ubuntu/standalone_w_3.txt', 'results/')
        scp.get('/home/ubuntu/standalone_w_6.txt', 'results/')
        print('Standalone results files are in folder /results')
        scp.close()
    elif (instance=='cluster'):
        # Benchmark cluster
        # 3 threads
        print("Benchmarking the cluster...")
        stdin, stdout, stderr = ssh.exec_command(benchmark_cluster(3))
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        # 6 threads
        stdin, stdout, stderr = ssh.exec_command(benchmark_cluster(6))
        old_stdout = sys.stdout
        log_file = open("logfile.log", "w")
        print('env setup done \n stdout:', stdout.read(), file=log_file)
        log_file.close()
        print("Done.")
        
        print('Retrieving results files')
        scp = SCPClient(ssh.get_transport())
        scp.get('/home/ubuntu/cluster_rw_3.txt', 'results/')
        scp.get('/home/ubuntu/cluster_rw_6.txt', 'results/')
        scp.get('/home/ubuntu/cluster_r_3.txt', 'results/')
        scp.get('/home/ubuntu/cluster_r_6.txt', 'results/')
        scp.get('/home/ubuntu/cluster_w_3.txt', 'results/')
        scp.get('/home/ubuntu/cluster_w_6.txt', 'results/')
        print('Cluster results files are in folder /results')
        scp.close()
    ssh.close()
        
print("\n############### Benchmarking Mysql ###############\n")

execute_commands(ip_standalone, 'standalone')
execute_commands(ip_master, 'cluster')
print("MySQL benchmark done!")
