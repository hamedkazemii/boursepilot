#!/bin/bash


URL="http://localhost:8080/api/v1/health"


STATUS=$(curl -s $URL)


if [[ -z "$STATUS" ]]

then

echo "Sandoghchi DOWN"

exit 1


else

echo "Sandoghchi OK"

fi

