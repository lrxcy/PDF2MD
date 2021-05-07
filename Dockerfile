FROM ubuntu:latest

RUN apt-get update
#RUN apt-get -y install apt-utils
RUN apt-get -y install sudo
RUN apt-get -y install nano
RUN apt-get -y install git
RUN apt-get -y install wget
RUN apt-get -y install curl
RUN apt-get -y install openssh-server
RUN apt-get -y install iptables
RUN apt-get -y install iproute2
RUN apt-get -y install net-tools
RUN apt-get -y install build-essential
RUN apt-get -y install software-properties-common
RUN apt-get -y install libpoppler-cpp-dev
RUN apt-get -y install pkg-config

# Python Dependencies
RUN apt-get -y install python3-pip
RUN apt-get -y install python3-venv
RUN apt-get -y install python3-dev
RUN apt-get -y install qpdf

# Python Packages
RUN python3 -m pip install cluster
RUN python3 -m pip install pdfrw
# RUN python3 -m pip install pdftotext
# RUN python3 -m pip install pdf2image
# RUN python3 -m pip install pyperclip
RUN python3 -m pip install requests
#RUN python3 -m pip install img2pdf
RUN python3 -m pip install pdfminer.six
RUN python3 -m pip install redis
RUN python3 -m pip install tqdm
RUN python3 -m pip install seaborn
RUN python3 -m pip install matplotlib
RUN python3 -m pip install numpy
RUN python3 -m pip install deepdiff
RUN python3 -m pip install Pillow
#RUN python3 -m pip install PyPDF2
RUN python3 -m pip install flask
RUN python3 -m pip install sanic
RUN python3 -m pip install sanic_limiter
RUN python3 -m pip install werkzeug
RUN python3 -m pip install aiofiles
#RUN python3 -m pip install PyMuPDF
#RUN python3 -m pip fitz

# Create User
RUN useradd -ms /bin/bash morphs -p lamorsa
RUN mkdir -p /home/morphs
RUN chown -R morphs:morphs /home/morphs
RUN usermod -aG sudo morphs
RUN echo 'morphs ALL=(ALL) NOPASSWD:ALL' | tee -a /etc/sudoers
USER morphs
WORKDIR /home/morphs

COPY main.py /home/morphs/main.py
#ENTRYPOINT [ "/bin/bash" ]
ENTRYPOINT [ "python3" , "/home/morphs/main.py" ]