from os.path import isfile, join
from os import listdir
import paramiko
import time
import json
import sys
from scp import SCPClient

DESTINATION_PATH = '~'

FILES = ['collected_data.json','proxy.py','deploy.sh']

def ssh_connect_with_retry(ssh, ip_address, retries):
    """
    This function connects via ssh on the instance.
    ssh : the id of the instance
    ip_address : the ip addres sof the instance
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


def upload_files(ip):
    """
    This function sets up the environment and starts the scripts on the selected instance.
    ip : the ip of the instance
    """
    # Setting Up SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_connect_with_retry(ssh, ip, 0)
    print("Connected through SSH!")

    print("Sending the necessary files...")
    scp = SCPClient(ssh.get_transport())
    scp.put(
        FILES,
        remote_path=DESTINATION_PATH,
        recursive=True
    )

    time.sleep(20)

    print("Files sent!")

    print("preparing .sh files for execution...")
    stdin, stdout, stderr = ssh.exec_command("sh deploy.sh")
    old_stdout = sys.stdout
    log_file = open("logfile.log", "w")
    print('env setup done \n stdout:', stdout.read(), file=log_file)
    log_file.close()

    ssh.close()


# Retrieving the data from the .json file
with open('collected_data.json', 'r') as openfile:
    json_object = json.load(openfile)
    openfile.close()
    
ip_proxy = json_object["ip_proxy"]

print("\n############### Sending the necessary files to the proxy ###############\n")

upload_files(ip_proxy)

print("\n############### Done sending the files ###############\n")
