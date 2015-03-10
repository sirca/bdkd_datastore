source /root/virtualenvs/py2.7/bin/activate

# Parallel as many processors
nproc=$(cat /proc/cpuinfo | awk '/^processor/{print $3}' | tail -1)
i=0
while [  $i -le $nproc ]; do
  (cd /home/data/src/tree.assembly/scripts/ && nohup python simulate_worker.py&)
  let i=i+1
done

# Run in foreground to keep hold container alive
(cd /home/data/src/tree.assembly/scripts/ && python simulate_worker.py)
