#!/bin/csh
#$ -S /bin/sh
docker run -d -e SETTINGS_FLAVOR=s3  \
         -e AWS_BUCKET=bdkd-docker-registry  \
         -e STORAGE_PATH=/dev \
         -e AWS_KEY=AKIAJ7NT2LABYRX37AXA \
         -e AWS_SECRET=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 \
         -p 5000:5000 \
         registry
