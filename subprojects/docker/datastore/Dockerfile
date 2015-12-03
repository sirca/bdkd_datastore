FROM bdkd/anaconda:v1.0.0

MAINTAINER Lolo Fernandez "lolo.fernandez@sirca.org.au"

ADD files /tmp/files

RUN source /root/anaconda/envs/py27/bin/activate py27 ; \
    pip install /tmp/files/bdkd-datastore-0.1.7.zip ; \
    pip install /tmp/files/datastorewrapper-0.1.7.zip; \
    rm -fr /tmp/files

RUN mkdir -p /home/data/notebooks; \
    touch /home/data/pre-install.sh

ENV NOTEBOOKS /home/data/notebooks

COPY entrypoint.sh /entrypoint.sh

EXPOSE 8888

CMD ["/bin/bash","-c", "/entrypoint.sh"]
