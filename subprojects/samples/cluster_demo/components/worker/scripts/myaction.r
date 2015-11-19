#!/usr/bin/env Rscript

# Trivial sample application: write message and length to a file in the /tmp 
# directory.

# Output file name: file in /tmp
ofn <- paste('/tmp', system2('cat', args='/proc/sys/kernel/random/uuid', stdout = TRUE), sep='/')

# Read from stdin
ifh <- file('stdin')
open(ifh)
while(length(line <- readLines(ifh,n=1)) > 0) {
  writeLines(c(line, nchar(line)), ofn)
}
close(ifh)
