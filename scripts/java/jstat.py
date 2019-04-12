#!/usr/bin/env python
#coding=utf-8
'''
功能: 调用jstat获取JVM的各项指标
说明: 用于zabbix自动发现告警
版本: V1.0 2019-04-01
特性: 1. 线程功能，提高脚本执行速度
'''
import datetime
import time
import sys
import os
import commands
import subprocess
import json
import argparse
import socket
import threading

jstat_cmd = commands.getoutput("which jstat")
jstack_cmd = commands.getoutput("which jstack")
jvmname_cmd = "jps|grep -Ev 'Jps|JStack|Jstat|--'|awk '{print $2,$1}'"
jvmport_cmd = "netstat -tpnl|grep -oP '(?<=:)\d+.*\d+(?=/java)'|awk '{print $1,$NF}'"

hostname = socket.gethostname()
zbx_sender='/usr/bin/zabbix_sender'
zbx_cfg='/etc/zabbix/zabbix_agentd.conf'
zbx_tmp_file='/etc/zabbix/scripts/java/.zabbix_jvm_status'

'''
output=sys.stdout
outputfile=open("/etc/zabbix/scripts/java/log.txt","a")
sys.stdout=outputfile

now = time.time()
t = time.localtime(int(now))
dt = time.strftime("%Y%m%d%H%M%S", t)
print dt
'''

jvm_threads = []

def get_status(cmd,opts,pid):
    value = commands.getoutput('%s -%s %s' % (cmd,opts,pid)).strip().split('\n')

    #print value[0].split(' ')
    #print value[1].split(' ')
    #print filter(None, value[0].split(' '))
    #print filter(None, value[1].split(' '))   

    if filter(None, value[0].split(' ')):
        if filter(None, value[1].split(' ')):
	    kv = []
	    for i in filter(None, value[0].split(' ')):
		if i != '':
		    kv.append(i)
	    vv = []
	    for i in filter(None, value[1].split(' ')):
		if i != '':
		    vv.append(i)
	    data = dict(zip(kv,vv))
	    return data    
	else:
	    pass
    else:
	pass

'''	    
    kv = []
    for i in filter(None, value[0].split(' ')):
        if i != '':
            kv.append(i)

    vv = []
    for i in filter(None, value[1].split(' ')):
        if i != '':
            vv.append(i)

    data = dict(zip(kv,vv))
    return data
'''

def get_thread(cmd,pid):
    value = commands.getoutput('sudo %s %s|grep http|wc -l' % (cmd,pid))
    data = {"Thread":value}
    return data

def get_jvm(jport,jprocess):
    '''
      使用jstat获取Java的性能指标
    '''
    
    file_truncate()    # 清空zabbix_data_tmp
    
    gcutil_data = get_status(jstat_cmd,"gcutil",jprocess)
    gccapacity_data = get_status(jstat_cmd,"gccapacity",jprocess)
    gc_data = get_status(jstat_cmd,"gc",jprocess)
    thread_data = get_thread(jstack_cmd,jprocess)
    data_dict = dict(gcutil_data.items()+gccapacity_data.items()+gc_data.items()+thread_data.items())

    for jvmkey in data_dict.keys():
        zbx_data = "%s jvm[%s,%s] %s" %(hostname,jport,jvmkey,data_dict[jvmkey])
        with open(zbx_tmp_file,'a') as file_obj: file_obj.write(zbx_data + '\n')

def jvm_name_discovery():
    output = subprocess.Popen(jvmname_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    jvm_name_lists = output.stdout.readlines()
    jvm_name_proce = []
    for jvm_name_tmp in jvm_name_lists:
         jvm_name_proce.append(jvm_name_tmp.split())
    return jvm_name_proce

def jvm_port_discovery():
    output = subprocess.Popen(jvmport_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    jvm_port_lists = output.stdout.readlines()
    jvm_port_proce = []
    for jvm_port_tmp in jvm_port_lists:
         jvm_port_proce.append(jvm_port_tmp.split())
    return jvm_port_proce
    

def file_truncate():
    '''
      用于清空zabbix_sender使用的临时文件
    '''
    with open(zbx_tmp_file,'w') as fn: fn.truncate()

def zbx_tmp_file_create():
    '''
      创建zabbix_sender发送的文件内容
    '''
    jvmname_list = jvm_name_discovery()
    for jvm_name_tmp in jvmname_list:
        jvmname = jvm_name_tmp[0]
        jvmprocess = jvm_name_tmp[1]
        th = threading.Thread(target=get_jvm,args=(jvmname,jvmprocess))
        th.start()
        jvm_threads.append(th)

def send_data_zabbix():
    '''
      调用zabbix_sender命令，将收集的key和value发送至zabbix server
    '''
    zbx_tmp_file_create()
    for get_jvmdata in jvm_threads:
        get_jvmdata.join()
    zbx_sender_cmd = "%s -c %s -i %s" %(zbx_sender,zbx_cfg,zbx_tmp_file)
    now = time.time()
    t = time.localtime(int(now))
    dt = time.strftime("%Y%m%d%H%M%S", t)
    #print dt
    print zbx_sender_cmd
    zbx_sender_status,zbx_sender_result = commands.getstatusoutput(zbx_sender_cmd)
    #print zbx_sender_status
    print zbx_sender_result

def zbx_name_discovery():
    '''
      用于zabbix自动发现JVM名称
    '''
    jvm_zabbix = []
    jvmname_list = jvm_name_discovery()
    for jvm_tmp in jvmname_list:
        jvm_zabbix.append({'{#JNAME}' : jvm_tmp[0],
                           '{#JPROCESS}' : jvm_tmp[1],
                         })
    return json.dumps({'data': jvm_zabbix}, sort_keys=True, indent=7,separators=(',', ':'))

def zbx_port_discovery():
    '''
      用于zabbix自动发现JVM端口
    '''
    jvm_zabbix = []
    jvmport_list = jvm_port_discovery()
    for jvm_tmp in jvmport_list:
        jvm_zabbix.append({'{#JPORT}' : jvm_tmp[0],
                           '{#JPROCESS}' : jvm_tmp[1],
                         })
    return json.dumps({'data': jvm_zabbix}, sort_keys=True, indent=7,separators=(',', ':'))

def cmd_line_opts(arg=None):
    class ParseHelpFormat(argparse.HelpFormatter):
        def __init__(self, prog, indent_increment=5, max_help_position=50, width=200):
            super(ParseHelpFormat, self).__init__(prog, indent_increment, max_help_position, width)

    parse = argparse.ArgumentParser(description='JVM监控"',
                                    formatter_class=ParseHelpFormat)
    parse.add_argument('--version', '-v', action='version', version="1.0", help='查看版本')
    parse.add_argument('--jvmname', action='store_true', help='获取JVM名称')
    parse.add_argument('--jvmport', action='store_true', help='获取JVM端口')
    parse.add_argument('--data', action='store_true', help='发送JVM指标数据至zabbix')

    if arg:
        return parse.parse_args(arg)
    if not sys.argv[1:]:
        return parse.parse_args(['-h'])
    else:
        return parse.parse_args()


if __name__ == '__main__':
    opts = cmd_line_opts()
    if opts.jvmname:
	print zbx_name_discovery()
    elif opts.jvmport:
        print zbx_port_discovery()
    elif opts.data:
        send_data_zabbix()
    else:
        cmd_line_opts(arg=['-h'])


'''
NGCMN：新生代最小容量
NGCMX：新生代最大容量
NGC：当前新生代容量
OGCMN：老年代最小容量
OGCMX：老年代最大容量
OGC：当前老年代大小

MCMN：最小元数据容量
MCMX：最大元数据容量
MC：元数据空间大小
MU：元数据空间使用大小
M：元数据空间使用百分比

EC：Eden区大小
EU：Eden区使用大小
E：Eden区使用百分比
S0C：第一个幸存区大小
S0U：第一个幸存区使用大小
S0：第一个幸存区使用百分比
S1C：第二个幸存区大小
S1U：第二个幸存区使用大小
S1：第二个幸存区使用百分比
OC：老年代大小
OU：老年代使用大小
O：老年代使用百分比

CCSMN：最小压缩类空间大小
CCSMX：最大压缩类空间大小
CCSC：压缩类空间大小
CCSU：压缩类空间使用大小
CCS：压缩类空间使用百分比

YGCT：年轻代GC消耗时间
YGC：年轻代GC次数
FGCT：老年代GC消耗时间
FGC：老年代GC次数
GCT：GC消耗总时间
Thread：线程数
'''
