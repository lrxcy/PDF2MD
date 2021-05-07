#!/bin/bash
sudo docker rm -f "pdf-to-md" || echo ""
ContainerID=$(sudo docker run -dit --restart='always' -e IMAGE_UPLOAD_SERVER_URL="" -e IMAGE_UPLOAD_SERVER_KEY="" --name pdf-to-md -p 9545:9454 pdf-to-md | tail -1)
echo $ContainerID
sudo docker logs -f $ContainerID
# ssudo docker run -it --name pdf-to-md -p 9545:9454 pdf-to-md