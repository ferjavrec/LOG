import asyncio
import websockets
import os
import sys
import requests
import tkinter
from   tkinter import *
from   tkinter import ttk
from   tkinter import font
import tkinter.font
from   tkinter import messagebox
import tkinter.font as tkfont
import tkinter as tk
import paramiko
import select
import threading
from   time     import time, sleep, localtime, strftime
from   datetime import date, datetime, timedelta
import pysftp
import subprocess 
from   ping3 import ping, verbose_ping

os.system('cls')
####################################################
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

ver        = 1.5
IS_TEST    = False
start_time = st_time = last_update = time()
last_today = ""
START      = 0
tg_DST = tg_NXD = tg_P25 = tg_YSF = ''

###########################################################################################
NUM_HISTORY = 10
TIMEOUT     = 3600
disp_line   = 5
tgs         = [] #[450, 45021, 45022, 45023, 45024, 45025, 45026, 45027, 45028, 45029, 91, 3100, 214]
IP  = '192.168.0.160'
ID = PW     = 'dvswitch'
ip_id_pw    = 'ip=192.168.0.160 | id=dvswitch | pw=dvswitch'
get_log_ok  = False
ip_chk_ok   = False
ping_chk    = 'NG'
###########################################################################################

logs          = {}
logs['DMR'  ] = {}
logs['DSTAR'] = {}
logs['NXDN' ] = {}
logs['YSF'  ] = {}
logs['P25'  ] = {}
DMR_STATUS    = {}
for mode in ('DMR', 'DSTAR', 'NXDN', 'P25', 'YSF') :
    i = 0
    while i < disp_line :
        logs[mode][i] = ['            ', '        ', '2021-02-21', '00:00:00']
        i += 1

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

def elapsed_time() :
    global start_time
    elapsed = time() - start_time
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return "{:0>2}:{:0>2}:{:0>2.0f}".format(int(hours),int(minutes),seconds)

def log_stack(mode, call, tg, date, time) :  
    global logs
    call = call.ljust(8,' ')[:8]
    tg   =   tg.ljust(8,' ')[:8]
    i = 0
    for str_logs in logs[mode] :
        i += 1    
        if call == logs[mode][0][0] :                # 같은 Callsign 일 경우 시간만 바꿈
            logs[mode][0] = [call, tg, date, time]
            return
    while 0 < i :
        str_logs = logs[mode][i-1]
        logs[mode][i] = str_logs
        i -= 1
    logs[mode][0] = [call, tg, date, time]

def utc2local(utc_datetime):
    try :
        time_1 = datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S') 
        now_timestamp = time()
        offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
        time_2 = time_1 + offset
    except : time_2 = utc_datetime
    return time_2.strftime('%Y-%m-%d'), time_2.strftime('%H:%M:%S')

def checkFile(filePath):                    # 파일 유무 확인
    try:
        with open(filePath, 'r') as f : return True
    except FileNotFoundError     as e : return False
    except IOError               as e : return False 

def ip_check(IP) :
    global ping_chk
    OS_IS = 'WIN'
    if OS_IS == "WIN" : ping_chk = ping(IP)
    else              : ping_chk = subprocess.call(["ping", IP, "-c1", "-W2", "-q"], stdout=open(os.devnull,'w'))
    if ping_chk == 1 or ping_chk == None : ping_chk = 'NG' ; return False
    else                                 : ping_chk = 'OK' ; return True

def log_file_name(key) :
    global get_log_ok                                                           # Key = yesterday, today
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
    except : 
        get_log_ok = False
    return get_log_ok

def read_log() :
    global total_line, file_lines
    try :
        with open('log.txt',  mode='r', encoding='windows-1252') as open_file :      
            lines = open_file.readlines()
        return lines
    except : lines = {} ; pass
    return lines

def read_server_info() : 
    global logs_tgs, tgs, IP, ID, PW, ip_chk_ok
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
                    logs_tgs = {}
                    for tg in tgs : logs_tgs[tg] = []  
                elif 'ip=' in line : 
                    IP_ID_PW  = line.split('|')
                    IP = IP_ID_PW[0][IP_ID_PW[0].find('ip=')+3:].strip()
                    ID = IP_ID_PW[1][IP_ID_PW[1].find('id=')+3:].strip()
                    PW = IP_ID_PW[2][IP_ID_PW[2].find('pw=')+3:].strip()
                    ip_chk_ok = False
    else :
        with open('./log.ini', mode='w+') as open_file : 
            open_file.seek(0)
            open_file.write('tgs=[450, 45021, 45022, 45023, 45024, 45025, 45026, 45027, 45028, 45029, 91, 3100, 214] \n')
            open_file.write('ip=192.168.0.160 | id=dvswitch | pw=dvswitch \n')
        sleep(1)
        read_server_info()
    return tgs, IP, ID, PW

def stack_logs(line) : #file_log) :
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
            print('---', line_3)
            call = line_3[line_3.find('from')+5:line_3.find('/') ].strip()
            if 'via' in line_3 : 
                tg_DST = line_3[line_3.find('via')+3 :           ].strip()
            tg = tg_DST
        elif mode == 'YSF'         : 
            call = line_3[line_3.find('from')+5:line_3.find('to')].strip().replace('-RPT','')
            tg = tg_YSF
        if call != '' : log_stack(mode, call.ljust(8,' '), tg, str_date, str_time)              
    elif 'YSF' in line and 'tgs=' in line :         #   YSF, Remote CMD: tgs=74652
        tg_YSF = line[line.find('tgs=')+4:].strip().replace('74652', '119-YSF').replace('32642', '021-YSF').replace('37865', 'YCS450').replace('62432', 'C4DS5QDR').ljust(8,' ')
  
def disp_log() :   
    global st_time, ip_chk_ok, tgs, IP, ID, PW
    st_time   = time()    
    if tgs == [] or (not ip_chk_ok) :                           ##### log.ini 파일 읽기 
        tgs, IP, ID, PW = read_server_info()    
    if not ip_chk_ok :                                          ##### Server IP 주소 Ping Test 한번만 확인
        ip_chk_ok = ip_check(IP)                            
    if ip_chk_ok :       
        now_time = datetime.today().strftime('%H')
        if int(now_time) < 18 : 
            yest_today = ['yesterday', 'today']
        else : yest_today = ['today']
        for key in yest_today :                                 ##### Read Log File  
            file_name = log_file_name(key)
            get_log_ok = get_log(IP, ID, PW, file_name) 
            if get_log_ok :
                file_lines = read_log()                 
                for line in file_lines : 
                    stack_logs(line) 
            
######################################################################################
class Monitor(threading.Thread):
    def __init__(self, tgs, timeout=TIMEOUT, num_logs=NUM_HISTORY) :
        global logs_tgs        
        threading.Thread.__init__(self)
        self.tgs = tgs
        self.timeout = timeout
        self.num_logs = num_logs
        self.logs_tgs = logs_tgs
        for tg in tgs :  self.logs_tgs[tg] = []
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
        data_new = data_new[0:(self.num_logs)]
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
                            self.logs_tgs[dstID] = self.sort_data_by_time(self.logs_tgs[dstID] + [data])

                            now = time()
                            for tg in self.tgs:
                                text_tg     = tg
                                text_active = text_inactive = ''
                                last_heard_time = '       '
                                history_tg  = self.logs_tgs[tg]     
                                # print('---', history_tg)                                                 
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
                                # print('---', DMR_STATUS[tg])
                        if self._flag_stop : return
            except Exception as e:  pass #print('RESTART 2 : ' + e.__str__()) 

    def run(self) :
        self._flag_stop = False
        asyncio.run(self.process())        
    def stop(self) :
        self._flag_stop = True      

def get_log_start() :
    global tgs, IP, ID, PW, channel, ip_chk_ok, last_today, cmd_0, ssh

    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()                                                 # Load SSH host keys.
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())                   # Add SSH host key automatically if needed.   
    ssh.connect(IP, username=ID, password=PW, look_for_keys=False , timeout=2)
    channel = ssh.get_transport().open_session()        
    last_today = log_file_name('today')
    cmd_0 = "tail -f " + last_today
    channel.exec_command(cmd_0)   
    get_log_ok = True
 
def get_log_loop() :
    global get_log_ok, ip_chk_ok, channel, last_today, monitor, START, cmd_0, last_update, ssh
    i = 0
    if ip_chk_ok :
        if last_today != log_file_name('today') :
            get_log_start()
        rl, wl, xl = select.select([channel], [], [], 0.0)
        if len(rl) > 0:
            line = str(channel.recv(1024))
            i = x1 = x2 = 0
            line_log = []
            while True :        
                x1 = line.find("M: ", x2+1)
                x2 = line.find("\\n", x1+1)
                if x2 == -1 or x1 == -1  : break            
                line_log.append( line[x1:x2+1] )
                i += 1
            for line_stack in line_log :
                stack_logs(line_stack) 
                print(line_stack)
    if START < 2 : START += 1
    elif START == 2 :    
        disp_log()
        os.system('del log.txt')   
        os.system('del null')
        START += 1
    elif START > 2 : 
        START += i 
        if i != 0 : last_update = time()
        if time() - last_update > 120 : 
            ssh.close()
            get_log_start()
    disp_1()
    disp_2()
    root.after(2000, get_log_loop)  

def on_closing():
    global monitor
    monitor.stop()      # monitor thread 중지 2021.03.01
    root.destroy()

############################################################################################################

def makeTextFrame(root) :
    global IP, ID, PW, ping_chk
    global dmr_cl, dmr_tm, dmr_tg, dst_cl, dst_tm, dst_tg, nxd_cl, nxd_tm, nxd_tg, p25_cl, p25_tm, p25_tg, ysf_cl, ysf_tm, ysf_tg

    dmr_cl = StringVar('') ; dmr_tm = StringVar('') ; dmr_tg = StringVar('')
    dst_cl = StringVar('') ; dst_tm = StringVar('') ; dst_tg = StringVar('')
    nxd_cl = StringVar('') ; nxd_tm = StringVar('') ; nxd_tg = StringVar('')
    p25_cl = StringVar('') ; p25_tm = StringVar('') ; p25_tg = StringVar('')
    ysf_cl = StringVar('') ; ysf_tm = StringVar('') ; ysf_tg = StringVar('')

    text_str = "Five Mode Log Status V1.50 by DS5QDR Lee, Heonmin (C) 2021-2022"
    Five = LabelFrame(root, text=text_str, width=600, font=H11, padx=5, pady=0, fg=WHIT, bg=GR25, relief=SUNKEN)

    Label(Five, text='DMR'         , fg=GOLD, bg=GR25, font=H11B).grid(row=1, column= 1, sticky=(W), padx=2, pady=0)    
    Label(Five, textvariable=dmr_tg, fg=GOLD, bg=GR25, font=H11B).grid(row=1, column= 2, sticky=(W), padx=2, pady=0)
    Label(Five, textvariable=dmr_cl, fg=GOLD, bg=GR25, font=H11 ).grid(row=2, column= 1, sticky=(W), padx=2, pady=0, rowspan=5)
    Label(Five, textvariable=dmr_tm, fg=GOLD, bg=GR25, font=H11 ).grid(row=2, column= 2, sticky=(W), padx=2, pady=0, rowspan=5)

    Label(Five, text='DSTAR'       , fg=WHIT, bg=GR25, font=H11B).grid(row=1, column= 3, sticky=(W), padx=2, pady=0)    
    Label(Five, textvariable=dst_tg, fg=WHIT, bg=GR25, font=H11B).grid(row=1, column= 4, sticky=(W), padx=2, pady=0)
    Label(Five, textvariable=dst_cl, fg=WHIT, bg=GR25, font=H11 ).grid(row=2, column= 3, sticky=(W), padx=2, pady=0, rowspan=5)
    Label(Five, textvariable=dst_tm, fg=WHIT, bg=GR25, font=H11 ).grid(row=2, column= 4, sticky=(W), padx=2, pady=0, rowspan=5)

    Label(Five, text='NXDN'        , fg=GOLD, bg=GR25, font=H11B).grid(row=1, column= 5, sticky=(W), padx=2, pady=0)    
    Label(Five, textvariable=nxd_tg, fg=GOLD, bg=GR25, font=H11B).grid(row=1, column= 6, sticky=(W), padx=2, pady=0)
    Label(Five, textvariable=nxd_cl, fg=GOLD, bg=GR25, font=H11 ).grid(row=2, column= 5, sticky=(W), padx=2, pady=0, rowspan=5)
    Label(Five, textvariable=nxd_tm, fg=GOLD, bg=GR25, font=H11 ).grid(row=2, column= 6, sticky=(W), padx=2, pady=0, rowspan=5)

    Label(Five, text='P25'         , fg=WHIT, bg=GR25, font=H11B).grid(row=1, column= 7, sticky=(W), padx=2, pady=0)    
    Label(Five, textvariable=p25_tg, fg=WHIT, bg=GR25, font=H11B).grid(row=1, column= 8, sticky=(W), padx=2, pady=0)
    Label(Five, textvariable=p25_cl, fg=WHIT, bg=GR25, font=H11 ).grid(row=2, column= 7, sticky=(W), padx=2, pady=0, rowspan=5)
    Label(Five, textvariable=p25_tm, fg=WHIT, bg=GR25, font=H11 ).grid(row=2, column= 8, sticky=(W), padx=2, pady=0, rowspan=5)

    Label(Five, text='YSF'         , fg=GOLD, bg=GR25, font=H11B).grid(row=1, column= 9, sticky=(W), padx=2, pady=0)    
    Label(Five, textvariable=ysf_tg, fg=GOLD, bg=GR25, font=H11B).grid(row=1, column=10, sticky=(W), padx=2, pady=0)
    Label(Five, textvariable=ysf_cl, fg=GOLD, bg=GR25, font=H11 ).grid(row=2, column= 9, sticky=(W), padx=2, pady=0, rowspan=5)
    Label(Five, textvariable=ysf_tm, fg=GOLD, bg=GR25, font=H11 ).grid(row=2, column=10, sticky=(W), padx=2, pady=0, rowspan=5)

    ip_check(IP)
    text_str = 'DVSwitch Info : ip =' + IP + '   id=' + ID + '   pw=' + PW + '   ping_test=' + ping_chk
    Label(Five, text=text_str, fg=AQUA, bg=GR25, font=H11 ).grid(row=8, column=1, sticky=(W), padx=2, pady=0, columnspan=8)

    return Five

def disp_1() :
    global dmr_cl, dmr_tm, dmr_tg, dst_cl, dst_tm, dst_tg, nxd_cl, nxd_tm, nxd_tg, p25_cl, p25_tm, p25_tg, ysf_cl, ysf_tm, ysf_tg
    global logs
    
    ET = '\n'
    dmr_str_cl = dmr_str_tm = ''
    dst_str_cl = dst_str_tm = '' 
    nxd_str_cl = nxd_str_tm = ''    
    p25_str_cl = p25_str_tm = ''    
    ysf_str_cl = ysf_str_tm = ysf_tg_str = ''    
    for i in range(0, 5):
        if i == 4 : ET = ''
        dmr_str_cl += logs['DMR'  ][i][0] + ET ; dmr_str_tm += logs['DMR'  ][i][3] + ET # logs[mode][0] = [call, tg, date, time]
        dst_str_cl += logs['DSTAR'][i][0] + ET ; dst_str_tm += logs['DSTAR'][i][3] + ET 
        nxd_str_cl += logs['NXDN' ][i][0] + ET ; nxd_str_tm += logs['NXDN' ][i][3] + ET 
        p25_str_cl += logs['P25'  ][i][0] + ET ; p25_str_tm += logs['P25'  ][i][3] + ET 
        ysf_str_cl += logs['YSF'  ][i][0] + ET ; ysf_str_tm += logs['YSF'  ][i][3] + ET 
        if len(logs['YSF'][i][1].strip()) != 0 : ysf_tg_str  = logs['YSF'  ][i][1]
    dmr_tg.set(logs['DMR'  ][0][1].replace(' ','')) ; dmr_cl.set(dmr_str_cl) ; dmr_tm.set(dmr_str_tm)
    dst_tg.set(logs['DSTAR'][0][1].replace(' ','')) ; dst_cl.set(dst_str_cl) ; dst_tm.set(dst_str_tm)
    nxd_tg.set(logs['NXDN' ][0][1].replace(' ','')) ; nxd_cl.set(nxd_str_cl) ; nxd_tm.set(nxd_str_tm)
    p25_tg.set(logs['P25'  ][0][1].replace(' ','')) ; p25_cl.set(p25_str_cl) ; p25_tm.set(p25_str_tm)        
    ysf_tg.set(ysf_tg_str.replace(' ',''))          ; ysf_cl.set(ysf_str_cl) ; ysf_tm.set(ysf_str_tm)

def makeGUIFrame(root) :
    global tg_ref_list, tgs
    global DMR_STATUS

    text_str = "DMR TG Status Monitoring V1.50 by VK2CYO Chanyeol Yoo (C) 2020-2022"
    DMRTG = LabelFrame(root, text=text_str, width=600, font=H11, padx=5, pady=5, fg=WHIT, bg=GR25, relief=SUNKEN)

    def fixed_map(option):
        return [elm for elm in style.map("Treeview", query_opt=option) if elm[:2] != ("!disabled", "!selected")]   

    style = ttk.Style(root)
    style.configure("Treeview"               , foreground =GR25, rowheight=14   , font=H11)                      # font 는 표내용 글자 크기 조정 rowheight = row height
    style.configure("Treeview.Heading"       , foreground =GR25, background=GR25, font=H11B)                     # font 는 표제목 글자 크기 조정

    style.map("Treeview", foreground=fixed_map("foreground"), background=fixed_map("background"))

    tg_ref_list = ttk.Treeview(DMRTG, height=12, show="headings", style="Treeview")
    tg_ref_list.grid(column=1, row=2, sticky=W, rowspan=4, columnspan=5)
    ht= len(tgs)+len(tgs)//5
    # print('---------------------', ht)
    tg_ref_list.config(height=ht)

    font_3=tkinter.font.Font(family="Helvetica", size=11 )
    font_4=tkinter.font.Font(family="Helvetica", size=11 )
    font_5=tkinter.font.Font(family="Helvetica", size=11 )
    font_6=tkinter.font.Font(family="Helvetica", size=11 )
    tg_ref_list.tag_configure("EMPTY", font=font_3, foreground=WHIT, background=GR25 )
    tg_ref_list.tag_configure("ONAIR", font=font_4, foreground=WHIT, background=BLUE )
    tg_ref_list.tag_configure("STDBY", font=font_5, foreground=GOLD, background=GR25 )
    tg_ref_list.tag_configure("LINE" , font=font_6, foreground=WHIT, background=GR25 )

    cols = ("TG", "On Air", "Last Call")
    widths = [80, 80, 535]
    tg_ref_list.config(columns=cols)
    tg_ref_list.column("#0", width=0 )

    i = 0
    for item in cols:
        a = 'center' if i < 2 else 'w'
        tg_ref_list.column( item, width=widths[i], anchor=a )
        tg_ref_list.heading(item, text=item)
        i += 1
    return DMRTG

def disp_2() :
    global tg_ref_list
    global DMR_STATUS

    tg_ref_list.delete(*tg_ref_list.get_children())
    i = 0
    font_x = 'EMPTY'
    for tg in DMR_STATUS :
        col_0 = DMR_STATUS[tg]['tg'    ]
        col_1 = DMR_STATUS[tg]['on_air']
        if col_1.isdigit() :                ## 만약 숫자면 Last Heard Elapsed Time을 보여 줌
            elap  = time() - int(col_1)
            col_1 = str(int(elap//60)).rjust(2, '0')+':'+str(int(elap%60)).rjust(2, '0') 
        col_2  = DMR_STATUS[tg]['stdby' ]
        font_x = DMR_STATUS[tg]['status']
        tg_ref_list.see(tg_ref_list.insert('', 'end', None, value=(col_0, col_1, col_2), tags=(font_x)  ))
        i += 1
        if (i)%5 == 0 :                     ## 매 5 라인마다 구분선 삽입
            ln = ' '.ljust(110, '-')
            tg_ref_list.insert('', 'end', None, value=(ln, ln, ln), tags=('LINE')  )        

####################################################################################################################################
root = Tk()
root.title("Five Mode Log Status & DMR TG Status Monitoring")

tgs, IP, ID, PW = read_server_info()
row = 12 + len(tgs) + len(tgs)//5 
hgt = row * 14 - 1
dms = '755x'+str(hgt)+'+60+00'
# root.geometry(dms)
root.resizable(False, False)
style = ttk.Style()
style.configure("Fix.Font", font=("TkFixedFont", 11))

Five_Mode=makeTextFrame(root)
Five_Mode.grid( padx=5, pady=1, row=0, column=0)
DMR_Status=makeGUIFrame( root)
DMR_Status.grid(padx=5, pady=5, row=1, column=0, sticky=(W,E))

get_log_start()
monitor = Monitor(tgs)
monitor.start()

root.after(2000, get_log_loop) 
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
