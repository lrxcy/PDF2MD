FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get -y install sudo nano git wget curl openssh-server \
    iptables iproute2 net-tools build-essential software-properties-common \
    libpoppler-cpp-dev pkg-config python3-pip python3-venv python3-dev qpdf

#RUN apt-get -y install apt-utils

# Create User
RUN useradd -ms /bin/bash morphs -p lamorsa && mkdir -p /home/morphs && \
    chown -R morphs:morphs /home/morphs && \
    usermod -aG sudo morphs && \
    echo 'morphs ALL=(ALL) NOPASSWD:ALL' | tee -a /etc/sudoers

USER morphs
WORKDIR /home/morphs

COPY main.py /home/morphs/main.py
COPY requirements.txt /home/morphs/requirements.txt

RUN python3 -m pip install -r /home/morphs/requirements.txt

#ENTRYPOINT [ "/bin/bash" ]
ENTRYPOINT [ "python3" , "/home/morphs/main.py" ]
