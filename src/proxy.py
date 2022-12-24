import sys
import json
import random
import pymysql
import pymysql.cursors
from pythonping import ping
from sshtunnel import SSHTunnelForwarder

def send_query(ip, ip_master, query):
    '''
    Sends the query to the selected node.
    source : https://pymysql.readthedocs.io/en/latest/user/examples.html
    ip : the ip of the node
    query : the query
    '''
    tunnel = SSHTunnelForwarder(
        ip, 
        ssh_username="ubuntu",
        ssh_password="new_key.pem",
        remote_bind_address=(ip_master, 3306))
    tunnel.start
    connection = pymysql.connect(host=ip_master,
                        user='myapp',
                        password='password',
                        database='sakila',
                        charset='utf8mb4',
                        port=3306, 
                        autocommit=True)
    with connection:
        if (query=='example'):
            with connection.cursor() as cursor:
                # Example
                print("Example for the query 'SELECT * FROM actor;' : ")
                sql = 'SELECT * FROM actor;'
                cursor.execute(sql)
                result = cursor.fetchall()
            for line in result:
                print(line)
        else:
            with connection.cursor() as cursor:
                # Custom query
                cursor.execute(query)
                result = cursor.fetchall()
                for line in result:
                    print(line)

    
def is_write_request(request):
    '''
    Determines of the query needs write access.
    request: the requested instruction
    '''
    is_write = False
    instructions = request.split(";")
    for instruction in instructions:
        keyword = instruction.strip().lower().split()
        if len(keyword)>0 and keyword[0] in ["alter","rename","create","drop","delete","update","insert","grant","revoke","merge"]:
            is_write = True
    return is_write

def direct_hit(ip_master, query):
    '''
    Directly forward incoming requests to MySQL master node.
    '''
    send_query(ip_master, ip_master, query)
    
def rand(ip_slaves, ip_master, query):
    '''
    Randomly choose a slave node on MySQL cluster and forward the request to it.
    '''
    slave = ip_slaves[random.randint(0,2)]
    print('Selected : ' + str(slave))
    send_query(slave, ip_master, query)

def customized(ips, ip_master, query):
    '''
    Measure the ping time of all the servers and forward the message to one with less response time.
    return the ip of the server with the lowest ping
    '''
    best = None
    time = 10000
    for ip in ips:
        ping_result = ping(ip, count=1, timeout=2)
        if ping_result.packet_loss != 1 and ping_result.rtt_avg_ms < time:
            best = ip
            time = ping_result.rtt_avg_ms
    if (best is not None):
        print('Best one : ' + str(best))
        send_query(best, ip_master, query)

def get_query():
    '''
    Gets and returns the query.
    '''
    print("Please type \'example\' for an example query.")
    return input('QUERY> ')


# Retrieving the data from the .json file
with open('collected_data.json', 'r') as openfile:
    json_object = json.load(openfile)
    openfile.close()
    
ip_slaves = json_object["private_ip_slaves"]
ip_master_list = [json_object["private_ip_master"]]
ip_master = json_object["private_ip_master"]
while True:
    print('\nProxy :')
    print('    press \'1\' for direct hit (default if write query). ')
    print('    press \'2\' for random. ')
    print('    press \'3\' for customized. ')
    print('    press \'q\' to quit. ')
    line = input('> ')
    if (line == '1'):
        print('\nDirect hit')
        query = get_query()
        if len(query) > 0:
            direct_hit(ip_master, query)
    elif (line == '2'):
        print('\nRandom')
        query = get_query()
        if len(query) > 0:
            if (is_write_request(query)):
                print('Request needs write access. Forwarding to the master.')
                direct_hit(ip_master, query)
            else:
                rand(ip_slaves, ip_master, query)
    elif (line == '3'):
        print('\nCustomized')
        query = get_query()
        if len(query) > 0:
            if (is_write_request(query)):
                print('Request needs write access. Forwarding to the master.')
                direct_hit(ip_master, query)
            else:
                customized(ip_master_list+ip_slaves, ip_master, query)
    elif (line == 'q'):
        sys.exit()
    elif (line == ''):
        continue
    else:
        print('Unknown commad.')