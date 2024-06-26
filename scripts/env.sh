#!/bin/sh

docker run -d -p 27017:27017 mongo:latest
docker run -d --network=host zookeeper:latest
docker run -d --network=host rabbitmq:latest
sleep 3

echo -n $SECRETS | base64 -d > testdata/secrets.json
