#Installs ubuntu 20.04 from Docker HubRUN apt-get update

FROM ubuntu:latest
RUN apt-get update

RUN apt-get install -y apt-utils
RUN apt-get install -y python3 python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools
RUN apt-get install -y vim 
RUN apt-get install -y git

#Declaring working directory in our container and download from github
WORKDIR /home/hwc/apps hwc-server
COPY . .
RUN pip3 install -r requirements.txt