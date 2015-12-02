source /root/anaconda/envs/py27/bin/activate py27
source /home/data/pre-install.sh
cd $NOTEBOOKS

ipython2 notebook --no-browser --port 8888 --ip=*
