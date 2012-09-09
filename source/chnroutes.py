#!/usr/bin/env python
#OLDGW=`netstat -nr | grep '^default' | grep -v 'ppp' | sed 's/default *\\([0-9\.]*\\) .*/\\1/'`

import re
import urllib2
import sys
import os
import argparse
import math
import textwrap


def generate_mac(metric):
    results=fetch_ip_data()
    
    upscript_header=textwrap.dedent("""\
    #!/bin/sh
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    OLDGW=`netstat -nr | grep '^default' | sed 's/default *\\([0-9\.]*\\) .*/\\1/'`

    if [ ! -e /tmp/pptp_oldgw ]; then
        echo "${OLDGW}" > /tmp/pptp_oldgw
    fi
    
    dscacheutil -flushcache
    
    """)
    
    downscript_header=textwrap.dedent("""\
    #!/bin/sh
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"
    
    if [ ! -e /tmp/pptp_oldgw ]; then
            exit 0
    fi
    
    ODLGW=`cat /tmp/pptp_oldgw`
    
    """)
    
    upfile=open('ip-up','w')
    downfile=open('ip-down','w')
    
    upfile.write(upscript_header)
    upfile.write('\n')
    downfile.write(downscript_header)
    downfile.write('\n')
    
    for ip,_,mask in results:
        upfile.write('route add %s/%s "${OLDGW}"\n'%(ip,mask))
        downfile.write('route delete %s/%s ${OLDGW}\n'%(ip,mask))
    
    downfile.write('\n\nrm /tmp/pptp_oldgw\n')
    upfile.close()
    downfile.close()

    os.chmod('ip-up', 00755)
    os.chmod('ip-down', 00755)
    
    print "For pptp on mac only, you can copy ip-up and ip-down to the /etc/ppp folder"

def fetch_ip_data():
    #fetch data from apnic
    print "Fetching data from apnic.net, it might take a few minutes, please wait..."
    url=r'http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest'
    data=urllib2.urlopen(url).read()
    
    cnregex=re.compile(r'apnic\|cn\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|a.*',re.IGNORECASE)
    cndata=cnregex.findall(data)
    
    results=[]

    for item in cndata:
        unit_items=item.split('|')
        starting_ip=unit_items[3]
        num_ip=int(unit_items[4])
        
        imask=0xffffffff^(num_ip-1)
        #convert to string
        imask=hex(imask)[2:]
        mask=[0]*4
        mask[0]=imask[0:2]
        mask[1]=imask[2:4]
        mask[2]=imask[4:6]
        mask[3]=imask[6:8]
        
        #convert str to int
        mask=[ int(i,16 ) for i in mask]
        mask="%d.%d.%d.%d"%tuple(mask)
        
        #mask in *nix format
        mask2=32-int(math.log(num_ip,2))
        
        results.append((starting_ip,mask,mask2))
         
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description="Generate routing rules for vpn.")
    parser.add_argument('-m','--metric',
                        dest='metric',
                        default=5,
                        nargs='?',
                        type=int,
                        help="Metric setting for the route rules")
    
    args = parser.parse_args()
    generate_mac(args.metric)
