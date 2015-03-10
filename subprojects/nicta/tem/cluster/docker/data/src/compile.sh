# grail
echo "/usr/local/lib" > /etc/ld.so.conf.d/nlopt.conf
/sbin/ldconfig
(cd /data/src/grail && make install)

# tree
(cd /data/src/tree && make install)

# tree.assembly
(cd /data/src/tree.assembly && make install) 
