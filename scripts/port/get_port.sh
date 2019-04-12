#cat get_port.sh 
#!/bin/bash

nginx_port_SPACE=`netstat -tnlp |grep nginx| awk '{print $4}' | grep -v "::" | grep : | awk -F: '{print $2}'`
#echo +++++nginx_port_SPACE+++++
#echo "$nginx_port_SPACE"

java_port_SPACE=`netstat -tnlp |grep java| awk '{print $4}' | grep -v "::" | grep : | awk -F: '{print $2}'`
#echo +++++java_port_SPACE+++++
#echo "$java_port_SPACE"

node_port_SPACE=`netstat -tnpl|grep node |awk '{print $4}'|grep ":::"|awk -F::: '{print $2}'`
#echo +++++node_port_SPACE+++++
#echo "$node_port_SPACE"

PORTSPACE=("$nginx_port_SPACE
$java_port_SPACE
$node_port_SPACE")
#echo +++++PORTSPACE+++++
#echo "$PORTSPACE"|grep -v '^$'



COUNT=`echo "$PORTSPACE" |grep -v '^$'|wc -l`
INDEX=0
echo '{
    "data":['
    echo "$PORTSPACE" |grep -v '^$'| while read LINE; do
    echo -n '
        {
            "{#LISTEN_PORT}":"'$LINE'"
        }'
    INDEX=`expr $INDEX + 1`
    if [ $INDEX -lt $COUNT ]; then
        echo ','
    fi
done
echo '
    ]
}'

