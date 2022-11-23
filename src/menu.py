import boto3
import sys

def get_running_instances():
    """
    This function returns the ids of the running instances.
    returns a list containing the IDs of the instances.
    """
    ec2_resource = boto3.resource('ec2')
    instances = (ec2_resource.instances).filter()
    nb_running_instances = 0
    id_list = []
    for instance in instances:
        state = instance.state['Name']
        if (state == 'running'):
            id = instance.id
            instance_type = instance.instance_type
            id_list.append(id)
            nb_running_instances += 1
            ip = instance.public_ip_address
            print(str(nb_running_instances) + '. ' + str(id) + ' : ' + str(instance_type) +
                ' is running. Public IP : ' + str(ip))
    return id_list

def delete_sg():
    """
    This function delete the security group.
    """
    boto3.client('ec2').delete_security_group(
        GroupName='PROJECT',
    )
    print('Security Group PROJECT deleted.')


def terminate_instance(id_list):
    """
    This function terminates the specified instances.
    id_list : the IDs of the instances.
    """
    for instanceID in id_list:
        boto3.resource('ec2').instances.filter(
            InstanceIds=[instanceID]).terminate()
        print('Instance ' + str(instanceID) + ' is shutting down.')


def wait_for_instance_terminated(ids):
    """
    This function waits until the instances are in state "terminated".
    ids : the IDs of the instances.
    """
    print('Waiting for the instances to terminate...')
    waiter = boto3.client('ec2').get_waiter('instance_terminated')
    waiter.wait(
        InstanceIds=ids
    )
    print('All instances terminated.')


def shutdown_system(instances_ids):
    """
    This function shutdows the system.
    ids : the IDs of the instances that needs to be shut down.
    """
    print('Shutting down system...')
    terminate_instance(instances_ids)
    wait_for_instance_terminated(instances_ids)
    delete_sg()
    print('System shutdown.')


id_list = [id]
while True:
    print('\nMenu :')
    print('    press \'i\' to get informations. ')
    print('    press \'q\' to quit. ')
    print('    press \'s\' to shutdown everything. ')
    line = input('> ')
    if (line == 'i'):
        print('\nRunning instances :')
        id_list = get_running_instances()
    elif (line == 'q'):
        sys.exit()
    elif (line == 's'):
        shutdown_system(id_list)
    elif (line == ''):
        continue
    else:
        print('Unknown commad.')
