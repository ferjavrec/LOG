#!/usr/bin/python3
# DVSwitch All Mode Last Heard Status Monitoring Host by DS5QDR Lee, Heonmin
# DSTAR, YSF Module by DS5QDR 2021.08.26
# DMR TG Status Monitoring by VK2CYO  Chanyeol Yoo
# 2021.09.03.

import asyncio
import re
import websockets
import os
import sys
import platform
import requests
import threading
import paramiko
import select
import socket
import _thread
from   tkinter           import *
from   websockets.client import connect  
from   websockets.server import serve
from   re                import I, T
from   time              import time, sleep, localtime, strftime, gmtime
from   datetime          import date, datetime, timedelta

VERSION      = 'V1.33'
NUM_HISTORY  = 8                # NUMBER OF HISTORY FOR EACH TALKGROUP
TIMEOUT      = 3600*24          # TIMEOUT FOR INACTIVE CALLS
# LH_INI       = './lh.ini'
LH_INI       = './lh_host.ini'

restart_cnt  = 0
tgs          = []
tgs_kor      = []
tgs_wld      = []
tgs_new      = []
ADDR_CNCT    = {}
DMR_STATUS   = {}
get_log_ok   = False
tgs_updated  = False  

def date_time() : 
    return strftime("%Y-%m-%d %H:%M:%S", localtime(time()))

def stamp2time(stamp) :
    return strftime("%Y-%m-%d %H:%M:%S", localtime(stamp) )

def elapsed_time(addr_time) :
    elapsed = int(time()) - addr_time
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return "{:0>2}:{:0>2}:{:0>2.0f}".format(int(hours),int(minutes),seconds)

def utc2local(utc_datetime):
    rtn_date = rtn_time = ''
    try :        
        time_1   = datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S') 
        now_timestamp = time()
        offset   = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
        time_2   = time_1 + offset
        rtn_date = time_2.strftime('%Y-%m-%d')
        rtn_time = time_2.strftime('%H:%M:%S')
    except : pass #beep(1, '--- utc2local error') ; time_2 = utc_datetime
    return rtn_date, rtn_time

def datetime2stamp(date_time) :
    date = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
    timestamp = str(int(datetime.timestamp(date)))
    return timestamp    

def sec2hms(sec) : 
    HH, MM  = divmod(sec, 3600)
    MM, SS  = divmod(MM, 60)
    new_HMS = str(HH).rjust(2,'0') + ':' + str(MM).rjust(2,'0') + ':' + str(SS).rjust(2,'0')
    if new_HMS[:2] == '-1' : new_HMS == '00:00:00'
    return new_HMS

YSFs          = []
URLs          = []
LOG_tgs       = {}
added_tg_info = ''
def read_server_info() : 
    global LOG_tgs, tgs, tgs_kor, tgs_wld
    global added_tg_info
    global DMR_STATUS
    if checkFile(LH_INI) :       
        with open(LH_INI, mode='r+') as open_file :    
            lines = open_file.readlines()
            open_file.seek(0)
            for line in lines : 
                if 'tgs_kor' in line :
                    tgs_str_cl = line.replace('tgs_kor=[', '').replace(']', '')
                    tgs_str_tm = tgs_str_cl.split(',')
                    for tg in tgs_str_tm : 
                        if tg.strip() == '' : continue
                        tgs_kor.append(tg.strip())
                    tgs_kor.sort()                                 # 새로운 값으로 sort
                elif 'tgs_wld' in line :
                    tgs_str_cl = line.replace('tgs_wld=[', '').replace(']', '')
                    tgs_str_tm = tgs_str_cl.split(',')
                    for tg in tgs_str_tm : 
                        if tg.strip() == '' : continue
                        tgs_wld.append(tg.strip())
                    tgs_wld.sort()                                 # 새로운 값으로 sort
                elif 'tgs_new' in line :
                    tgs_str_cl = line.replace('tgs_new=[', '').replace(']', '')
                    tgs_str_tm = tgs_str_cl.split(',')
                    for tg in tgs_str_tm : 
                        if tg.strip() == '' : continue
                        tgs_new.append(tg.strip())
                    tgs_new.sort()  
                elif 'YSF' in line :                    
                    ysf, url = line.replace('\n','').replace('[','').replace(']','').split(',')
                    YSFs.append(ysf.strip())
                    URLs.append(url.strip())                    
                elif '|' in line :
                    added_tg_info += line.replace('\n', '') + '/'                    # added_tg_info
            tgs = tgs_kor + tgs_wld + tgs_new
            LOG_tgs = {}
            for tg in tgs :                     # tgs_kor, tgs_wld, tgs_new 의 DMR_STATUS 생성
                DMR_STATUS[tg] = {'tg': tg, 'status': 'EMPTY', 'on_air': '', 'on_time': '' ,'stdby': ''}            
    else :
        with open(LH_INI, mode='w+') as open_file : 
            open_file.seek(0)
            open_file.write('tgs_kor=[450, 45021, 45022, 45023, 45024, 45025, 45026, 45027, 45028, 45029, 45030, 45031, 45032, 45033, 45034, 45035, 45036, 45037, 45038, 45039, 45050, 45051, 45052, 45053, 45054, 45055, 4507777] \n')
            open_file.write('tgs_wld=[91, 93, 3100, 214] \n')
            open_file.write('tgs_new=[ ] \n')
            open_file.truncate() 
        read_server_info()
    return tgs

def read_lh_txt() :
    global DMR_STATUS
    global addr_list_his, ADDR_CNCT

    try : 
        with open('lh.txt') as f:
            lines = f.readlines()
            for line in lines :
                try :
                    if line.count('|') == 4 : 
                        tg, status, onair, on_time, stdby = line.split('|')
                        tg      = tg.strip()
                        stdby   = stdby.replace('\n','')               
                        on_time = on_time.ljust(10, ' ')
                        if tg not in DMR_STATUS : continue

                        print('---', tg.ljust(8,' '), status, onair.ljust(10), on_time, stdby)
                        if tg.isdigit() and stdby.strip() != '' :
                            if onair.count(':') == 2 : onair = on_time
                            DMR_STATUS[tg] = {'tg': tg, 'status': status, 'on_air': onair, 'on_time': on_time, 'stdby': stdby}
                    elif line.count('|') == 5 :
                        addr_ip, login_time, addr_city, addr_time, tgs_in, etc  = line.split(' | ')
                        addr_ip = addr_ip.replace('>>','').strip()
                        # city = addr_city.split(', ')
                        # addr_city = city[0] +', '+ city[1].ljust(20, ' ') +', '+ city[2].ljust(15, ' ')
                        ADDR_CNCT[addr_ip] = {'addr_ip': addr_ip, 'login_time': login_time,'addr_city': addr_city, 'addr_time': addr_time, 'tgs_in': tgs_in }
                        # print('---', ADDR_CNCT[addr_ip])
                except : pass
    except : print('--- no lh.txt so create it') ; pass

def checkFile(filePath):                    # 파일 유무 확인
    try:
        with open(filePath, 'r') as f : return True
    except FileNotFoundError     as e : return False
    except IOError               as e : return False 

class Monitor(threading.Thread):
    def __init__(self, tgs, timeout=TIMEOUT, num_LOG=NUM_HISTORY) :
        global LOG_tgs
        threading.Thread.__init__(self)
        self.tgs     = tgs
        self.timeout = timeout
        self.num_LOG = num_LOG
        self.LOG_tgs = LOG_tgs
        for tg in tgs :  self.LOG_tgs[int(tg)] = []
        self._flag_stop = False 

    def sort_data_by_time(self, data):
        now = time()
        data_new = []
        callsigns = set([d['SourceCall'] for d in data])
        for callsign in callsigns:
            entry = {}
            for d in data:
                if d['SourceCall'] == callsign:
                    if (len(entry) == 0) or (d['Stop'] > entry['Stop']) or (d['Stop']==0 and d['Start'] > entry['Start']):
                        entry = d
            data_new.append(entry)
        data = data_new
        data_new = []
        for d in data:
            if d['Stop'] == 0 or now-d['Stop'] < self.timeout:
                data_new.append(d)
        data_new = sorted(data_new, key=lambda k:k['Start'], reverse=True)
        data_new = data_new[0:(self.num_LOG)]
        return data_new

    def get_data_from_packet(self, str_d):
        str_d = str_d.replace('\\', '')
        str_d = str_d.replace('"{', '{')
        str_d = str_d.replace('}"', '}')
        str_d = str_d.replace('null', 'None')
        str_d = str_d[str_d.find('{'):str_d.rfind('}')+1]
        try:
            data = eval(str_d)
            return data['payload']
        except: return None
        # except Exception as e: print('get_data_from_packet(self, str_d) error : ' + e.__str__())  

    async def process(self):
        global DMR_STATUS, tgs_updated, tgs
        uri = "wss://api.brandmeister.network/lh/%7D/?EIO=3&transport=websocket"
        while True:
            try:
                async with websockets.connect(uri) as self.websocket:
                    while True :
                        if tgs_updated :    # tg 추가시 업데이트
                            self.tgs = tgs
                            self.LOG_tgs = LOG_tgs
                            tgs_updated = False
                        str_d = await self.websocket.recv()                        
                        data = self.get_data_from_packet(str_d)
                        if data==None : continue
                        if str(data['DestinationID']) in self.tgs:
                            dstID = data['DestinationID']
                            self.LOG_tgs[dstID] = self.sort_data_by_time(self.LOG_tgs[dstID] + [data])

                            now = time()
                            for tg in self.tgs:
                                text_tg     = tg
                                text_active = text_inactive = ''
                                last_heard_time = '       '
                                history_tg  = self.LOG_tgs[int(tg)]     
                                try:
                                    text_inactive = ''
                                    tg_status     = 'EMPTY' 
                                    for d in history_tg:
                                        if now - d['Stop'] < TIMEOUT:
                                            if text_inactive == '' : last_heard_time = str(d['Stop'])   ## Last Heard Time을 text_active에 전달
                                            text_inactive += d['SourceCall'].ljust(8, ' ')                                       
                                    if history_tg[0]['Stop'] == 0:
                                        text_active = history_tg[0]['SourceCall'].ljust(6, ' ')
                                        tg_status   = 'ONAIR'
                                    elif len(text_inactive) > 0:
                                        text_active = last_heard_time
                                        tg_status   = 'STDBY'
                                except Exception as e: continue # print('RESTART 1 : ' + e.__str__()) ; continue

                                if text_inactive == '' and text_active == '' : 
                                    tg_status     = DMR_STATUS[text_tg]['status' ] 
                                    text_active   = DMR_STATUS[text_tg]['on_air' ] 
                                    on_time       = DMR_STATUS[text_tg]['on_time']
                                    text_inactive = DMR_STATUS[text_tg]['stdby'  ]
                                else : on_time    = DMR_STATUS[text_tg]['on_time']
                                DMR_STATUS[text_tg] = {}
                                DMR_STATUS[text_tg]['tg'     ] = text_tg
                                DMR_STATUS[text_tg]['status' ] = tg_status
                                DMR_STATUS[text_tg]['on_air' ] = text_active
                                DMR_STATUS[text_tg]['on_time'] = on_time
                                DMR_STATUS[text_tg]['stdby'  ] = text_inactive
                        if self._flag_stop : return
            except Exception as e: pass # print('RESTART 2 : ' + e.__str__())
            sleep(1)
    def run(self) :
        self._flag_stop = False
        asyncio.run(self.process())
    def stop(self) :
        self._flag_stop = True   

def add_new_tg(tg_add, addr_ip) :
    global DMR_STATUS
    global tgs_new, tgs, LOG_tgs, tgs_updated
    global added_tg_info

    tg_add = tg_add.strip()
    DMR_STATUS[tg_add] = { 'tg': tg_add, 'status': 'EMPTY', 'on_air': '', 'on_time': '', 'stdby': ''} 
    tgs_new.append(tg_add)            # tg 는 추가되는 TG
    tgs.append(tg_add)
    LOG_tgs[int(tg_add)] = [] 

    with open(LH_INI, mode='r+') as open_file :    
        lines = open_file.readlines()
        open_file.seek(0)
        for line in lines : 
            if 'tgs_new' in line : 
                line = line.replace(']', tg_add + ', ]')
            open_file.write(line)

        addr_ip        = addr_ip.replace('192.168.0.1', '122.37.194.58')
        new_add_tg     = str(datetime.now())[:19] + ' | ' + tg_add.rjust(6, ' ') + ' | ' + ipInfo(addr_ip) + '\n'
        added_tg_info += new_add_tg + '/'               # LH : TG 시 rtn 정보 형성 
        print('--- new_add_tg :', new_add_tg)
        open_file.write(new_add_tg)                     # 추가시키는 tg_add 요청자 정보 기록함
        open_file.truncate()   
    tgs_updated = True                                  # tg 추가시 async 에서 tgs 변수 업데이트

import ipinfo
def ipInfo(addr=''):
    from urllib.request import urlopen
    from json import load    
    if addr == '' : url = 'https://ipinfo.io/json' 
    else          : url = 'https://ipinfo.io/' + addr + '/json'
    res     = urlopen(url) 
    data    = load(res)
    print('--- addr, data', addr, data)
    rtn_str = data['city'].replace('Wŏnju', 'Wonju').replace("Yangp'yŏng", 'Yangpyong').ljust(15,' ') + ', ' + data['region'].ljust(20,' ') + ', ' + data['country'] 
    return rtn_str

cnct_ip_prt   = True
last_IP_List  = last_IP_str   = ''
addr_list_now = addr_list_his = ''
addr_city_now = addr_city_his = ''
IP_City       = 'start' 
def print_addr(addr, tgs_in) :
    global ADDR_CNCT, last_IP_List, last_IP_str
    global addr_list_now, addr_list_his, cnct_ip_prt 
    global addr_city_now, addr_city_his, IP_City

    addr_ip   = addr[0].replace('192.168.0.1', IP_EXT)                    # 내부 IP --> 외부 IP로 변환
    if addr_ip not in ADDR_CNCT :
        ADDR_CNCT[addr_ip] = {'addr_ip': addr_ip, 'login_time': date_time(), 'addr_city': ipInfo(addr_ip), 'addr_time': str(int(time())), 'tgs_in': '' }    

    ADDR_CNCT[addr_ip]['addr_time' ] = str(int(time()))
    ADDR_CNCT[addr_ip]['login_time'] = date_time()
    if tgs_in not in 'LH : KOR, LH : WLD, LH : NEW, IP_INFO, LH : IP, IP_TGIN USRP:XRF' :
        ADDR_CNCT[addr_ip]['tgs_in'] = tgs_in.replace('LH : ', '')

    addr_list_now = addr_list_his = ''
    addr_city_now = addr_city_his = ''
    for ip in ADDR_CNCT : 
        time_gap = int(time()) - int(ADDR_CNCT[ip]['addr_time'] )
        if time_gap < 60 : addr_list_now += ip + ', ' ; addr_city_now += ADDR_CNCT[ip]['addr_city'] + '/ '
        else             : addr_list_his += ip + ', ' ; addr_city_his += ADDR_CNCT[ip]['addr_city'] + '/ '

    if (int(time()-3)%30 < 3 and cnct_ip_prt) or IP_City == 'start' :
        cnct_ip_prt  = False
        loc_time     = datetime.now()
        loc_DATE_HMS = loc_time.strftime("%Y-%m-%d %H:%M:%S")
        # print('--- ip_list_now', addr_list_now)
        # print('--- ip_list_his', addr_list_his)
        IP_City = ''
        sort_ADDR_CNCT()
        for ip in ADDR_CNCT :
            City_str  = '>>' if ip in addr_list_now else '  '
            City_str += ADDR_CNCT[ip]['addr_ip'].ljust(15,' ') +' | '+ ADDR_CNCT[ip]['login_time'] +' | '+ ADDR_CNCT[ip]['addr_city'] +' | '+ ADDR_CNCT[ip]['addr_time'] +' | '+ ADDR_CNCT[ip]['tgs_in'] +' | '
            IP_City  += City_str + '/ '
            print(City_str) 
        print('-----------------', len(ADDR_CNCT)) 
    elif int(time()-3)%30 > 3 : cnct_ip_prt = True

def sort_ADDR_CNCT() :
    global ADDR_CNCT
    TEMP = {}
    for ip in ADDR_CNCT :
        city = ADDR_CNCT[ip]['addr_city']
        if city.strip() == '' : continue
        order = city.split(', ')
        key = order[2] + order[1] + order[0] + ip
        TEMP[key] = ADDR_CNCT[ip]
    ADDR_CNCT = {}
    for key in sorted(TEMP) :
        ip = TEMP[key]['addr_ip']
        ADDR_CNCT[ip]= TEMP[key]

def tg_send(sock, tg_in, addr, tgs_in) :
    global added_tg_info
    global last_IP_List, last_IP_str
    global IP_City

    print_addr(addr, tgs_in)

    IP = addr[0].replace('192.168.0.1', '122.37.194.58')
    last_IP_rtn = last_IP_str + IP + ' : '
    if   tg_in == 'IP_TGIN' :                                                   # ADMIN, Elapsed
        print( IP_City.replace('/ ' , '\n') ) 
        ips_info = IP_City.split('/ ')
        tg_out = ''
        for ip_info in ips_info :
            if ip_info.strip() == '' : continue
            ip_tg = ip_info.split(' | ')
            tg_out += ip_tg[0] +' | '+ ip_tg[1] +' | '+ ip_tg[2] +' | '+ ip_tg[4].ljust(80,' ')[:80] + '\n'
            print(tg_out)
        print( tg_out )
    elif tg_in == 'IP_INFO' :                                                   # ADMIN, Version
        ips_info = IP_City.split('/ ')
        tg_out = '\nConneced IP Info\n\n'
        for ip_info in ips_info :
            tg_out += ip_info[:84] + '\n'
        print( tg_out )
    elif tg_in == 'LH : IP' :                                                   # no ADMIN, Vesion
        ip_in   = addr[0].replace('192.168.0.1', IP_EXT)
        tg_out  = '\n\nYour IP Address : ' + ip_in + '\n\n'
        addr_city = ADDR_CNCT[ip_in]['addr_city'].split(', ')
        tg_out += addr_city[0].strip() +', '+ addr_city[1].strip() +', '+ addr_city[2].strip() + '\n\n'
        tg_out += 'tgs = ' + ADDR_CNCT[ip_in]['tgs_in'] + '\n\n'
        print( tg_out )         # 접속 ip 정보 리턴
    else : tg_out = tg_status_rtn(addr, tg_in)                                  # tgs, KOR, WLD, NEW 
    
    rtn_udp(addr, tg_out)

def rtn_udp(addr, tg_out) :
    i, BUFF_SIZE = [0, 512]                                                     # tg_out을 512 byte로 잘라 보내 줌    
    while True :
        send_str = tg_out[i*BUFF_SIZE:(i+1)*BUFF_SIZE]
        rtn_str  = bytes(send_str, 'utf-8')
        sock.sendto(rtn_str, addr)
        if len(send_str) < BUFF_SIZE : break
        i += 1

usrp_xrf_ref = ''
def usrp_xrf() :                                                            # _thread : USRP가 DMR일 경우 XRF071C LH 보내 줌
    global USRP_XRF_REF, usrp_xrf_ref
    
    while True :     
        usrp_xrf_ref = ''
        del_keys = [] 
        for key in USRP_XRF_REF :
            on_time = USRP_XRF_REF[key]['on_time']
            if int(time()) - on_time > 60 : del_keys.append(key)
            else                          : usrp_xrf_ref += stamp2time(on_time) + key[8:] + '|' + str(on_time) + '/'
        for del_key in del_keys : del USRP_XRF_REF[del_key]
        print('--- usrp_xrf_ref :\n', usrp_xrf_ref.replace('/', '\n'))
        sleep(2)

# 11:25:00|DS4ERW|XRF071C|CQ|1630980790
# 11:25:00|DS4CZS|XRF071C|CQ|1630980811
# 012345678


ref_cal   = 0
xrf_cal   = 660       # 보정값 
xrf_alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ref_alpha = 'ABCDE'
for key in xrf_alpha : DMR_STATUS['XRF071' + key] = {'tg': 'XRF071' + key, 'status': 'EMPTY', 'on_air' : '', 'on_time': '', 'stdby': ''}
for key in ref_alpha : DMR_STATUS['REF082' + key] = {'tg': 'REF082' + key, 'status': 'EMPTY', 'on_air' : '', 'on_time': '', 'stdby': ''}

USRP_XRF_REF = {}
def xrf_lh() :                                              ## XRF Last_Heard Module
    global xrf_cal, USRP_XRF_REF
    URL = 'http://xlx.elechomebrew.com/db2/index.php'
    while True : 
        try :
            XRF = {}
            r0 = requests.get(URL)
            r1 = str((r0.content).decode('utf-8'))
            r2 = r1.replace('<tr>', '').replace('</tr>', '').replace('<td>', '').replace('</td>', '').replace('\"','').replace('</a>', '').replace('</td>', '').replace('\n', '')
            r3 = r2.split('<tr class=table-center>')
            for str_1 in reversed(r3) :
                if '</table>   </div>   <div class=col-md-3>' in str_1 : continue
                try : 
                    if 'src=./img/sat.png alt=>' not in str_1 : continue
                    str_2 = str_1.split('src=./img/sat.png alt=>')
                    str_3 = str_2[1].split('  ')
                    str_4 = str_3[1] + str_3[3] + str_3[4] + str_3[5]
                    blank, call, date_str, time_str, key = str_4.split(' ')     
                    try :
                        x1    = str_2[0].find('/db/')
                        x2    = str_2[0].find(' class', x1)
                        call  = str_2[0][x1+4:x2]
                    except : pass

                    date_time_str = date_str[6:]+'-'+date_str[3:5]+'-'+date_str[:2]   + ' ' + time_str+':00'    
                    date_time = int(datetime2stamp(date_time_str))

                    call      = call.strip().ljust(8,' ') 
                    key       = 'XRF071' + key

                    if key == 'XRF071C' and int(time() - date_time + xrf_cal) < 60 :  # USRP mode가 DMR 일경우 XRF071C CQ 정보 보내줌
                        usrp_key = time_str +':00|' + call.strip() + '|XRF071C|CQ'
                        if usrp_key not in USRP_XRF_REF :
                            USRP_XRF_REF[usrp_key] = {'key': usrp_key, 'on_time': int(time())}  

                    try    : stdby = (call +        XRF[key]['stdby'].replace(call, ''))[:8*8]
                    except : stdby = (call + DMR_STATUS[key]['stdby'].replace(call, ''))[:8*8]

                    if stdby.strip() != '' : status = 'STDBY'
                    try :
                        sec    = int(time()) - date_time + xrf_cal
                        if sec < 0 : sec = 0
                        onair  = sec2hms(sec)
                        ontime = str(int(date_time - xrf_cal))
                    except Exception as e: print('--- __name__ error ' + e.__str__()) ; onair = ''

                    if 'tx.gif' in str_1 or (int(time())-int(ontime))<15 : 
                        status  = 'ONAIR' 
                        onair   = call
                        stdby   = stdby.replace(call, '')

                    XRF[key] = {'tg': key, 'status': status, 'on_air': onair, 'on_time': ontime, 'stdby': stdby}                
                except Exception as e: print('--- xrf_lh : __name__ error ' + e.__str__(), key)       
            for key in XRF :
                if XRF[key]['stdby'] != '' and XRF[key]['status'] != 'EMPTY' :
                    DMR_STATUS[key] = XRF[key]

        except Exception as e: print('--- XRF _lh __name__ error ' + e.__str__())
        sleep(2)

def ref_lh() :                                              ## REF Last_Heard Module
    global ref_cal
    URL = 'http://ref082.dstargateway.org'
    
    while True : 
        try :
            REF = {}
            r0 = requests.get(URL)
            r1 = str((r0.content).decode('utf-8'))
            r2 = r1.split('<th width="108" align="center" valign="middle"><span class="style1">Time</span><br /></th>')
            r3 = r2[1].split('<tr bgcolor="#D3DCE6">')
            for lh in reversed(r3) :
                try :
                    lh = lh.replace('\n', '').replace('   ', '')
                    if '<strong>' in lh :
                        x1 = lh.find('<strong>')
                        x2 = lh.find('</strong><', x1)
                        call = lh[x1+8:x2].strip()
                    else :
                        x1 = lh.find('<td width="95" valign="middle"><span class="style1">')
                        x2 = lh.find('</span></td>', x1)
                        call = lh[x1+52:x2].strip()
                    if ' ' in call : call = call[:call.find(' ')]

                    if call.strip() == '' : continue
                    x3 = lh.find('<td width="63" align="center" valign="middle"><span class="style1">')
                    x4 = lh.find('</span></td>', x3)
                    ch = 'REF082' + lh[x3+67:x4]
                    x5 = lh.find('<td width="108" align="center" valign="middle"><span class="style1">')
                    x6 = lh.find('</span><br',x5)
                    tm = lh[x5+68:x6].replace('/', '-')

                    date_time_str = tm
                    key           = ch   
                    date_time     = int(datetime2stamp(date_time_str))
                    call          = call.strip().ljust(8,' ') 

                    if key == 'REF082C' and int(time() - date_time + xrf_cal) < 60 :  # USRP mode가 DMR 일경우 REF082C CQ 정보 보내줌
                        usrp_key = tm +'|' + call.strip() + '|REF082C|CQ'
                        if usrp_key not in USRP_XRF_REF :
                            USRP_XRF_REF[usrp_key] = {'key': usrp_key, 'on_time': int(time())}  

                    try    : stdby = (call +         REF[key]['stdby'].replace(call, ''))[:8*8]
                    except : stdby = (call + DMR_STATUS[key]['stdby'] .replace(call, ''))[:8*8]

                    if stdby.strip() != '' : status = 'STDBY'
                    try :
                        sec    = int(time()) - date_time + ref_cal
                        onair  = sec2hms(sec)
                        ontime = str(date_time + ref_cal)                    
                    except Exception as e: print('--- __name__ error ' + e.__str__()) ; onair = ''

                    if sec < 60 : 
                        status = 'ONAIR' 
                        onair  = call
                        stdby  = stdby.replace(call, '')

                    REF[key] = {'tg': key, 'status': status, 'on_air': onair, 'on_time': ontime, 'stdby': stdby}
                except Exception as e: print('--- ref_lh : __name__ error ' + e.__str__())
            for key in REF :
                if REF[key]['stdby'] != '' and REF[key]['status'] != 'EMPTY' :
                    DMR_STATUS[key] = REF[key]
        except Exception as e: print('--- ref _lh __name__ error ' + e.__str__())
        sleep(2)

def ysf_lh(URL, YSF) :                                              ## REF Last_Heard Module
    while True : 
        try : 
            r0 = requests.get(URL)
            r1 = str((r0.content).decode('utf-8'))
            r2 = r1.split('<table id="oldallHeard" class="table table-condensed">')
            r3 = r2[1].split('$(document).ready(function(){')
            r4 = r3[0][r3[0].find('<tbody>')+7:r3[0].find('</tbody>')]
            r4 = r4.replace('<tr>', '').replace('</tr>', '').replace('<td>', ' ').replace('</td>', ' ').replace('<td nowrap>', '')
            r4 = r4.replace('/', ' ').replace('\n', '').replace('2021', '/2021')
            r5 = r4.split('/')

            for lh in reversed(r5) :
                if lh.strip() == '' or '*****' in lh or 'UNLINK' in lh or 'NOCALL' in lh  : continue
                key           = YSF        
                date_time_str = lh[:19]
                call          = lh[20:27].replace('-','').strip().ljust(8, ' ') 

                if date_time_str.count('-') != 3 and date_time_str.count(':') != 2 : continue
                if ';' in call or '&' in call : continue

                date_time     = int(datetime2stamp(date_time_str))
                if time() - date_time > 3600*24*3 : continue                                   # 3일 이상 데이타는 보이지 않게 함
                stdby         = (call + DMR_STATUS[key]['stdby'].replace(call, ''))[:8*8]
                if stdby.strip() != '' : status = 'STDBY'
                try :
                    sec   = int(time()) - date_time
                    onair = sec2hms(sec)
                except Exception as e: print('--- __name__ error ' + e.__str__()) ; onair = ''

                if sec < 60 : 
                    status = 'ONAIR' 
                    onair = call
                    stdby = stdby.replace(call, '')
                DMR_STATUS[key] = {'tg': key, 'status': status, 'on_air':onair   , 'on_time': str(date_time), 'stdby': stdby}
        except  Exception as e: print('--- ysf _lh __name__ error ' + e.__str__(), YSF)
        sleep(30)

lh_txt_save = True
def tg_status_rtn(addr=['',''], tg_list=[]) :
    global tgs, LOG_tgs, tgs_updated
    global last_IP_List, lh_txt_save 
    global IP_City

    try :
        for tg in tg_list :
            if tg not in tgs and tg.strip() != '' and tg.isdigit() : add_new_tg(tg, addr[0])                ## 새로운 TG가 들어오면 lh.ini 파일에 추가하는 모듈
              
        tg_rtn_all = tg_prt_all = 'LH : '
        for tg in sorted(DMR_STATUS) : 
            if  DMR_STATUS[tg]['on_time'].strip() == '' : pass
            elif tg[:3] not in 'XRF REF YSF' and int(time()-int(DMR_STATUS[tg]['on_time'])) > 24*3600 :     ## 24시간 지나면 DMR TG 자동 리셋
                DMR_STATUS[tg] = {'tg': tg, 'status': 'EMPTY', 'on_air': '', 'on_time': '', 'stdby': ''}

            status   = DMR_STATUS[tg]['status' ]
            tg_str   = DMR_STATUS[tg]['tg'     ]
            active   = DMR_STATUS[tg]['on_air' ]   
            on_time  = DMR_STATUS[tg]['on_time'].ljust(10, ' ')
            inactive = DMR_STATUS[tg]['stdby'  ]
            if active.isdigit() : 
                on_time = active 
                active  = strftime('%H:%M:%S', gmtime(time()-int(active) ))                                 ## on_air가 숫자이면 지난 시간으로 변환하여 표시
                    
            ## /home/pi/lh.txt 기록용 문자열 저장
            tg_prt      = tg_str.ljust(9,' ') + '|' + status.ljust(8,' ') + '|' + active.ljust(8,' ') + '|' + on_time + '|' + inactive + '/'
            tg_prt_all += tg_prt

            ## LH_Client 요청 정보 tg_rtn_all 만들어 리턴
            tg_rtn     = tg_str.strip()      + '|' + status.strip() + '|' + active.strip()      + '|' +                 inactive.strip() + '/'            
            if tg_list != [] and (tg in tg_list or (tg[:3] in 'XRF REF NXDN P25 YSF' and 'EMPTY' not in tg_rtn ) ) : 
                if   tgs_in == 'LH : KOR' and 'EMPTY' not in tg_rtn and active[:3] != '24:'   : pass        ## KOR 일 경우 DMR 450* TG와 DSTAR EMPTY 아닌 정보 모두 표시
                elif tgs_in == 'LH : WLD' and tg[:3] in 'XRF REF NXDN P25 YSF'                : continue    ## WLD 일 경우 DMR tgs_wld 만 표시
                elif tgs_in == 'LH : NEW' and tg[:3] in 'XRF REF NXDN P25 YSF'                : continue    ## NEW 일 경우 DMR tgs_new 만 표시
                elif 'WLD' not in tgs_in and 'NEW' not in tgs_in                              : 
                    if   tg in 'XRF071C REF082C YSF-119 '                                     : pass        ## 기본 LH : 요청 시 DSTAR REF는 시간과 관계없이 표시
                    elif tg[:3] in 'XRF REF ' and active.find(':')==2 and active > '01:00:00' : continue    ## 기본 LH : 요청 시 DSTAR 1시간 이상 Skip
                    elif tg[:3] in 'YSF     ' and active.find(':')==2 and active > '24:00:00' : continue    ## 기본 LH : 요청 시 YSF  24시간 이상 Skip
                tg_rtn_all += tg_rtn                         
    except Exception as e: 
        print('--- tg_status_rtn error ' + e.__str__(), tg, type(tg)) 
        print('--- DMR_STATUS[tg] error', DMR_STATUS[tg])
    
    lh_txt_write(tg_prt_all)                            ## lh.txt 저장

    return tg_rtn_all

def lh_txt_write(tg_prt_all) :
    global lh_txt_save
    global addr_list_now, addr_city_his
    global IP_City

    if int(time())%30 < 3 and lh_txt_save :                                          ## 30초에 한번 lh.txt 저장
        lh_txt_save = False
        tg_prt_all =  tg_prt_all.replace('LH : ','LH : \n').replace('/','\n')
        print(tg_prt_all)                                                         #########################################################################
        with open('lh.txt', mode='w+') as open_file :
            open_file.write( tg_prt_all                      )
            open_file.write( '\nConnected ip list \n'        )
            open_file.write( 'now = ' + addr_list_now + '\n' )
            open_file.write( 'his = ' + addr_list_his + '\n' )
            open_file.write( IP_City.replace('/ ', '\n')     )
            open_file.write( date_time()              + '\n' )
            open_file.truncate()             
    elif int(time())%30 > 3 : lh_txt_save = True    


############################################################################################################
############################################################################################################
if sys.platform == 'linux' : os.system('clear')
testIP = "8.8.8.8"
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect((testIP, 0))
IP       = s.getsockname()[0]
from requests import get
IP_EXT   = get('https://api.ipify.org').text
if   IP == '192.168.0.16' : UDP_PORT = 49894
elif IP == '192.168.0.11' : UDP_PORT = 49895 
elif IP == '192.168.0.17' : UDP_PORT = 49897
else                      : UDP_PORT = 49894

print('Last Heard Status Monitoring program ' + VERSION + ' by DS5QDR  Lee, Heonmin')
print('- IP Address :'          , IP        )
print('--- UDP_PORT :'          , UDP_PORT  )
print('usrp_udp is running from', date_time())

read_server_info()      ## lh.ini 파일로 부터 tgs, DVS IP, ID, PW 읽고 DMR_STATUS 생성
read_lh_txt()       # 지난 lh.txt 읽어들임
tg_status_rtn()

monitor = Monitor(tgs)
monitor.start()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind( (IP, UDP_PORT) )
sock.settimeout(3.0)

last_tgs = tgs
str_tgs  = []
for tg in tgs : str_tgs.append(str(tg)) 

if __name__ == "__main__":
    _thread.start_new_thread( xrf_lh  , () )      
    _thread.start_new_thread( ref_lh  , () ) 
    _thread.start_new_thread( usrp_xrf, () ) # USRP mode가  DMR일 경우 DSTAR LH 보내 중

    for URL, YSF in zip(URLs, YSFs)  : 
        DMR_STATUS[YSF] = {'tg': YSF, 'status': 'EMPTY', 'on_air' : '', 'on_time': '', 'stdby': ''}
        _thread.start_new_thread( ysf_lh , (URL, YSF) )  
        
    
    last_call = ''
    while True:
        try :             
            tgs_in, addr = sock.recvfrom(1024*4)
            tgs_in       = tgs_in.decode("utf-8").replace('ALL', 'KOR')

            if   tgs_in == 'LH : KOR' : tg_in = tgs_kor           # tgs_kor 표시 + dstar 
            elif tgs_in == 'LH : WLD' : tg_in = tgs_wld           # tgs_wld 표시  
            elif tgs_in == 'LH : NEW' : tg_in = tgs_new           # tgs_new 표시
            elif tgs_in == 'IP_INFO'  : tg_in = tgs_in            #    ADMIN, Version     
            elif tgs_in == 'LH : IP'  : tg_in = tgs_in            # no ADMIN, Version                       
            elif tgs_in == 'IP_TGIN'  : tg_in = tgs_in            #    ADMIN, TGIN
            elif tgs_in == 'USRP:XRF' :                           #    USRP
                status = DMR_STATUS['XRF071C']['status']
                stdby  = DMR_STATUS['XRF071C']['stdby' ]                
                call   = DMR_STATUS['XRF071C']['on_air'] 
                call   = call if call [:2] != '00' else stdby[:8].strip() 
                if last_call != call : 
                    _thread.start_new_thread( usrp_xrf, (addr,) ) # USRP mode가  DMR일 경우 DSTAR LH 보내 중
                    last_call = call
                continue
            elif tgs_in[5:6].isdigit()     : tg_in = tgs_in.replace('LH : ','').replace(' ','').split(',')
            else : continue
            if not tgs_in[5:6].isdigit() : 
                print('--- tgs_in :', tgs_in)
            _thread.start_new_thread( tg_send, (sock, tg_in, addr, tgs_in) )   # Host Processing을 thread로 실행
        except Exception as e:             # print('--- __name__ error ' + e.__str__() ) 
            ######################################################################################## Test
            tgs_in = 'LH : 450, 45021, 45022, 45023, 45024, 45025, 45026, 45027, 45028, 45029, 91, 214' 
            tg_in  = tgs_in.replace('LH : ','').replace(' ','').split(',')
            addr   = (IP_EXT, UDP_PORT)
            _thread.start_new_thread( tg_send, (sock, tg_in, addr, tgs_in) )
            ######################################################################################## Test