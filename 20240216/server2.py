import socket
import subprocess
import signal
import time
import sys

host = '192.168.0.13'
port = 3030

# DROP 12.1.0.0/16
subprocess.run("docker exec -i -t oai-spgwu /bin/bash -c 'iptables -A FORWARD -s 12.1.0.0/16 -j DROP'", shell=True, check=True)
# ACCEPT 192.168.0.12(TINM)
subprocess.run("docker exec -i -t oai-spgwu /bin/bash -c 'iptables -I FORWARD 1 -s 12.1.0.0/16 -d 192.168.0.12 -j ACCEPT'", shell=True, check=True)

accept_list = []    # iptables 관리용 ip list

# FILE READ & UPDATE IP_LIST
def read_file(file_list):
 
    # output.json 있는 ip를 중복없이 parameter에 저장
    f = open("output.json", "r")
    for line in f:
        ip = line.split(",")[-1].strip()
        file_list.append(ip)
    file_list = list(set(file_list))
    f.close()
    
    return file_list


# INSERT & DELETE IPTABLES RULE
def check_and_update_ip_lists():
    global accept_list
    ip_list = []

    # tshark ip를 ip_list에 저장
    ip_list = read_file(ip_list)

    # accept_list
    for new_ip in ip_list:
        if new_ip not in accept_list:
            subprocess.run(f"docker exec -i -t oai-spgwu /bin/bash -c 'iptables -I FORWARD 1 -j ACCEPT -s {new_ip}'", shell=True, check=True)
            accept_list.append(new_ip)
            print(f"accept list = {accept_list}")

    # accept_list에 있는 ip가 ip_list에 없을 때, delete rule
    for ip in accept_list:
        if ip not in ip_list:
            print(f"drop ip :  {ip}")
            subprocess.run(f"docker exec -i -t oai-spgwu /bin/bash -c 'iptables -D FORWARD -j ACCEPT -s {ip}'", shell=True, check=True)
            accept_list.remove(ip)
            print(f"accept list (after drop) = {accept_list}")
            

# SIGINT HANDLER FUNCTION
def handler(signum, frame):
    print("\nPRESS CTRL + C")
    
    # iptables reset
    subprocess.run("docker exec -i -t oai-spgwu /bin/bash -c 'iptables -F'", shell=True, check=True)

    #강제 종료
    sys.exit(0)


# SIGINT
signal.signal(signal.SIGINT, handler)

# UDP_SOCKET_PROGRAMMING
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((host, port))

print(f"UDP 서버가 {host}:{port}에서 실행 중입니다.")

while True:
    data, client_address = server_socket.recvfrom(1024)

    data = data.decode('utf-8')
    print(f"클라이언트로부터 수신: {data}")

    # 무한 루프 & 1초마다 반복 실행 (tshark)
    while(True):
        subprocess.run("tshark -i demo-oai -Y '(ip.src==12.1.0.0/16)&&(ip.dst==192.168.0.12)&&(frame.len eq 98)' -T fields -e ip.src -a 'duration:3' -e json > output.json", shell=True, capture_output=True, text=True)
        check_and_update_ip_lists()
        time.sleep(1)   
