# Anaconda Docker image

It contains Python 2.7 and Anaconda python libraries running on a CentOS 6

See [Dockerfile](Dockerfile)

## Build
```
docker build -t="anaconda" .
```

## Run
```
docker run -ti anaconda bash
source /root/anaconda/envs/py27/bin/activate py27
```
