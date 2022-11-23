from concurrent.futures import wait
import boto3
import time

AWS_REGION = 'us-east-1'
INSTANCE_TYPE = "t2.micro"
KEY_PAIR_NAME = "vockey"
AMI_ID = "ami-08c40ec9ead489470"

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
    response = ec2_client.create_security_group(GroupName="LAB2",
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
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])
    return security_group_id


def create_ec2_instances(nbr, type, sg_id, subnet_id):
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
        }]
    )


def wait_until_running_and_get_ip():
    """
    This function waits for the EC2 instance to become available.
    returns the id and the ip the instance.
    """
    while (True):
        ec2 = boto3.resource('ec2')
        for instance in ec2.instances.all():
            if instance.state["Name"] == "running":
                return instance.id, instance.public_ip_address
        time.sleep(5)


# Start

print("\n############### SETTING UP THE SYSTEM ###############\n")

print("Getting the vpc and the subnet IDs...")
vpcID, subnet_id = get_vpc_id_and_subnet_id()
print("IDs obtained!")

print("Creating the security group...")
sg_id = create_sg(vpcID)
print("Security group created!\n")

print("Creating the EC2 instance...")
create_ec2_instances(1, INSTANCE_TYPE, sg_id, subnet_id)
print("EC2 instance created!\n")

print("Waiting for the EC2 instance to get in the running state...")
id, ip = wait_until_running_and_get_ip()
print("EC2 instance is running!")

time.sleep(20)

print("\n############### DONE SETTING UP THE SYSTEM ###############\n")
