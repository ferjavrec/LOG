#!/usr/bin/python3
# DVSwitch All Five Mode Log Status by DS5QDR Lee, Heonmin
# DMR TG Status Monitoring by VK2CYO  Chanyeol Yoo
# 2021.06.22.

import os
import requests
import paramiko
import select
import threading
import pysftp
import subprocess 
import base64
import asyncio
import websockets
import webbrowser
import winsound
import tkinter
import tkinter.font as tkfont
import tkinter      as tk
from   tkinter      import *
from   tkinter      import ttk
from   tkinter      import font
from   tkinter      import messagebox
from   time         import time, sleep, localtime, strftime, gmtime
from   datetime     import date, datetime, timedelta
from   ping3        import ping, verbose_ping

os.system('cls')
####################################################
GR12       = 'gray12'
GR18       = 'gray18'
GR25       = 'gray25'
GRAY       = 'gray'
WHIT       = 'white'
REDD       = 'red'
YLOW       = 'yellow'
BLUE       = 'blue'
AQUA       = 'aqua'
LTBL       = 'light blue'
GOLD       = 'gold'
BLCK       = 'black'
H11        = 'Arial 11'         #'Helvetica 11'
H11B       = 'Arial 11 bold'    #Helvetica 11 bold'
####################################################

VERSION    = 'V1.56'
IS_TEST    = False
start_time = st_time = last_update = time()
last_today = ""
tg_DST = tg_NXD = tg_P25 = tg_YSF = ''

###########################################################################################
NUM_HISTORY = 8
TIMEOUT     = 3600*24
disp_line   = 5
tgs         = [] #[450, 45021, 45022, 45023, 45024, 45025, 45026, 45027, 45028, 45029, 91, 3100, 214]
IP          = '192.168.0.160'
ID = PW     = 'dvswitch'
ip_id_pw    = 'ip=192.168.0.160 | id=dvswitch | pw=dvswitch'
ip_chk_ok   = False
get_log_ok  = True
last_ip_chk = True
ping_chk    = 'NG'
down_log    = True 
last_time   = time()
###########################################################################################

LOG          = {}
LOG['DMR'  ] = {}
LOG['DSTAR'] = {}
LOG['NXDN' ] = {}
LOG['YSF'  ] = {}
LOG['P25'  ] = {}
DMR_STATUS   = {}
for mode in ('DMR', 'DSTAR', 'NXDN', 'P25', 'YSF') :
    i = 0 ; w = 15
    while i < disp_line :
        LOG[mode][i] = [''.ljust(w,' '), ''.ljust(w,' '), ''.ljust(w,' '), ''.ljust(w,' ')]
        i += 1

def version_from_github(url, key) :    
    req = requests.get(url)
    try : 
        if req.status_code == requests.codes.ok:
            req = req.json() 
            content = base64.b64decode(req['content'])
            rtn_str = content.decode("utf-8")
        else : print('Content was not found.') ; return ''
    except : beep(1, '--- version from github error') ; pass    

    LOG    = ['LOG  for Windows', ':']
    USRP   = ['USRP for RPi    ', ':']
    if key == 'LOG' :
        x1 = rtn_str.find(LOG[0]) + len(LOG[0])
        x2 = rtn_str.find(LOG[1], x1)
        version = rtn_str[x1:x2].strip()
    print(rtn_str)
    print(version)
    return version

url = 'https://api.github.com/repos/ds5qdr/upgrade_files/contents/check_upgrade.txt'
GITHUB = version_from_github(url, 'LOG')  

class CnOpts(object):   # pylint:disable=r0903              2021.04.30. 22:17
    def __init__(self, knownhosts=None):
        self.log = False
        self.compression = False
        self.ciphers     = None
        if knownhosts is None : knownhosts = known_hosts()
        self.hostkeys = paramiko.hostkeys.HostKeys()
        try : self.hostkeys.load(knownhosts)
        except IOError : pass
        else           : pass
## https://stackoverflow.com/questions/56521549/failed-to-load-hostkeys-warning-while-connecting-to-sftp-server-with-pysftp

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None  

def beep(time, msg=None):
    winsound.Beep(1500, int(time*1000))
    print('---- msg', msg)

def elapsed_time() :
    global start_time
    elapsed = time() - start_time
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return "{:0>2}:{:0>2}:{:0>2.0f}".format(int(hours),int(minutes),seconds)

def log_stack(mode, call, tg, date, time) :  
    global LOG
    call = call.replace(' ','').ljust(7,' ')[:7]
    tg   =   tg.replace(' ','').ljust(7,' ')[:7]
    if call == LOG[mode][0][0] : LOG[mode][0]   = [call, tg, date, time] ; return   # 같은 Callsign 일 경우 시간만 바꿈
    for i in range(4, -1, -1)  : LOG[mode][i+1] = LOG[mode][i]
    LOG[mode][0] = [call, tg, date, time]

def utc2local(utc_datetime):
    rtn_date = rtn_time = ''
    try :        
        time_1   = datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S') 
        now_timestamp = time()
        offset   = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
        time_2   = time_1 + offset
        rtn_date = time_2.strftime('%Y-%m-%d')
        rtn_time = time_2.strftime('%H:%M:%S')
    except : beep(1, '--- utc2local error') ; time_2 = utc_datetime
    return rtn_date, rtn_time

def checkFile(filePath):                    # 파일 유무 확인
    try:
        with open(filePath, 'r') as f : return True
    except FileNotFoundError     as e : return False
    except IOError               as e : return False 

def ip_check(IP) :
    global ping_chk, ip_chk_ok
    OS_IS = 'WIN'
    if OS_IS == "WIN" : ping_chk = ping(IP)
    else              : ping_chk = subprocess.call(["ping", IP, "-c1", "-W2", "-q"], stdout=open(os.devnull,'w'))
    if ping_chk == 1 or ping_chk == None : ip_chk_ok = False ; ping_chk = 'NG'
    else                                 : ip_chk_ok = True  ; ping_chk = 'OK'
    return ip_chk_ok

def log_file_name(key) :
    now_time = datetime.today().strftime('%H')
    if int(now_time) < 9 :                                                      # UTC Local 전환 시 파일 명 변경
        today        = (date.today() - timedelta(1)).strftime('%Y-%m-%d')
        yesterday    = (date.today() - timedelta(2)).strftime('%Y-%m-%d')
    else :
        today        = (date.today()               ).strftime('%Y-%m-%d')
        yesterday    = (date.today() - timedelta(1)).strftime('%Y-%m-%d')   
    if key == 'yesterday' : file_name = '/var/log/mmdvm/MMDVM_Bridge-' + yesterday + '.log'
    elif key == 'today'   : file_name = '/var/log/mmdvm/MMDVM_Bridge-' + today     + '.log'
    return file_name

def get_log(IP, ID, PW, file_name) : 
    global get_log_ok
    try :
        with pysftp.Connection(host=IP, username=ID, password=PW, port=22, cnopts = cnopts ) as sftp :
            sftp.get(file_name, 'log.txt')
        sftp.close() 
        get_log_ok = True
    except : beep(1, '--- get_log error') ; get_log_ok = False
    # print('--- get_log_ok ', get_log_ok)
    return get_log_ok

def read_log() :
    try :
        with open('log.txt',  mode='r', encoding='windows-1252') as open_file :      
            lines = open_file.readlines()
    except : beep(1, '--- read_log error') ; lines = {} ; pass
    return lines

def read_server_info() : 
    global LOG_tgs, tgs, IP, ID, PW, ip_chk_ok
    if checkFile('./log.ini') :       
        with open('./log.ini', mode='r') as open_file :    
            lines = open_file.readlines()
            open_file.seek(0)
            for line in lines :
                if 'tgs' in line :
                    tgs_str_cl = line[line.find('[')+1:line.find(']')]
                    tgs_str_tm = tgs_str_cl.split(',')
                    tgs = []
                    for tg in tgs_str_tm : tgs.append(int(tg))   
                    LOG_tgs = {}
                    for tg in tgs : LOG_tgs[tg] = []  
                elif 'ip=' in line : 
                    IP_ID_PW  = line.split('|')
                    IP = IP_ID_PW[0][IP_ID_PW[0].find('ip=')+3:].strip()
                    ID = IP_ID_PW[1][IP_ID_PW[1].find('id=')+3:].strip()
                    PW = IP_ID_PW[2][IP_ID_PW[2].find('pw=')+3:].strip()
                    # ip_chk_ok = False
    else :
        with open('./log.ini', mode='w+') as open_file : 
            open_file.seek(0)
            open_file.write('tgs=[450, 45021, 45022, 45023, 45024, 45025, 45026, 45027, 45028, 45029, 91, 3100, 214] \n')
            open_file.write('ip=192.168.0.160 | id=dvswitch | pw=dvswitch \n')
        sleep(1)
        read_server_info()
    return tgs, IP, ID, PW

def stack_LOG(line) : 
    global tg_DST, tg_NXD, tg_P25, tg_YSF 
    line_1 = line[ 3:22]
    line_2 = line[27:line.find(',')].replace('DMR Slot 2', 'DMR').replace('D-Star', 'DSTAR')
    line_3 = line[line.find(',')+1:line.find('\n')]
    
    call = ''    
    mode = line_2    
    str_date, str_time = utc2local(line_1)    
    if 'from' in line_3 and 'to' in line_3 :
        if   mode in 'DMR NXDN P25' :
            call = line_3[line_3.find('from')+5:line_3.find('to')].strip()
            tg   = line_3[line_3.find('TG')    :                 ].strip()
        elif mode == 'DSTAR' and 'CQCQCQ' in line_3 : 
            call = line_3[line_3.find('from')+5:line_3.find('/') ].strip()
            if 'via' in line_3 : 
                tg_DST = line_3[line_3.find('via')+3 :           ].strip()
                print('===============', line_3)
            tg = tg_DST
        elif mode == 'YSF'         : 
            call = line_3[line_3.find('from')+5:line_3.find('to')].strip().replace('-RPT','')
            tg = tg_YSF
        if call != '' : log_stack(mode, call.ljust(8,' '), tg, str_date, str_time)              
    elif 'YSF' in line and 'tgs=' in line :         #   YSF, Remote CMD: tgs=74652
        tg_YSF = line[line.find('tgs=')+4:].strip().replace('74652', '119-YSF').replace('32642', '021-YSF').replace('37865', 'YCS450').replace('62432', 'C4DS5QDR').ljust(8,' ')
  
def down_log_stack() :   
    global st_time, ip_chk_ok, tgs, IP, ID, PW
    st_time   = time()    
    if tgs == [] or (not ip_chk_ok) :                           ##### log.ini 파일 읽기 
        tgs, IP, ID, PW = read_server_info()                         
    if ip_chk_ok :       
        now_time = datetime.today().strftime('%H')
        if int(now_time) < 18 : yest_today = ['yesterday', 'today']
        else                  : yest_today = ['today']
        for key in yest_today :                                 ##### Read Log File  
            file_name = log_file_name(key)
            if get_log(IP, ID, PW, file_name) :                 # MMDVM_Bridge-data.log 파일 다운로드
                lines = read_log()                              # 다운로드 파일을  lines 변수에 할당
                for line in lines : stack_LOG(line)             # lines 내용을 stack
            
######################################################################################
class Monitor(threading.Thread):
    def __init__(self, tgs, timeout=TIMEOUT, num_LOG=NUM_HISTORY) :
        global LOG_tgs        
        threading.Thread.__init__(self)
        self.tgs = tgs
        self.timeout = timeout
        self.num_LOG = num_LOG
        self.LOG_tgs = LOG_tgs
        for tg in tgs :  self.LOG_tgs[tg] = []
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

    async def process(self):
        global DMR_STATUS
        uri = "wss://api.brandmeister.network/lh/%7D/?EIO=3&transport=websocket"
        while True:
            try:
                async with websockets.connect(uri) as self.websocket:
                    while True:
                        str_d = await self.websocket.recv()                        
                        data = self.get_data_from_packet(str_d)
                        if data==None : continue
                        if data['DestinationID'] in self.tgs:
                            dstID = data['DestinationID']
                            self.LOG_tgs[dstID] = self.sort_data_by_time(self.LOG_tgs[dstID] + [data])

                            now = time()
                            for tg in self.tgs:
                                text_tg     = tg
                                text_active = text_inactive = ''
                                last_heard_time = '       '
                                history_tg  = self.LOG_tgs[tg]     
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
                                except Exception as e: pass # print('RESTART 1 : ' + e.__str__())
                                DMR_STATUS[tg] = {}
                                DMR_STATUS[tg]['status'] = tg_status
                                DMR_STATUS[tg]['tg'    ] = text_tg
                                DMR_STATUS[tg]['on_air'] = text_active
                                DMR_STATUS[tg]['stdby' ] = text_inactive
                        if self._flag_stop : return
            except Exception as e:  pass #print('RESTART 2 : ' + e.__str__()) 

    def run(self) :
        self._flag_stop = False
        asyncio.run(self.process())        
    def stop(self) :
        self._flag_stop = True      

############################################################################################################
def makeTextFrame(root) :
    global Five, IP, ID, PW, ping_chk
    global dmr_cl, dmr_tm, dmr_tg, dst_cl, dst_tm, dst_tg, nxd_cl, nxd_tm, nxd_tg, p25_cl, p25_tm, p25_tg, ysf_cl, ysf_tm, ysf_tg
    global ip_addrs, id_psswd, ping_tst, lgin_tst, mssg_dsp, ping_tst_str, lgin_tst_str, mssg_dsp_str

    dmr_cl = StringVar('') ; dmr_tm = StringVar('') ; dmr_tg = StringVar('')
    dst_cl = StringVar('') ; dst_tm = StringVar('') ; dst_tg = StringVar('')
    nxd_cl = StringVar('') ; nxd_tm = StringVar('') ; nxd_tg = StringVar('')
    p25_cl = StringVar('') ; p25_tm = StringVar('') ; p25_tg = StringVar('')
    ysf_cl = StringVar('') ; ysf_tm = StringVar('') ; ysf_tg = StringVar('')

    text_str = 'Five Mode Log Status '+VERSION+' by DS5QDR Lee, Heonmin (C) 2021-2022'
    Five = LabelFrame(root, text=text_str, width=600, font=H11, padx=5, fg=WHIT, bg=GR12, relief=SUNKEN)

    Label(Five, text='DMR'                  , fg=GOLD, bg=GR12, font=H11B).grid(row=1, column= 1, sticky=(W))    
    Label(Five, textvariable=dmr_tg         , fg=GOLD, bg=GR12, font=H11B).grid(row=1, column= 2, sticky=(E))
    Label(Five, textvariable=dmr_cl, width=7, fg=GOLD, bg=GR12, font=H11 ).grid(row=2, column= 1, sticky=(E), rowspan=5)
    Label(Five, textvariable=dmr_tm         , fg=GOLD, bg=GR12, font=H11 ).grid(row=2, column= 2, sticky=(E), rowspan=5)

    Label(Five, text='DSTAR'                , fg=WHIT, bg=GR12, font=H11B).grid(row=1, column= 3, sticky=(W))    
    Label(Five, textvariable=dst_tg         , fg=WHIT, bg=GR12, font=H11B).grid(row=1, column= 4, sticky=(E))
    Label(Five, textvariable=dst_cl, width=7, fg=WHIT, bg=GR12, font=H11 ).grid(row=2, column= 3, sticky=(E), rowspan=5)
    Label(Five, textvariable=dst_tm         , fg=WHIT, bg=GR12, font=H11 ).grid(row=2, column= 4, sticky=(E), rowspan=5)

    Label(Five, text='NXDN'                 , fg=GOLD, bg=GR12, font=H11B).grid(row=1, column= 5, sticky=(W))    
    Label(Five, textvariable=nxd_tg         , fg=GOLD, bg=GR12, font=H11B).grid(row=1, column= 6, sticky=(E))
    Label(Five, textvariable=nxd_cl, width=7, fg=GOLD, bg=GR12, font=H11 ).grid(row=2, column= 5, sticky=(E), rowspan=5)
    Label(Five, textvariable=nxd_tm         , fg=GOLD, bg=GR12, font=H11 ).grid(row=2, column= 6, sticky=(E), rowspan=5)

    Label(Five, text='P25'                  , fg=WHIT, bg=GR12, font=H11B).grid(row=1, column= 7, sticky=(W))    
    Label(Five, textvariable=p25_tg         , fg=WHIT, bg=GR12, font=H11B).grid(row=1, column= 8, sticky=(E))
    Label(Five, textvariable=p25_cl, width=7, fg=WHIT, bg=GR12, font=H11 ).grid(row=2, column= 7, sticky=(E), rowspan=5)
    Label(Five, textvariable=p25_tm         , fg=WHIT, bg=GR12, font=H11 ).grid(row=2, column= 8, sticky=(E), rowspan=5)

    Label(Five, text='YSF'                  , fg=GOLD, bg=GR12, font=H11B).grid(row=1, column= 9, sticky=(W))    
    Label(Five, textvariable=ysf_tg         , fg=GOLD, bg=GR12, font=H11B).grid(row=1, column=10, sticky=(E))
    Label(Five, textvariable=ysf_cl, width=7, fg=GOLD, bg=GR12, font=H11 ).grid(row=2, column= 9, sticky=(E), rowspan=5)
    Label(Five, textvariable=ysf_tm         , fg=GOLD, bg=GR12, font=H11 ).grid(row=2, column=10, sticky=(E), rowspan=5)
    
    ping_tst_str = StringVar('')           # ip_addrs
    lgin_tst_str = StringVar('')           # lgin_tst
    mssg_dsp_str = StringVar('')           # mssg_dsp
    idpw = 'id='+ID+'   pw='+PW
    dvs_info = Label(Five, text='DVS info'            , fg=AQUA, bg=GR12, font=H11 ) # 01234567890123456
    ip_addrs = Label(Five, text='ip='+IP.ljust(16,' '), fg=AQUA, bg=GR12, font=H11 ) # ip=192.168.0.110+
    id_psswd = Label(Five, text=idpw.ljust(    32,' '), fg=AQUA, bg=GR12, font=H11 )
    ping_tst = Label(Five, textvariable=ping_tst_str  , fg=AQUA, bg=GR12, font=H11 )
    lgin_tst = Label(Five, textvariable=lgin_tst_str  , fg=AQUA, bg=GR12, font=H11 )
    mssg_dsp = Label(Five, textvariable=mssg_dsp_str  , fg=AQUA, bg=GR12, font=H11 )
    dvs_info.grid(row=8, column=1, sticky=(W), padx=2, columnspan=1)
    ip_addrs.grid(row=8, column=2, sticky=(W), padx=2, columnspan=2)
    id_psswd.grid(row=8, column=4, sticky=(W), padx=2, columnspan=3)
    ping_tst.grid(row=8, column=7, sticky=(W), padx=2, columnspan=1)
    lgin_tst.grid(row=8, column=8, sticky=(W), padx=2, columnspan=1)
    mssg_dsp.grid(row=8, column=9, sticky=(W), padx=2, columnspan=2)
    mssg_dsp.bind("<Button-1>", lambda e : webbrowser.open_new("https://github.com/ds5qdr/LOG"))

    ip_check(IP)
    disp_0()    
    DVS_cnt_info()                                  # Five Mode Log 마지막 IP, ID, PW, ping, Log, New Version 표시
    return Five

def DVS_cnt_info() :
    global Five, IP, ID, PW, ping_chk
    global ip_chk_ok, get_log_ok
    global ip_addrs, id_psswd, ping_tst, lgin_tst, mssg_dsp, ping_tst_str, lgin_tst_str, mssg_dsp_str

    # print('----- ip_chk_ok, get_log_ok', ip_chk_ok, get_log_ok)

    if   ip_chk_ok and     get_log_ok : ip, log = ['OK', 'OK']
    elif ip_chk_ok and not get_log_ok : ip, log = ['OK', 'NG']
    else                              : ip, log = ['NG', 'NG'] ; get_log_ok = False
    
    # ipidpw  = 'DVS Info : ip =' + IP + '   id=' + ID + '   pw=' + PW 
    ping_test = 'ping  '     + ip 
    log_ok    = 'login '     + log
    github    = 'new '       + GITHUB + ' available'           # Download V1.55
    blank     = ' elapsed  ' + elapsed_time()                  # 0123456789012345                    
    log_ng    = 'disconnected'
    chk_ini   = ' check  log.ini  file '
    if ip_chk_ok  : ip_addrs.configure(fg=AQUA, bg=GR12) ; ping_tst.configure(fg=AQUA, bg=GR12)
    else          : ip_addrs.configure(fg=WHIT, bg=REDD) ; ping_tst.configure(fg=WHIT, bg=REDD) 
    ping_tst_str.set(ping_test)

    if get_log_ok : id_psswd.configure(fg=AQUA, bg=GR12) ; lgin_tst.configure(fg=AQUA, bg=GR12) ; mssg_dsp.configure(fg=AQUA, bg=GR12) 
    else          : id_psswd.configure(fg=WHIT, bg=REDD) ; lgin_tst.configure(fg=WHIT, bg=REDD) ; mssg_dsp.configure(fg=WHIT, bg=REDD) 
    lgin_tst_str.set(log_ok) 

    if   not ip_chk_ok    : mssg_dsp_str.set(chk_ini) 
    elif not get_log_ok   : mssg_dsp_str.set(log_ng )  
    elif GITHUB > VERSION : mssg_dsp_str.set(github )    ; mssg_dsp.configure(fg=WHIT, bg=BLUE)        
    else                  : mssg_dsp_str.set(blank  )    ; mssg_dsp.configure(fg=WHIT, bg=GR12)   

def disp_0() :
    dmr_cl.set('  Data  \n\n\n  Data  ') ; dmr_tm.set(' Loading \n\n\n Loading ')
    dst_cl.set('\n\n  Data  \n\n'      ) ; dst_tm.set('\n\n Loading \n\n'       )
    nxd_cl.set('  Data  \n\n\n  Data  ') ; nxd_tm.set(' Loading \n\n\n Loading ')
    p25_cl.set('\n\n  Data  \n\n'      ) ; p25_tm.set('\n\n Loading \n\n'       )
    ysf_cl.set('  Data  \n\n\n  Data  ') ; ysf_tm.set(' Loading \n\n\n Loading ')

def disp_1() :
    global dmr_cl, dmr_tm, dmr_tg, dst_cl, dst_tm, dst_tg, nxd_cl, nxd_tm, nxd_tg, p25_cl, p25_tm, p25_tg, ysf_cl, ysf_tm, ysf_tg
    global LOG
    
    ET = '\n'
    dmr_str_cl = dmr_str_tm = ''
    dst_str_cl = dst_str_tm = '' 
    nxd_str_cl = nxd_str_tm = ''    
    p25_str_cl = p25_str_tm = ''    
    ysf_str_cl = ysf_str_tm = ysf_tg_str = ''    
    for i in range(0, 5):
        if i == 4 : ET = ''
        dmr_str_cl += LOG['DMR'  ][i][0] + ET ; dmr_str_tm += LOG['DMR'  ][i][3] + ET # LOG[mode][0] = [call, tg, date, time]
        dst_str_cl += LOG['DSTAR'][i][0] + ET ; dst_str_tm += LOG['DSTAR'][i][3] + ET 
        nxd_str_cl += LOG['NXDN' ][i][0] + ET ; nxd_str_tm += LOG['NXDN' ][i][3] + ET 
        p25_str_cl += LOG['P25'  ][i][0] + ET ; p25_str_tm += LOG['P25'  ][i][3] + ET 
        ysf_str_cl += LOG['YSF'  ][i][0] + ET ; ysf_str_tm += LOG['YSF'  ][i][3] + ET 
        if len(LOG['YSF'][i][1].strip()) != 0 : ysf_tg_str  = LOG['YSF'  ][i][1]
    dmr_tg.set(LOG['DMR'  ][0][1]) ; dmr_cl.set(dmr_str_cl) ; dmr_tm.set(dmr_str_tm)
    dst_tg.set(LOG['DSTAR'][0][1]) ; dst_cl.set(dst_str_cl) ; dst_tm.set(dst_str_tm)
    nxd_tg.set(LOG['NXDN' ][0][1]) ; nxd_cl.set(nxd_str_cl) ; nxd_tm.set(nxd_str_tm)
    p25_tg.set(LOG['P25'  ][0][1]) ; p25_cl.set(p25_str_cl) ; p25_tm.set(p25_str_tm)        
    ysf_tg.set(ysf_tg_str)          ; ysf_cl.set(ysf_str_cl) ; ysf_tm.set(ysf_str_tm)

def makeGUIFrame(root) :
    global tg_ref_list, tgs
    global DMR_STATUS

    text_str = "DMR TG Status Monitoring V1.50 by VK2CYO Chanyeol Yoo (C) 2020-2022"
    DMRTG = LabelFrame(root, text=text_str, width=600, font=H11, padx=5, pady=5, fg=WHIT, bg=GR12, relief=SUNKEN)

    def fixed_map(option):
        return [elm for elm in style.map("Treeview", query_opt=option) if elm[:2] != ("!disabled", "!selected")]   

    style = ttk.Style(root)
    style.configure("Treeview"               , foreground =GR12, rowheight=14   , font=H11)                      # font 는 표내용 글자 크기 조정 rowheight = row height
    style.configure("Treeview.Heading"       , foreground =GR12, background=GR12, font=H11B)                     # font 는 표제목 글자 크기 조정

    style.map("Treeview", foreground=fixed_map("foreground"), background=fixed_map("background"))

    tg_ref_list = ttk.Treeview(DMRTG, height=12, show="headings", style="Treeview")
    tg_ref_list.grid(column=1, row=2, sticky=W, rowspan=4, columnspan=5)
    ht= len(tgs)+len(tgs)//5
    tg_ref_list.config(height=ht)

    font_3=tkinter.font.Font(family="Helvetica", size=11)                          # EMPTY
    font_4=tkinter.font.Font(family="Helvetica", size=11)                          # ONAIR
    font_5=tkinter.font.Font(family="Helvetica", size=11)                          # STDBY
    font_6=tkinter.font.Font(family="Helvetica", size=11)                          # Line
    tg_ref_list.tag_configure("EMPTY", font=font_3, foreground=WHIT, background=GR12 )
    tg_ref_list.tag_configure("ONAIR", font=font_4, foreground=WHIT, background=BLUE )
    tg_ref_list.tag_configure("STDBY", font=font_5, foreground=GOLD, background=GR12 )
    tg_ref_list.tag_configure("LINE" , font=font_6, foreground=GRAY, background=GR12 )

    cols = ("TG", "On Air", "Last Call")
    widths = [80, 80, 520]
    tg_ref_list.config(columns=cols)
    tg_ref_list.column("#0", width=0 )

    i = 0
    for item in cols:
        a = 'center' if i < 2 else 'w'
        tg_ref_list.column( item, width=widths[i], anchor=a )
        tg_ref_list.heading(item, text=item)
        i += 1
    i = 0
    for tg in tgs :
        col_0 = col_1 = col_2 = ' '.ljust(115, ' ')
        tg_ref_list.see(tg_ref_list.insert('', 'end', None, value=(tg, col_1, col_2), tags=('EMPTY')  ))
        i += 1
        if (i)%5 == 0 :                     ## 매 5 라인마다 구분선 삽입
            ln = ' '.ljust(115, '-')
            tg_ref_list.insert('', 'end', None, value=(ln, ln, ln), tags=('LINE') ) 
    return DMRTG

def disp_2() :
    global tg_ref_list
    global DMR_STATUS

    tg_ref_list.delete(*tg_ref_list.get_children())
    i = 0
    font_x = 'EMPTY'
    for tg in DMR_STATUS :
        col_0  = DMR_STATUS[tg]['tg'    ]
        col_1  = DMR_STATUS[tg]['on_air']
        col_2  = DMR_STATUS[tg]['stdby' ]    
        font_x = DMR_STATUS[tg]['status'] 
        if col_1.isdigit() :                                ## 만약 숫자면 Last Heard Elapsed Time을 보여 줌
            elap  = time() - int(col_1)
            col_1 = strftime('%H:%M:%S', gmtime(elap))
            if elap > 3600 : font_x = 'EMPTY'         ## 1시간 이상 교신이 없으면 황색 -> 흰색으로 변경 
        tg_ref_list.see(tg_ref_list.insert('', 'end', None, value=(col_0, col_1, col_2), tags=(font_x)  ))
        i += 1
        if (i)%5 == 0 :                     ## 매 5 라인마다 구분선 삽입
            ln = ' '.ljust(115, '-')
            tg_ref_list.insert('', 'end', None, value=(ln, ln, ln), tags=('LINE')  )        

def get_log_start() :
    global IP, ID, PW, channel, last_today, ssh
    global get_log_ok
    try : 
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()                                                 # Load SSH host keys.
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())                   # Add SSH host key automatically if needed.   
        ssh.connect(IP, username=ID, password=PW, look_for_keys=False , timeout=2)
        channel = ssh.get_transport().open_session()        
        last_today = log_file_name('today')
        cmd_0 = "tail -f " + last_today
        channel.exec_command(cmd_0)   
        get_log_ok = True
    except : beep(1, '--- get_log_start error') ; get_log_ok = False 
    return get_log_ok

def get_log_loop() :
    global ip_chk_ok, get_log_ok, last_ip_chk, channel, last_today, monitor, last_update, ssh
    global down_log, last_time, IP

    disp_2()                                # dmr_status display    
    if ip_chk_ok and get_log_ok :
        if down_log :
            down_log_stack()                # yesterday, today log download and stack
            os.system('del log.txt')   
            down_log = False
        else : disp_1()                     # five mod log status display

        if last_today != log_file_name('today') : get_log_start()   # trail -f MMDVM_Bridge.log --> get_log_ok True/False 결정
        if get_log_ok : 
            rl, wl, xl = select.select([channel], [], [], 0.0)
            if len(rl) > 0:
                line = str(channel.recv(1024))
                x1 = x2 = 0
                line_log = []
                while True :        
                    x1 = line.find("M: ", x2+1)
                    x2 = line.find("\\n", x1+1)
                    if x2 == -1 or x1 == -1  : break            
                    line_log.append( line[x1:x2+1] )
                for line_stack in line_log :
                    stack_LOG(line_stack) 
                    print(line_stack)    

    if time() - last_time > 15 :                    # 매 30초마다 ip_check() 실행
        last_time = time() ; 
        if ip_check(IP) : 
            if not last_ip_chk :
                ssh.close() ; get_log_start()       # last_ip_chk False 이후 trail -f MMDVM_Bridge.log 다시 시작
                last_ip_chk = True  
        else :  last_ip_chk = False
    DVS_cnt_info()                              # Five Mode Log 마지막 IP, ID, PW, ping, Log, New Version 표시
    root.after(2000, get_log_loop)  

def on_closing():
    global monitor
    monitor.stop()      # monitor thread 중지 2021.03.01
    root.destroy()
####################################################################################################################################
root = Tk()
root.title("Five Mode Log Status & DMR TG Status Monitoring")

tgs, IP, ID, PW = read_server_info()
row = 12 + len(tgs) + len(tgs)//5 
hgt = row * 14 
# dms = '755x'+str(hgt)+'+60+00'
dms = '+60+00'
# root.geometry(dms)
root.resizable(False, False)
style = ttk.Style()
style.configure("Fix.Font", font=("TkFixedFont", 11))

Five_Mode=makeTextFrame(root)       ## 여기서 ip_chk하고 ip_chk_ok 리턴
DMR_Status=makeGUIFrame(root)
Five_Mode.grid( padx=5, pady=1, row=0, column=0)
DMR_Status.grid(padx=5, pady=5, row=1, column=0, sticky=(W,E))

monitor = Monitor(tgs)
monitor.start()

root.after(2000, get_log_loop) 
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()