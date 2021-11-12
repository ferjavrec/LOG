import asyncio
import websockets
import os
import sys
import requests
import tkinter

import paramiko
import select
import threading

from   time     import time, sleep, localtime, strftime
from   datetime import date, datetime, timedelta
import pysftp

os.system('mode con: cols=100 lines=30')

ver        = 1.2
IS_TEST    = False
start_time = st_time = last_update = time()
last_today = ""
START      = 0

###########################################################################################
NUM_HISTORY = 10
TIMEOUT     = 3600
disp_line   = 5
tgs         = [] #[450, 45021, 45022, 45023, 45024, 45025, 45026, 45027, 45028, 45029, 91, 3100, 214]
IP          = '192.168.0.160'
ID = PW     = 'dvswitch'
ip_id_pw    = 'ip=192.168.0.160 | id=dvswitch | pw=dvswitch'
get_log_ok    = False
ip_chk_ok      = False
###########################################################################################

logs          = {}
logs['DMR'  ] = {}
logs['DSTAR'] = {}
logs['NXDN' ] = {}
logs['YSF'  ] = {}
logs['P25'  ] = {}
for mode in ('DMR', 'DSTAR', 'NXDN', 'P25', 'YSF') :
    i = 0
    while i < disp_line :
        logs[mode][i] = ['        ', '        ', '2021-02-21', '00:00:00']
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
os.system('cls')

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
    global ip_chk_ok
    ping_chk = os.system("ping -n 1 -w 1 " + IP + "> null") 
    if ping_chk == 0 : return True
    else             : return False

def log_file_name(key) :
    global get_log_ok                                                           # Key = yesterday, today
    now_time = datetime.today().strftime('%H')
    if int(now_time) < 9 :                                                      # UTC Local 전환 시 파일 명 변경
        today        = (date.today() - timedelta(1)).strftime('%Y-%m-%d')
        yesterday    = (date.today() - timedelta(2)).strftime('%Y-%m-%d')
    else :
        today        = (date.today()               ).strftime('%Y-%m-%d')
        yesterday    = (date.today() - timedelta(1)).strftime('%Y-%m-%d')   
    if key == 'yesterday' : 
        file_name    = '/var/log/mmdvm/MMDVM_Bridge-' + yesterday + '.log'
    elif key == 'today' :
        file_name    = '/var/log/mmdvm/MMDVM_Bridge-' + today     + '.log'
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
            file_lines = open_file.readlines()
        return file_lines
    except : file_lines = {} ; pass
    return file_lines

def print_log(key) :
    global logs, st_time, text, prt_line
    interval =  str(time() - st_time)[0:5] 
    st_time  = time()
    prt_line = []
    line_0   = ' Five Mode Log Disp V1.0 by DS5QDR (C) 2021  ^^   Last updated : ' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '   ' + str(interval) + '  \n'
    prt_line.append(line_0)
    text.delete(1.0, 40.80)
    if ip_chk_ok :       
        i = 0
        while i < disp_line :
            if i == 0 :
                line_1 = ' DMR     ' + logs['DMR'][i][1] +                     ' | ' +          'DSTAR   ' + logs['DSTAR'][i][1] + ' | ' +        'P25     ' + logs['P25'][i][1] + ' | ' +         'NXDN    ' + logs['NXDN'][i][1] + ' | ' + 'YSF     '        + logs['YSF'][i][1] + ' \n' 
                line_2 = '       '   + logs['DMR'][i][2] +                     ' |       '                 + logs['DSTAR'][i][2] + ' |       '               + logs['P25'][i][2] + ' |       '                + logs['NXDN'][i][2] + ' |       '               + logs['YSF'][i][2] + '\n' 
                line_3 = ' '         + logs['DMR'][i][0] + logs['DMR'][i][3] + ' | ' + logs['DSTAR'][i][0] + logs['DSTAR'][i][3] + ' | ' + logs['P25'][i][0] + logs['P25'][i][3] + ' | ' + logs['NXDN'][i][0] + logs['NXDN'][i][3] + ' | ' + logs['YSF'][i][0] + logs['YSF'][i][3] + '\n'
                prt_line.append( line_1 )
                prt_line.append( line_2 )
                prt_line.append( line_3 )
            else :
                line_3 = ' '         + logs['DMR'][i][0] + logs['DMR'][i][3] + ' | ' + logs['DSTAR'][i][0] + logs['DSTAR'][i][3] + ' | ' + logs['P25'][i][0] + logs['P25'][i][3] + ' | ' + logs['NXDN'][i][0] + logs['NXDN'][i][3] + ' | ' + logs['YSF'][i][0] + logs['YSF'][i][3] + '\n'
                prt_line.append( line_3 )
            i += 1 
    else : 
        line_1 = '\n DVSwitch Server 정보를 확인중에 있습니다. 10초 후에도 Log 정보가 보이지 않으면 \n log.ini 파일 내 IP, ID, PW 정보를 수정하신 후 재시작 하세요 \n\n'
        prt_line.append( line_1 )    
    line_5 = ' DVSwitch Info : ip=' + IP.ljust(16,' ') + ' | id=' + ID.ljust(13, ' ') + ' | pw=' + PW.ljust(12, ' ') + '  | ' + str(ip_chk_ok) + '    ' + str(get_log_ok) + '\n\n'
    prt_line.append( line_5 ) 

def read_server_info() : 
    global logs_tgs, tgs, IP, ID, PW, ip_chk_ok
    if checkFile('./log.ini') :       
        with open('./log.ini', mode='r') as open_file :    
            file_lines = open_file.readlines()
            open_file.seek(0)
            for line in file_lines :
                if 'tgs' in line :
                    tgs_str_1 = line[line.find('[')+1:line.find(']')]
                    tgs_str_2 = tgs_str_1.split(',')
                    tgs = []
                    for tg in tgs_str_2 :
                        tgs.append(int(tg))   
                    logs_tgs = {}
                    for tg in tgs :
                        logs_tgs[tg] = []  
                elif 'ip=' in line : 
                    IP_ID_PW  = line.split('|')
                    IP = IP_ID_PW[0][IP_ID_PW[0].find('ip=')+3:].strip()
                    ID         = IP_ID_PW[1][IP_ID_PW[1].find('id=')+3:].strip()
                    PW         = IP_ID_PW[2][IP_ID_PW[2].find('pw=')+3:].strip()
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
    line_1 = line[ 3:22]
    line_2 = line[27:line.find(',')].replace('DMR Slot 2', 'DMR').replace('D-Star', 'DSTAR')
    line_3 = line[line.find(',')+1:line.find('\n')]
    
    mode = line_2
    str_date, str_time = utc2local(line_1)    
    if 'from' in line_3 and 'to' in line_3 :
        if   mode in 'DMR NXDN P25' :
            call = line_3[line_3.find('from')+5:line_3.find('to')].strip()
            tg   = line_3[line_3.find('TG')    :                 ].strip()
        elif mode == 'DSTAR'     : 
            call = line_3[line_3.find('from')+5:line_3.find('/') ].strip()
            tg   = line_3[line_3.find('via')+3 :                 ].strip()            
        elif mode == 'YSF'         : 
            call = line_3[line_3.find('from')+5:line_3.find('to')].strip().replace('-RPT','')
            tg = tg_YSF
    elif 'YSF' in line and 'tgs=' in line :            
        tg_YSF = line[line.find('tgs=')+4:].strip().replace('74652', '119-YSF').replace('32642', '021-YSF').replace('37865', 'YCS450').replace('62432', 'C4DS5QDR').ljust(8,' ')
    if 'from' in line and 'to' in line :
        log_stack(mode, call.ljust(8,' '), tg, str_date, str_time)  
  
def disp_log() :
    global st_time, ip_chk_ok, tgs, IP, ID, PW, text 
    st_time   = time()
    
    if tgs == [] or (not ip_chk_ok) :                           ##### log.ini 파일 읽기 
        tgs, IP, ID, PW = read_server_info()    
    if not ip_chk_ok :                                          ##### Server IP 주소 Ping Test 한번만 확인
        ip_chk_ok = ip_check(IP)                            
    if ip_chk_ok :       
        print_log(ip_chk_ok)                                    # 초기 공백 5 mode 출력
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
            text.delete(1.0, 40.80)
            print_log(get_log_ok)
            
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

    def get_data_from_packet(self, str):
        str = str.replace('\\', '')
        str = str.replace('"{', '{')
        str = str.replace('}"', '}')
        str = str.replace('null', 'None')
        str = str[str.find('{'):str.rfind('}')+1]
        try:
            data = eval(str)
            return data['payload']
        except: return None

    async def process(self):
        uri = "wss://api.brandmeister.network/lh/%7D/?EIO=3&transport=websocket"
        while True:
            try:
                async with websockets.connect(uri) as self.websocket:
                    while True:
                        str = await self.websocket.recv()                        
                        data = self.get_data_from_packet(str)
                        if data==None : continue
                        if data['DestinationID'] in self.tgs:
                            dstID = data['DestinationID']
                            self.logs_tgs[dstID] = self.sort_data_by_time(self.logs_tgs[dstID] + [data])
                        if self._flag_stop : return
            except Exception as e: pass

    def run(self) :
        self._flag_stop = False
        asyncio.run(self.process())        
    def stop(self) :
        self._flag_stop = True

def print_dmr(self) :
    global tg, tgs, logs_tgs, start_time, text, prt_line, cmd_0, last_today, START
    now = time()    
    str_1 = elapsed_time()
    line_6 = ' DMR Status Monitoring V1.5 by VK2CYO Chanyeol Yoo (C) 2021           Elapsed Time : ' + str_1 + ' \n'
    prt_line.append( line_6 )

    i = 1  
    for tg in tgs:
        text_tg = text_tg = str(tg).rjust(5, ' ')
        text_active = ''
        text_inactive = ''
        tg_color = ''
        logs_tg = self.logs_tgs[tg]
        try:
            text_inactive = ''
            for d in logs_tg:
                if text_inactive == '': last_call_time = str(int(now-d['Stop'])//60).rjust(2, '0')+':'+str((int(now-d['Stop']))%60).rjust(2,'0')
                if now - d['Stop'] < TIMEOUT:
                    text_inactive = text_inactive + ('%s ' % (d['SourceCall']).ljust(6, ' '))
            text_inactive = text_inactive

            tg_color = 'EMPTY'
            if logs_tg[0]['Stop'] == 0:
                elapsed = now-logs_tg[0]['Start']
                text_active = '%s' % (logs_tg[0]['SourceCall'])            
                text_active = text_active.ljust(7, ' ')
                text_tg     = str(tg).rjust(5, ' ')
                tg_color    = 'ONAIR'
            elif len(text_inactive) > 0:
                text_active = last_call_time
                text_tg     = str(tg).rjust(5, ' ')
                tg_color    = 'STDBY'
        except Exception as e: a = 1            
        line_7 = ' %s | %s| %s' % (text_tg, text_active.ljust(7), text_inactive) + '\n'
        prt_line.append( line_7 )

        if not (i%5) : prt_line.append( '\n' )
        i += 1
    prt_line.append(' DVSwitch Log File : ' + last_today + ' : ' + str(START) + ' : ' + str(int(time()-last_update)))
    for prt in prt_line :
        text.insert(tkinter.CURRENT, prt)      
    text.pack()       

    if ip_chk_ok : 
        text.tag_add(   '01', '1.0', '1.end')
        text.tag_config('01', foreground='black', background='white', borderwidth=10)    
        text.tag_add(   '02', '2.0', '2.end')
        text.tag_config('02', foreground='red'  , background='yellow')  
        text.tag_add(   '09', '9.0', '9.end')
        text.tag_config('09', foreground='hotpink') 
        text.tag_add(   '11', '11.0', '11.60')
        text.tag_config('11', foreground='black', background='white', borderwidth=10)      
        text.tag_add(   '10', '11.60', '11.end')
        text.tag_config('10', foreground='red'  , background='white')    
        x_0 = 12+len(tgs)+len(tgs)//5
        x_1 = str(x_0) + '.0' 
        x_2 = str(x_0) + '.end'
        text.tag_add(   '12', x_1, x_2)
        text.tag_config('12', foreground='white', borderwidth=10)  
    else :
        text.tag_add(   '01', '1.0', '1.end')
        text.tag_config('01', foreground='black', background='white', borderwidth=10)    
        text.tag_add(   '02', '2.0', '2.end')
        text.tag_config('02', foreground='red'  , background='yellow')  
        text.tag_add(   '06', '6.0', '6.end')
        text.tag_config('06', foreground='hotpink') 
        text.tag_add(   '08', '8.0', '8.60')
        text.tag_config('08', foreground='black', background='white', borderwidth=10)      
        text.tag_add(   '10', '8.60', '8.end')
        text.tag_config('10', foreground='red'  , background='white')    
        x_0 = 9+len(tgs)+len(tgs)//5
        x_1 = str(x_0) + '.0' 
        x_2 = str(x_0) + '.end'
        text.tag_add(   '12', x_1, x_2)
        text.tag_config('12', foreground='white', borderwidth=10)          
    
    for i in range(12, 13+len(tgs)+len(tgs)//5-1 ) :
        str_1 = str(i)
        str_2 = str_1+'.9'
        str_3 = str_1+'.15'
        text.tag_add(   str_1, str_2, str_3)
        text.tag_config(str_1, foreground='hotpink')        

def get_log_start() :
    global tgs, IP, ID, PW, channel, ip_chk_ok, last_today, cmd_0, ssh

    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()                                                 # Load SSH host keys.
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())                   # Add SSH host key automatically if needed.   
    # try : 
    ssh.connect(IP, username=ID, password=PW, look_for_keys=False , timeout=2)
    channel = ssh.get_transport().open_session()        
    last_today = log_file_name('today')
    cmd_0 = "tail -f " + last_today
    channel.exec_command(cmd_0)   
    get_log_ok = True
    # except : 
    #     print('++++++++++', '에러 발생')
    #     get_log_ok = False
 
def get_log_loop() :
    global get_log_ok, ip_chk_ok, channel, last_today, monitor, text, START, cmd_0, last_update, ssh
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
    print_log(True)
    print_dmr(monitor)     

    window.after(2000, get_log_loop)  

def on_closing():
    global monitor
    monitor.stop()      # monitor thread 중지 2021.03.01
    window.destroy()

############################################################################################################

window = tkinter.Tk()
window.title("Five Mode Log Dispay & DMR Status Monitoring")

cmd_0 = ''

tgs, IP, ID, PW = read_server_info()
row = 12 + len(tgs) + len(tgs)//5 
hgt = row * 14 - 1
dms = '700x'+str(hgt)+'+60+00'

window.geometry(dms)
window.resizable(False, False)
text=tkinter.Text(window, width=94, height=row, fg='white', bg='black', padx=5, pady=5)

get_log_start()
monitor = Monitor(tgs)
monitor.start()

window.after(2000, get_log_loop) 
window.protocol("WM_DELETE_WINDOW", on_closing)
window.mainloop()
