#! /bin/bash

find data/ -name "*.txt" -exec sed -i s/[”“]/\"/g '{}' \;
find data/ -name "*.txt" -exec sed -i s/[’]/"'"/g '{}' \;
find data/ -name "*.txt" -exec sed -i s/[\`]/"'"/g '{}' \;
