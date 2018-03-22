#!/bin/sh

i=1
while [ $i -le 100 ]; do
    echo "Migrating $i"
    i=$((i+1))
done
