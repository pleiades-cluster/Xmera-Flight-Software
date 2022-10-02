import time

# our 4 byte code to authorize commands
# pass-code for DEMO PURPOSES ONLY
super_secret_code = b'p\xba\xb8C'

# OTA command lookup & dispatch
commands = {
    b'\x8eb':    'noop',
    b'\xd4\x9f': 'hreset',   # new
    b'\x12\x06': 'shutdown',
    b'8\x93':    'query',    # new
    b'\x96\xa2': 'exec_cmd',
}

############### hot start helper ###############
def hotstart_handler(cdh,msg):
    # try
    try:
        cdh.radio1.node = cdh.cfg['id'] # this sat's radiohead ID
        cdh.radio1.destination = cdh.cfg['gs'] # target gs radiohead ID
    except: pass
    # check that message is for me
    if msg[0]==cdh.radio1.node:
        # TODO check for optional radio config

        # manually send ACK
        cdh.radio1.send('!',identifier=msg[2],flags=0x80)
        # TODO remove this delay. for testing only!
        time.sleep(0.5)
        message_handler(cdh, msg)
    else:
        print(f'not for me? target id: {hex(msg[0])}, my id: {hex(cdh.radio1.node)}')

############### message handler ###############
def message_handler(cdh,msg):
    multi_msg=False
    if len(msg) >= 10: # [RH header 4 bytes] [pass-code(4 bytes)] [cmd 2 bytes]
        if bytes(msg[4:8])==super_secret_code:
            # check if multi-message flag is set
            if msg[3] & 0x08:
                multi_msg=True
            # strip off RH header
            msg=bytes(msg[4:])
            cmd=msg[4:6] # [pass-code(4 bytes)] [cmd 2 bytes] [args]
            cmd_args=None
            if len(msg) > 6:
                print('command with args')
                try:
                    cmd_args=msg[6:] # arguments are everything after
                    print('cmd args: {}'.format(cmd_args))
                except Exception as e:
                    print('arg decoding error: {}'.format(e))
            if cmd in commands:
                try:
                    if cmd_args is None:
                        print('running {} (no args)'.format(commands[cmd]))
                        # eval a string turns it into a func name
                        eval(commands[cmd])(cdh)
                    else:
                        print('running {} (with args: {})'.format(commands[cmd],cmd_args))
                        eval(commands[cmd])(cdh,cmd_args)
                except Exception as e:
                    print('something went wrong: {}'.format(e))
                    cdh.radio1.send(str(e).encode())
            else:
                print('invalid command!')
                cdh.radio1.send(b'invalid cmd'+msg[4:])
            # check for multi-message mode
            if multi_msg:
                # TODO check for optional radio config
                print('multi-message mode enabled')
                response = cdh.radio1.receive(keep_listening=True,with_ack=True,with_header=True,view=True,timeout=10)
                if response is not None:
                    cdh.c_gs_resp+=1
                    message_handler(cdh,response)
        else:
            print('bad code?')


########### commands without arguments ###########
def noop(cdh):
    print('no-op')
    pass

def hreset(cdh):
    print('Resetting')
    try:
        cdh.radio1.send(data=b'resetting')
        cdh.micro.on_next_reset(self.cdh.micro.RunMode.NORMAL)
        cdh.micro.reset()
    except:
        pass

########### commands with arguments ###########

def shutdown(cdh,args):
    # make shutdown require yet another pass-code
    if args == b'\x0b\xfdI\xec':
        print('valid shutdown command received')
        # set shutdown NVM bit flag
        cdh.f_shtdwn=True
        # stop all tasks
        for t in cdh.scheduled_tasks:
            cdh.scheduled_tasks[t].stop()
        cdh.powermode('minimum')

        """
        Exercise for the user:
            Implement a means of waking up from shutdown
            See beep-sat guide for more details
            https://pycubed.org/resources
        """

        # deep sleep + listen
        # TODO config radio
        cdh.radio1.listen()
        if 'st' in cdh.cfg:
            _t = cdh.cfg['st']
        else:
            _t=5
        import alarm, board
        pin_alarm = alarm.pin.PinAlarm(pin=board.DAC0,value=True)
        time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + eval('1e'+str(_t))) # default 1 day
        # set hot start flag right before sleeping
        cdh.f_hotstrt=True
        alarm.exit_and_deep_sleep_until_alarms(pin_alarm,time_alarm)


def query(cdh,args):
    print(f'query: {args}')
    print(cdh.radio1.send(data=str(eval(args))))

def exec_cmd(cdh,args):
    print(f'exec: {args}')
    exec(args)