for host in $(qhost | tail -n +4 | cut -d " " -f 1);
   do qsub -l hostname=$host -wd /home/data/logs /home/data/cluster/sge/run_registry.sh;
done
