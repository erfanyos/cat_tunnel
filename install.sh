#!/bin/bash

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${GREEN}[!] Please run as root.${NC}"
        exit 1
    fi
}

print_cat() {
    clear
    cat << "EOF"
 /\_/\  
( o.o )  cat tunnel
 > ^ <
EOF
    echo -e "${CYAN}Welcome to Cat Tunnel Installer${NC}"
    echo
}

install_dependencies() {
    echo -e "${GREEN}[+] Updating packages and installing dependencies...${NC}"
    apt-get update
    apt-get install -y python3 python3-pip iproute2 net-tools haproxy
    pip3 install --upgrade pip
    pip3 install termcolor pyfiglet
    echo -e "${GREEN}[+] Dependencies installed.${NC}"
}

run_cat_tunnel_py() {
    python3 cat_tunnel.py "$@"
}

main_menu() {
    print_cat
    echo "Please choose an option:"
    echo "1) Setup Cat Tunnel - Iran Server"
    echo "2) Setup Cat Tunnel - Kharej Server"
    echo "3) Install and Configure HAProxy"
    echo "4) Install and Enable TCP Hybla Congestion Control"
    echo "5) Remove Cat Tunnel Completely"
    echo "9) Exit"
    echo

    read -p "Enter your choice: " choice

    case "$choice" in
        1)
            run_cat_tunnel_py --role iran
            ;;
        2)
            run_cat_tunnel_py --role kharej
            ;;
        3)
            run_cat_tunnel_py --haproxy
            ;;
        4)
            run_cat_tunnel_py --hybla
            ;;
        5)
            run_cat_tunnel_py --remove
            ;;
        9)
            echo "Bye!"
            exit 0
            ;;
        *)
            echo -e "${GREEN}[!] Invalid choice. Try again.${NC}"
            ;;
    esac
    sleep 2
}

check_root
install_dependencies

while true; do
    main_menu
done
