from concurrent.futures import wait
import boto3
import time
import json

AWS_REGION = 'us-east-1'
INSTANCE_TYPE = "t2.micro"
KEY_PAIR_NAME = "vockey"
AMI_ID = "ami-061dbd1209944525c"
NB_INSTANCES = 6

ec2_client = boto3.client("ec2", region_name=AWS_REGION)
ec2_resource = boto3.resource('ec2', region_name=AWS_REGION)

def get_vpc_id_and_subnet_id():
    """
    This function returns the id of the default vpc and of the first subnet.
    Returns vpc_id, subnet_id.
    """
    response = ec2_client.describe_vpcs()
    vpc_id = response['Vpcs'][0]['VpcId']
    response = ec2_client.describe_subnets(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    )
    subnet_id = response['Subnets'][0]['SubnetId']
    return vpc_id, subnet_id


def create_sg(vpcID):
    """
    This function creates a new security group for the VPC.
    vpcID : is the ID of the concerned VPC.
    Returns the security group ID.
    """
    response = ec2_client.create_security_group(GroupName="PROJECT",
                                                Description='SG_basic',
                                                VpcId=vpcID)
    security_group_id = response['GroupId']
    ec2_client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 80,
             'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 443,
             'ToPort': 443,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 1186,
             'ToPort': 1186,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 3306,
             'ToPort': 3306,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 30000,
             'ToPort': 65535,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'ICMP',
             'FromPort': -1,
             'ToPort': -1,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])
    ec2_client.authorize_security_group_egress(
        GroupId=security_group_id,
        IpPermissions=[
            {
                'FromPort': -1,
                'ToPort': -1,
                'IpProtocol': 'ICMP',
                'IpRanges': [
                    {
                        'CidrIp': '0.0.0.0/0',
                        'Description': "MySQL"
                    },
                ]
            }
        ]
    )
    return security_group_id


def create_ec2_instances(nbr, sg_id, subnet_id, name):
    """
    This function creates EC2 instances.
    nbr : is the desired number of instances to be created.
    type : the instance type. m4.large for example.
    sg_id : is the ID of the security group that you wish your instaces to follow.
    subnet_id : is the subnet where you instances will reside.
    """
    ec2_client.run_instances(
        MinCount=nbr,
        MaxCount=nbr,
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_PAIR_NAME,
        NetworkInterfaces=[{
            "DeviceIndex": 0,
            "Groups": [sg_id],
            "AssociatePublicIpAddress": True,
            "SubnetId": subnet_id
        }],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            },
        ]
    )


def wait_until_running_and_get_info():
    """
    This function waits for the EC2 instances to become available.
    returns the id, dns and the ip of the instances.
    """
    while (True):
        nb_running_instances = 0
        id_list_all = []
        id_list = {"slaves":[]}
        ip_list = {"slaves":[]}
        private_ip_list = {"slaves":[]}
        public_dns_list = {"slaves":[]}
        private_dns_list = {"slaves":[]}
        while (nb_running_instances < NB_INSTANCES):
            for instance in ec2_resource.instances.all():
                if instance.state["Name"] == "running":
                    id = instance.id
                    if id not in id_list_all:
                        id_list_all.append(id)
                        ip = instance.public_ip_address
                        private_ip = instance.private_ip_address
                        public_dns = instance.public_dns_name
                        private_dns = instance.private_dns_name
                        nb_running_instances += 1
                        name = "no name"
                        for tag in instance.tags:
                            if tag['Key'] == 'Name':
                                name = tag['Value']
                        if name == 'standalone':
                            id_list['standalone'] = id
                            ip_list['standalone'] = ip
                            private_ip_list['standalone'] = private_ip
                            public_dns_list['standalone'] = public_dns
                            private_dns_list['standalone'] = private_dns
                        elif name == 'master':
                            id_list['master'] = id
                            ip_list['master'] = ip
                            private_ip_list['master'] = private_ip
                            public_dns_list['master'] = public_dns
                            private_dns_list['master'] = private_dns
                        elif name == 'proxy':
                            id_list['proxy'] = id
                            ip_list['proxy'] = ip
                            private_ip_list['proxy'] = private_ip
                            public_dns_list['proxy'] = public_dns
                            private_dns_list['proxy'] = private_dns
                        else:
                            id_list["slaves"].append(id)
                            ip_list["slaves"].append(ip)
                            private_ip_list["slaves"].append(private_ip)
                            public_dns_list["slaves"].append(public_dns)
                            private_dns_list["slaves"].append(private_dns)
                        print(str(id) + ' : ' + str(name) +
                          ' is running.   (' + str(nb_running_instances) + '/5)')
            time.sleep(5)
        return id_list, ip_list, public_dns_list, private_dns_list, private_ip_list

# Start

print("\n############### SETTING UP THE SYSTEM ###############\n")

print("Creating security group...")
vpcID, subnet_id = get_vpc_id_and_subnet_id()
sg_id = create_sg(vpcID)
print("Done.")

print("\nCreating EC2 instances...")
create_ec2_instances(1, sg_id, subnet_id, "standalone")
print("Standalone server instance created.")

create_ec2_instances(1, sg_id, subnet_id, "master")
print("Master instance created.")

for i in 1,2,3:
    create_ec2_instances(1, sg_id, subnet_id, f"slave_{i}")
    print("Slave number " + str(i) + " instance created.")
    
create_ec2_instances(1, sg_id, subnet_id, "proxy")
print("Proxy instance created.")

print("\nWaiting for the EC2 instances to be running...")
id, ip, public_dns_list, private_dns_list, private_ip_list = wait_until_running_and_get_info()
print("All EC2 instances are running.")

# A dictionary to hold the resources IDs to store in a .json file for the other scripts to use
dictionary = {
    "sg_id": sg_id,
    "id_standalone": id["standalone"],
    "id_master": id["master"],
    "id_slaves": id["slaves"],
    "id_proxy": id["proxy"],
    "ip_standalone": ip["standalone"],
    "ip_master": ip["master"],
    "ip_slaves": ip["slaves"],
    "ip_proxy": ip["proxy"],
    "private_ip_standalone": private_ip_list["standalone"],
    "private_ip_master": private_ip_list["master"],
    "private_ip_slaves": private_ip_list["slaves"],
    "private_ip_proxy": private_ip_list["proxy"],
    "public_dns_standalone": public_dns_list["standalone"],
    "public_dns_master": public_dns_list["master"],
    "public_dns_slaves": public_dns_list["slaves"],
    "private_dns_standalone": private_dns_list["standalone"],
    "private_dns_master": private_dns_list["master"],
    "private_dns_slaves": private_dns_list["slaves"],
    }

# Serializing json
json_object = json.dumps(dictionary, indent=4)

# Writing to collected_data.json
with open("collected_data.json", "w") as outfile:
    outfile.write(json_object)

print("\n############### DONE SETTING UP THE SYSTEM ###############\n")