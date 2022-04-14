FROM ubuntu:latest

RUN apt-get update && apt-get -y install sudo nano git wget curl openssh-server \
    iptables iproute2 net-tools build-essential software-properties-common \
    libpoppler-cpp-dev pkg-config python3-pip python3-venv python3-dev qpdf

#RUN apt-get -y install apt-utils

# # Python Packages
# RUN python3 -m pip install cluster
# RUN python3 -m pip install pdfrw
# # RUN python3 -m pip install pdftotext
# # RUN python3 -m pip install pdf2image
# # RUN python3 -m pip install pyperclip
# RUN python3 -m pip install requests
# #RUN python3 -m pip install img2pdf
# RUN python3 -m pip install pdfminer.six
# RUN python3 -m pip install redis
# RUN python3 -m pip install tqdm
# RUN python3 -m pip install seaborn
# RUN python3 -m pip install matplotlib
# RUN python3 -m pip install numpy
# RUN python3 -m pip install deepdiff
# RUN python3 -m pip install Pillow
# #RUN python3 -m pip install PyPDF2
# RUN python3 -m pip install flask
# RUN python3 -m pip install sanic
# RUN python3 -m pip install sanic_limiter
# RUN python3 -m pip install werkzeug
# RUN python3 -m pip install aiofiles
# #RUN python3 -m pip install PyMuPDF
# #RUN python3 -m pip fitz

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
