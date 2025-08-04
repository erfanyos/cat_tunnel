#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import shutil
from time import sleep

def install_python_package(package):
    try:
        __import__(package)
    except ImportError:
        print(f"[+] Installing python package: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def install_system_packages():
    print("[+] Checking and installing system dependencies (apt-get update & install)...")
    subprocess.run("apt-get update", shell=True)
    packages = ["iproute2", "net-tools", "haproxy", "python3-pip"]
    for pkg in packages:
        result = subprocess.run(f"dpkg -s {pkg}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"[+] Installing system package: {pkg}")
            subprocess.run(f"apt-get install -y {pkg}", shell=True)

install_python_package("termcolor")
install_python_package("pyfiglet")

from termcolor import colored
import pyfiglet

VXLAN_ID = 1
VXLAN_IF = f"vxlan{VXLAN_ID:02d}"
SUBNET = "10.2.2.0/24"
IP_IRAN = "10.2.2.10/24"
IP_KHAREJ = "10.2.2.11/24"

def print_cat():
    cat_art = r"""
 /\_/\  
( o.o )  Cat Tunnel
 > ^ <
"""
    print(colored(cat_art, "cyan"))

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def check_root():
    if os.geteuid() != 0:
        print(colored("[!] Please run this script as root.", "red"))
        sys.exit(1)

def get_default_interface():
    code, out, err = run_cmd("ip route get 1.1.1.1 | awk '{print $5}' | head -n1")
    if code != 0 or not out:
        print(colored("[!] Cannot detect main network interface.", "red"))
        sys.exit(1)
    return out

def validate_port(port):
    return port.isdigit() and 1 <= int(port) <= 64435

def ask_port(prompt):
    while True:
        port = input(prompt).strip()
        if validate_port(port):
            return port
        else:
            print(colored("Invalid port! Must be 1-64435.", "red"))

def ask_yes_no(prompt):
    while True:
        choice = input(prompt + " (y/n): ").strip().lower()
        if choice in ['y', 'n']:
            return choice == 'y'
        print(colored("Please answer y or n.", "red"))

def setup_vxlan(role):
    print_cat()
    print(colored(f"Setting up VXLAN tunnel for role: {role}", "yellow"))
    install_system_packages()
    iran_ip = input("Enter IRAN server IP: ").strip()
    kharej_ip = input("Enter Kharej server IP: ").strip()
    port = ask_port("Enter tunnel port (1-64435): ")
    iface = get_default_interface()
    local_ip = iran_ip if role == "iran" else kharej_ip
    remote_ip = kharej_ip if role == "iran" else iran_ip
    local_vxlan_ip = IP_IRAN if role == "iran" else IP_KHAREJ

    print(colored(f"\nCreating VXLAN interface {VXLAN_IF} ...", "green"))
    run_cmd(f"ip link del {VXLAN_IF} 2>/dev/null")
    cmd_add = (
        f"ip link add {VXLAN_IF} type vxlan id {VXLAN_ID} local {local_ip} "
        f"remote {remote_ip} dev {iface} dstport {port} nolearning"
    )
    code, out, err = run_cmd(cmd_add)
    if code != 0:
        print(colored(f"[!] Failed to create VXLAN interface: {err}", "red"))
        sys.exit(1)

    run_cmd(f"ip addr add {local_vxlan_ip} dev {VXLAN_IF}")
    run_cmd(f"ip link set {VXLAN_IF} up")
    run_cmd(f"iptables -I INPUT 1 -p udp --dport {port} -j ACCEPT")
    run_cmd(f"iptables -I INPUT 1 -s {remote_ip} -j ACCEPT")
    run_cmd(f"iptables -I INPUT 1 -s {local_vxlan_ip.split('/')[0]} -j ACCEPT")

    print(colored("[+] VXLAN tunnel setup complete!", "green"))

    # ساخت اسکریپت bash برای راه‌اندازی VXLAN
    script_path = "/usr/local/bin/vxlan_cat_tunnel.sh"
    with open(script_path, "w") as f:
        f.write(f"""#!/bin/bash
ip link del {VXLAN_IF} 2>/dev/null
ip link add {VXLAN_IF} type vxlan id {VXLAN_ID} local {local_ip} remote {remote_ip} dev {iface} dstport {port} nolearning
ip addr add {local_vxlan_ip} dev {VXLAN_IF}
ip link set {VXLAN_IF} up
( while true; do ping -c 1 {remote_ip} > /dev/null 2>&1; sleep 30; done ) &
""")
    os.chmod(script_path, 0o755)

    # ساخت سرویس systemd برای راه‌اندازی VXLAN
    service_path = "/etc/systemd/system/vxlan_cat_tunnel.service"
    with open(service_path, "w") as f:
        f.write(f"""[Unit]
Description=Cat Tunnel VXLAN Service
After=network.target

[Service]
Type=oneshot
ExecStart={script_path}
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""")
    run_cmd("systemctl daemon-reload")
    run_cmd("systemctl enable vxlan_cat_tunnel.service")
    run_cmd("systemctl restart vxlan_cat_tunnel.service")
    print(colored("[+] Cat systemd service created and started!", "green"))

    # ساخت فایل تایمر برای ری‌استارت هر ۵ ساعت
    timer_path = "/etc/systemd/system/vxlan_timer.timer"
    with open(timer_path, "w") as f:
        f.write(f"""[Unit]
Description=Timer to restart VXLAN every 5 hours

[Timer]
OnBootSec=5h
OnUnitActiveSec=5h
Unit=vxlan_restart.service

[Install]
WantedBy=timers.target
""")
    # ساخت سرویس برای ری‌استارت کردن
    restart_service_path = "/etc/systemd/system/vxlan_restart.service"
    with open(restart_service_path, "w") as f:
        f.write(f"""[Unit]
Description=Restart VXLAN Service

[Service]
Type=oneshot
ExecStart=/bin/systemctl restart vxlan_cat_tunnel.service
""")
    # فعال‌سازی تایمر
    run_cmd("systemctl daemon-reload")
    run_cmd("systemctl enable vxlan_timer.timer")
    run_cmd("systemctl start vxlan_timer.timer")
    print(colored("[+] Cat tunnel restart timer created and started!", "green"))
    print(colored("ip local iran: 10.2.2.10 \n ip local kharej: 10.2.2.11", "yellow"))
    sleep(3)

def install_haproxy():
    print_cat()
    print(colored("Installing and configuring HAProxy...", "yellow"))
    install_system_packages()
    subprocess.run("apt update && apt install -y haproxy", shell=True)
    cfg_file = "/etc/haproxy/haproxy.cfg"
    backup_file = "/etc/haproxy/haproxy.cfg.bak"
    if os.path.exists(cfg_file):
        shutil.copy(cfg_file, backup_file)
    with open(cfg_file, "w") as f:
        f.write("""global
    daemon
    maxconn 256
    user haproxy
    group haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    log /dev/log local0

defaults
    mode tcp
    option dontlognull
    timeout connect 5000ms
    timeout client  50000ms
    timeout server  50000ms
""")
    subprocess.run("systemctl restart haproxy", shell=True)
    print(colored("[+] HAProxy restarted.", "green"))
    sleep(2)

    while True:
        ips = input("Enter target IPs (comma separated): ").strip()
        ports = input("Enter ports (comma separated): ").strip()

        if not ips or not ports:
            print(colored("IPs and ports cannot be empty.", "red"))
            continue

        ip_list = [ip.strip() for ip in ips.split(",")]
        port_list = [port.strip() for port in ports.split(",")]

        with open(cfg_file, "a") as f:
            for port in port_list:
                f.write(f"\nfrontend frontend_{port}\n")
                f.write(f"    bind *:{port}\n")
                f.write(f"    default_backend backend_{port}\n\n")
                f.write(f"backend backend_{port}\n")
                for idx, ip in enumerate(ip_list):
                    backup_flag = " backup" if idx != 0 else ""
                    f.write(f"    server server{idx+1} {ip}:{port} check{backup_flag}\n")

        code = subprocess.call(f"haproxy -c -f {cfg_file}", shell=True)
        if code != 0:
            print(colored("[!] HAProxy configuration invalid. Try again.", "red"))
            with open(cfg_file, "r") as f:
                lines = f.readlines()
            idx = next((i for i, line in enumerate(lines) if line.strip() == "defaults"), None)
            if idx is not None:
                with open(cfg_file, "w") as fw:
                    fw.writelines(lines[:idx+1])
            continue
        else:
            print(colored("[+] HAProxy configuration valid and updated.", "green"))
            subprocess.run("systemctl restart haproxy", shell=True)
            break

def install_hybla():
    print_cat()
    print(colored("Installing and enabling TCP Hybla Congestion Control...", "yellow"))
    subprocess.run("modprobe tcp_hybla", shell=True)
    subprocess.run("sysctl -w net.ipv4.tcp_congestion_control=hybla", shell=True)
    with open("/etc/sysctl.conf", "a") as f:
        f.write("\nnet.ipv4.tcp_congestion_control=hybla\n")
    print(colored("[+] TCP Hybla enabled successfully.", "green"))
    sleep(2)

def remove_all():
    print_cat()
    print(colored("Removing Cat Tunnel setup...", "yellow"))
    subprocess.run("systemctl stop vxlan_cat_tunnel.service", shell=True)
    subprocess.run("systemctl disable vxlan_cat_tunnel.service", shell=True)
    if os.path.exists("/etc/systemd/system/vxlan_cat_tunnel.service"):
        os.remove("/etc/systemd/system/vxlan_cat_tunnel.service")
    if os.path.exists("/usr/local/bin/vxlan_cat_tunnel.sh"):
        os.remove("/usr/local/bin/vxlan_cat_tunnel.sh")
    subprocess.run(f"ip link del {VXLAN_IF}", shell=True)
    subprocess.run(f"iptables -D INPUT -p udp --dport 1:65535 -j ACCEPT", shell=True)
    subprocess.run("systemctl stop haproxy", shell=True)
    subprocess.run("apt-get remove --purge -y haproxy", shell=True)
    subprocess.run("apt-get autoremove -y", shell=True)
    print(colored("[+] Removal complete.", "green"))
    sleep(2)

def main():
    check_root()
    parser = argparse.ArgumentParser(description="Cat Tunnel Tool")
    parser.add_argument("--role", choices=["iran", "kharej"], help="Setup VXLAN tunnel role")
    parser.add_argument("--haproxy", action="store_true", help="Install and configure HAProxy")
    parser.add_argument("--hybla", action="store_true", help="Install and enable TCP Hybla")
    parser.add_argument("--remove", action="store_true", help="Remove Cat Tunnel completely")
    args = parser.parse_args()

    if args.role:
        setup_vxlan(args.role)
    elif args.haproxy:
        install_haproxy()
    elif args.hybla:
        install_hybla()
    elif args.remove:
        remove_all()
    else:
        print_cat()
        print("Use one of the menu options from install.sh")

if __name__ == "__main__":
    main()