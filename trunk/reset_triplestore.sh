#!/bin/bash

cd /var/lib/4store
service 4store stop
rm -Rf RRH
4s-backend-setup RRH
chown -R fourstore RRH
service 4store start