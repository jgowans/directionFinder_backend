#!/usr/bin/env python

##Basic socket interface to the R&S signal generator used for CW test signal input
# Provided by Antheun Botha, Development Engineer, MESA Product Solutions, 2015-06-05

import serial, socket, string, time
import numpy as np

class SCPI:
  PORT = 5025
  BAUDRATE = 9600

  ## Connect to the R&S signal generator
  def __init__(self,
               host=None, port=PORT,           # set up socket connection
               device=None, baudrate=BAUDRATE, # set up serial port
               bytesize=serial.EIGHTBITS,
               parity=serial.PARITY_NONE,
               stopbit=serial.STOPBITS_ONE,
               timeout=3, writeTimeout=2,
               display_info=False):
    if host and device:
      raise RuntimeError('Only one connection can be initaited at a time.\nSelect socket or serial connection.\n')

    # Ethernet socket connection
    self.connection = None
    if host:
      self.connection = 'socket'
      print 'Establishing  LAN  connection with source'
      print '\nTrying:\t\n',host
      self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.s.connect((host, port))
      self.s.settimeout(1)
      print '\tConnected\n'
    elif device:
      print 'Establishing  SERIAL  connection with source'
      print '\nTrying:\t',device,'\n'
      self.connection = 'serial'
      self.s = serial.Serial(port=device, baudrate=9600,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=3, writeTimeout=3)
      print '\tConnected\n'
    else:
      raise RuntimeError('No connections specified.\n')

    # Querie instrument identificaton
    if display_info:
        self.write("*IDN?")
        print "DEVICE: " + self.read()

  def testConnect(self):
    try:   
      self.write('*IDN?')
      return self.read()
    except:
      return False

  # send query / command via relevant port comm
  def write(self, command):
    if self.connection == 'serial':
      self.s.flushInput()
      self.s.write(command + '\r\n')
    else:
      self.s.send(command+ '\n')
    time.sleep(0.4)
  def read(self):
    if self.connection == 'serial':
      return self.s.readline().strip()
    else:
      return self.s.recv(128)

 # activates RF output
  def outputOn(self):
       self.write("OUTPut ON")
  # deactivates the RF output
  def outputOff( self):
       self.write("OUTPut OFF")
  # reset
  def reset(self):
    self.write("*RST")
    self.write(" *CLS")

  # close the comms port to the R&S signal generator
  def  __close__(self):
    self.s.close()

  # set requested frequency
  def setFrequency(self, freq):
    self.write(" FREQuency %.2f"%(freq,)) # Hz
  
  def setSweep(self, start_freq,  step_size, stop_freq, 
    SG_level, dwell_time,prnt=False):
    self.write("SYST:DISP:UPD ON")
    self.write("FREQ:STAR %f Hz"%start_freq)
    self.write("FREQ:STOP %f Hz"%stop_freq)
    self.write("SWE:SPAC LIN")
    pnts = np.round((stop_freq-start_freq)/step_size,0)+1
    self.write("SWE:POIN %f"%pnts)
    self.write("SWE:DWEL %f s"%dwell_time)
    self.write("FREQ:MODE SWE")
    if self.connection == 'serial':
        self.write("TRIG:SOUR AUTO")
    else:
        self.write("SWE:MODE AUTO")
    self.write("POW %.1f"%SG_level)
    '''print out SG settings'''
    if prnt == True:
        self.write("FREQ:STAR?")
        x=self.read()
        print '\n\nSG start:\t',x
        self.write("FREQ:STOP?")
        y=self.read()
        print 'SG STOP:\t',y
        self.write("SWE:STEP:LIN?")
        z = self.read()
        print 'SG step:\t',z
        b = float(x.rstrip())+float(z.rstrip())
        print 'SG first:\t',b,'\n\n'


  # read signal generator frequency
  def getFrequency(self):
    self.write('FREQuency?')
    return_freq=self.read()
    try:
      return_freq=float(return_freq)
    except Exception as e:
      print e
      print return_freq.split('\n')
    return return_freq # Hz

  # set requested power level
  def setPower(self, pwr):
    self .write('POWer %s'%str(pwr)) # dBm

  # read sig gen power level
  def getPower(self):
    self.write('POWer?')
    return float(self.read()) # dBm
    


if __name__ == '__main__':

  raise Exception("No no, please don't run me")

  # SMB100A R&S Signal Generator IP address
  #siggen_ip='192.168.14.68'
  siggen_ip='localhost'
  siggen_port=5025


## Using SCPI class for comms to signal generator for CW input signal
  sigme=SCPI(siggen_ip)
  time.sleep(0.5)
  #sigme.setSweep(1000, 1000, 1E5, -50, 100)
  #sigme.outputOn()
  print(sigme.getPower())
  while True:
    time.sleep(0.5)
    sigme.setFrequency(sigme.getFrequency() + 1e6)
    print(sigme.getFrequency() / 1e6)
  try:
    sigme.__close__()
    print 'Closing all ports...'
  except:
    pass # socket already closed
#fin

