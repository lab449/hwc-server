# Installs ubuntu 20.04 from Docker HubRUN apt-get update
FROM python:3.8
ENV DEBIAN_FRONTEND noninteractive

LABEL maintainer="texnoman@itmo.ru"
RUN apt-get update

# Install dependency
RUN apt-get install -y apt-utils
RUN apt-get install -y vim git curl
RUN apt-get install -y pandoc

RUN apt-get install -y software-properties-common gnupg apt-transport-https ca-certificates
RUN apt-get install -y gcc
RUN python -m pip install --upgrade pip

# Declaring working directory in our container and download from github
WORKDIR /home/hwc/apps/hwc-server/clients
RUN git clone https://github.com/ITMORobotics/hwc-matlab-client.git

WORKDIR /home/hwc/apps/hwc-server
COPY ./requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt

COPY ./ ./

RUN git config pull.rebase false

CMD ["/bin/bash", "-c", "git -C /home/hwc/apps/hwc-server/clients/hwc-matlab-client pull origin; uwsgi /home/hwc/apps/hwc-server/hwc_server.ini"]

# # Expose ports
EXPOSE 5050
