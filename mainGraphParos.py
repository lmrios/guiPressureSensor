# -*- coding: utf-8 -*-

"""
Used names convention
variable : student, inkjetPrinter, bookingHistory
Class: Student, InkjetPrinter, BookingHistory
Method: Python does not define return value: getExpensesHistory(), setMyAge(age)
        Otherwise: List getExpensesHistory(), void setMyAge(int age)
Constants: MIN_REGISTRATION_AGE
Interface: (?) OnClickListener, IOnClickListener

GUI:    cboxTabMainPortParos1, cboxTabMainPortParos2, cboxTabMainTemp
        plotTabMainParos1, plotTabMainParos2, plotTabMainTemp, btnTabMainStart
        btnTabParos1Start, cboxTabParos1PortParos1 
        lblTabTempTamb
        lblTabParos_mbar (This is a FIXED label the underscore shows the text)
        
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import codeGuiGraphParos
# pyuic5 -x GuiGraphParos.ui -o codeGuiGraphParos.py


import serial
import re

import sys
import glob

import numpy as np
import threading
import queue

import collections
from time import localtime, strftime, sleep, time, clock


class PrSensors(QtWidgets.QMainWindow, codeGuiGraphParos.Ui_MainWindow):
    ''' 
    It will read serial port and graph the Pressure Sensors Data
    '''
    newTimeData = QtCore.pyqtSignal(bool)  # This signal updates the graph
    
    def __init__(self, parent=None):
        super(PrSensors, self).__init__(parent)
        self.setupUi(self)
        
        # Set all default status for labels, combobox, enable buttons, etc...
        self.lblTabParos1PortSelected.setText("No COM selected for the Paros1")
        self.paros1NPoints = self.sboxTabParos1NPoints.value()
        
        self.cboxTabParos1PortParos1.clear()
        self.cboxTabParos1PortParos1.addItem("Select COM")
        self.cboxTabParos1PortParos1.addItems(serialPorts) # is serialPorts a global variable ??? It seems so...
        self.cboxTabParos1PortParos1.update()
        
        self.changeTextSize(20)
        self.changeParos1NPoints(10) # it goes to  self.statusGuiTabParos1 = "READY"
        
        
        self.openedSerialPorts = []
        
        self.serialDevice1Port = 'COM6'
        self.serialDevice1Baudrate = 9600
        self.serialDevice1Timeout= 10
        self.serialDevice1Data = []
        
        # d = collections.deque(maxlen=10)
        
        self.serialDevice2Port = 'COM10'
        self.serialDevice2Baudrate = 9600
        self.serialDevice2Timeout= 10
        self.serialDevice2Data = []
        
        self.serialDevice3Port = 'COM11'
        self.serialDevice3Baudrate = 9600
        self.serialDevice3Timeout= 10
        self.serialDevice3Data = []
        
        self.counter= 1
        
        self.textFile = None
        
        self.valueFloat = 950.15
        self.flagRecieved= 0 
        self.flagThreadAlive = 1
        self.data = []

        self.readSensorsThread = threading.Thread(target=self.readSensors,
                                              args=(), daemon=True) 
        self.readSensorsThreadActive = False

        # set pyqtgraph -> plotWidget (embedded) behavior
        self.nPlotsParos1 = 1
        
        self.plotTabParos1RawParos1.setWindowTitle(' Ambient Pressure Paros1')
        self.plotTabParos1RawParos1.setLabel('bottom', 'Time', units='s')
        self.plotTabParos1RawParos1.addLegend(size=(50,80))
        # self.curvesPlotTabParos1RawParos1 = [self.plotTabParos1RawParos1.plot(pen=(i+1,self.nPlotsParos1), name = 'Amb. Pressure'+str(i)) for i in range(self.nPlotsParos1)]
        self.curvesPlotTabParos1RawParos1 = [self.plotTabParos1RawParos1.plot(pen=(0,255,0), name = 'Amb. Pressure') for i in range(self.nPlotsParos1)]
        

        self.plotTabParos1NetParos1.setWindowTitle(' Ambient Pressure Paros1')
        self.plotTabParos1NetParos1.setLabel('bottom', 'Time', units='s')
        self.curvesPlotTabParos1NetParos1 = [self.plotTabParos1NetParos1.plot(pen=(i,self.nPlotsParos1), name = 'Amb. Pressure'+str(i)) for i in range(self.nPlotsParos1)]
        # self.plotTabParos1NetParos1.setYRange(-0.020, +0.020)
        self.plotTabParos1NetParos1.showGrid(x = False, y = True, alpha = 0.85)
        
        
        # Queues Thread Safe
        self.rawDataQueue = queue.Queue(16)
        self.convertedDataQueue = queue.Queue(16)

        # Conections signal->slot
        self.cboxTabParos1PortParos1.activated[str].connect(self.changeLblTabParos1PortParos1)  # Works but check if it is correct
        self.sboxTabParos1NPoints.valueChanged.connect(self.changeParos1NPoints)
        self.sboxTabParos1TextSize.valueChanged.connect(self.changeTextSize)
        self.btnTabParos1Start.clicked.connect(self.startTabParos1)
        self.btnTabParos1Stop.clicked.connect(self.stopTabParos1)
        self.btnTabParos1Close.clicked.connect(self.closeTabParos1)

        
        self.statusGuiTabParos1 = "INIT"
        self.updateGuiTabParos1(self.statusGuiTabParos1)
        
    
    def updateGuiTabParos1(self, actualStatusGuiTabParos1):
        print("py: inside updateGuiTabParos1 ",actualStatusGuiTabParos1)
        if actualStatusGuiTabParos1 == "INIT":
            self.btnTabParos1Start.setEnabled(False)
            self.btnTabParos1Stop.setEnabled(True)
            self.btnTabParos1Close.setEnabled(True)
            self.cboxTabParos1PortParos1.setEnabled(True)
            self.sboxTabParos1NPoints.setEnabled(False)
            self.sboxTabParos1TextSize.setEnabled(False)
        if actualStatusGuiTabParos1 == "CONFIG":
            self.btnTabParos1Start.setEnabled(True)
            self.btnTabParos1Stop.setEnabled(True)
            self.btnTabParos1Close.setEnabled(True)
            self.cboxTabParos1PortParos1.setEnabled(True)
            self.sboxTabParos1NPoints.setEnabled(True)
            self.sboxTabParos1TextSize.setEnabled(False)
        if actualStatusGuiTabParos1 == "READY":
            self.btnTabParos1Start.setEnabled(True)
            self.btnTabParos1Stop.setEnabled(True)
            self.btnTabParos1Close.setEnabled(True)
            self.cboxTabParos1PortParos1.setEnabled(True)
            self.sboxTabParos1NPoints.setEnabled(True)
            self.sboxTabParos1TextSize.setEnabled(True)
        if actualStatusGuiTabParos1 == "MEASURING":
            self.btnTabParos1Start.setEnabled(False)
            self.btnTabParos1Stop.setEnabled(True)
            self.btnTabParos1Close.setEnabled(True)
            self.cboxTabParos1PortParos1.setEnabled(False)
            self.sboxTabParos1NPoints.setEnabled(False)
            self.sboxTabParos1TextSize.setEnabled(True) 


    
    def connectSerialPort (self, userCOM, userBaudrate, userTimeout):
        """
        userTimeout should be at least 1 second
        """
        try:
            ser = serial.Serial(userCOM, userBaudrate, timeout = userTimeout)
            ser.close()
            ser.open()
            return ser
        except serial.SerialException:
            print("py: Serial Exception " + userCOM + " might probably opened by another app")
            return None

            
    def changeLblTabParos1PortParos1(self):
        self.serialDevice1Port= self.cboxTabParos1PortParos1.currentText()
        if self.serialDevice1Port == "Select COM":
            self.lblTabParos1PortSelected.setText("No COM was selected...")
        else:
            self.lblTabParos1PortSelected.setText(self.serialDevice1Port + " will be used for ")
            self.statusGuiTabParos1 = "CONFIG"
            self.updateGuiTabParos1(self.statusGuiTabParos1)
    
  
    def changeTextSize (self, textSizeValue):
        if textSizeValue == None:
            textSize = self.sboxTabParos1TextSize.value()
        else:
            textSize = textSizeValue
        font = QtGui.QFont()
        font.setPointSize(int(textSize))
        self.lblTabParos1ActualValue.setFont(font)
        self.lblTabParos_mbar.setFont(font)
    
    
    def changeParos1NPoints(self, Npoints):
        if Npoints == None:
            self.paros1NPoints = self.sboxTabParos1NPoints.value()
        else:
            self.paros1NPoints  = Npoints
        self.lblTabParos1NPointsSelected.setText(str(self.paros1NPoints) + " samples will be used in the graph")
        
        self.plotTabParos1NetParos1.setXRange(0, self.paros1NPoints + 1 )
        self.plotTabParos1NetParos1.setYRange(-0.020, +0.020)
        
        self.statusGuiTabParos1 = "READY"
        self.updateGuiTabParos1(self.statusGuiTabParos1)

        
    def startTabParos1 (self):
        # print("py: inside starTabParos1")
        self.btnTabParos1Start.setEnabled(False)
        index = 0
        newConnection = self.connectSerialPort(self.serialDevice1Port,self.serialDevice1Baudrate, self.serialDevice1Timeout)
        if (newConnection != None):
            self.openedSerialPorts.append(newConnection)
            # Only for the Paros1
            self.initParos1(self.openedSerialPorts[0])
            index += 1
            
            startTime = strftime("%Y-%m-%dd_%H_%M_%S", localtime() )
            comentario = self.lineTabParos1Comment.text()
            
            self.textFile = open("DataParos" + comentario + startTime  +".txt", "w")

        else:
            print("-------------CHECK WARNING MESSAGE---------------")
            self.__showArchivoWarning("Error Message -> details...")
            print("-------------CHECK WARNING MESSAGE---------------")
            
            
        # newConnection = self.connectSerialPort(self.serialDevice2Port,self.serialDevice2Baudrate, self.serialDevice2Timeout)
        # if (newConnection != None):
            # self.openedSerialPorts.append(newConnection)
            # print ("\n newConnection stablished ",self.openedSerialPorts[index].name)    

            # value = self.openedSerialPorts[index].readline()
            # print ("\nThe received value is ", value)    
            # index += 1
        # else:
            # self.__showArchivoWarning(self.serialDevice2Port)
            
        
        # newConnection = self.connectSerialPort(self.serialDevice3Port,self.serialDevice3Baudrate, self.serialDevice3Timeout)
        # if (newConnection != None):
            # self.openedSerialPorts.append(newConnection)
            # print ("\n newConnection stablished ",self.openedSerialPorts[index].name)    

            # value = self.openedSerialPorts[index].readline()
            # print ("\nThe received value is ", value)    
            # index += 1
        # else:
            # self.__showArchivoWarning(self.serialDevice2Port)

        print("py: len(self.openedSerialPorts) ", len(self.openedSerialPorts))
        
        self.statusGuiTabParos1 = "MEASURING"
        self.updateGuiTabParos1(self.statusGuiTabParos1)
        
        self.readSensorsThreadActive = True
        self.readSensorsThread.start()
        # print("py: exit starTabParos1")
    
    def initParos1(self, connectionParos1):
        cleanCode = "*0100VR" + '\r\n'
        connectionParos1.write(bytes(cleanCode, 'UTF-8'))     
        connectionParos1.close()
        # print ("py: close COM Paros1, cleans the buffer")
        sleep(0.5)
       
        connectionParos1.open()
        # writeBurstCode = "*0100P4" + '\r\n'
        # connectionParos1.write(bytes(writeBurstCode, 'UTF-8'))
        print ("py: open COM Paros1 again")
        # value = connectionParos1.readline()
        # print ("\nThe received value is ", value)    

        
    def stopTabParos1 (self):
        self.readSensorsThreadActive = False
                 
        # # -------- To do: Debug Error ---------
        # # py: COM10 is closed
        # # Exception in thread Thread-3:
        # # Traceback (most recent call last):
        # # File "C:\Users\escalada\Anaconda3\envs\py34_qtGRAPH5L\lib\threading.py", line 911, in _bootstrap_inner
        # # self.run()
        # # File "C:\Users\escalada\Anaconda3\envs\py34_qtGRAPH5L\lib\threading.py", line 859, in run
        # # self._target(*self._args, **self._kwargs)
        # # File "mainPressureSensors.py", line 290, in readSensors
        # # flag = self.readArduino2Mthd(connection)
        # # File "mainPressureSensors.py", line 327, in readArduino2Mthd
        # # value = ser.readline() # a veces  recibo vacio CHECK
        # # File "C:\Users\escalada\Anaconda3\envs\py34_qtGRAPH5L\lib\site-packages\serial\serialwin32.py", line 252, in read
        # # raise SerialException('call to ClearCommError failed')
        # # serial.serialutil.SerialException: call to ClearCommError failed
                
        sleep(0.5) 
        
        # if SerialValvPulsos.isOpen():
            # cmd = "STOP" + '\r\n'
            # SerialValvPulsos.write(bytes(cmd, 'UTF-8'))
            # SerialValvPulsos.close()
            # print("\n\tpyCierro el puerto")
        
        for connection in self.openedSerialPorts:
                connection.close()
                print("py: "+ connection.name + " is closed")
                      
        if self.textFile != None:
            self.textFile.close()
        
        self.statusGuiTabParos1 = "INIT"
        self.updateGuiTabParos1(self.statusGuiTabParos1)
        
        # it will nice to be able to START again 
        # clear self.openedSerialPorts
        print("py: STOP. Bye!")
        sys.exit()
    
    def closeTabParos1 (self):
        # print("py: inside closeTabParos1 first STOP and CLOSE the opened ports")
        self.stopTabParos1()
        print("py: Bye!")
        sys.exit()
    
    def readSensors(self):
        # print("py: readSensorsThread ->  About enter the for LOOP")
        flagAllreadingsOK = []    
        while self.readSensorsThreadActive:
            # print ("py: opened Serial Ports", self.openedSerialPorts)
            # print ("py: length opened Serial Ports", len(self.openedSerialPorts))
            
            for connection in self.openedSerialPorts:
                
                # I think we should hace one readMethod and inside of it distinguish Paros or Arduino
                if (connection.name == self.serialDevice1Port):
                    
                    flag = self.readParos1Mthd(connection)
                    print("py: flag Paros1 value: ", flag)
                    flagAllreadingsOK.append(flag)
                else:
                    print("py: ELSE " +  connection.name)
                    
                    flag = self.readArduino2Mthd(connection)
                    print("\tpy:" +  connection.name + " flag value: ", flag)
                    flagAllreadingsOK.append(flag)
                
            if (True): # if (all(flagAllreadingsOK)): # if (flag1 and flag2):
                print("py: emit signal to drawPlot\n")
                self.newTimeData.emit(True)
        print("py: readSensorsThread -> finished")  
    
    
    def readParos1Mthd(self, connectionPort):
        # print("py: inside readParos1Mthd") 
        # print("py: the name ", connectionPort.name)
        writeBurstCode = "*0100P3" + '\r\n'
        connectionPort.write(bytes(writeBurstCode, 'UTF-8'))
        
        value = connectionPort.readline() # a veces  recibo vacio CHECK
        # print ("\nThe received value is ", value)
        valueStr = value.decode('ascii').strip('\r\n')
        # valueStrOK = valueStr.strip("*0001")
        # valueStrOK = valueStr.replace('*0001','')
        valueStrOK = valueStr[5:]
        # print ("\nThe received value is ", valueStrOK)

        #print ("The STR is ", valueStrOK)
        if isConvertibleTofloat(valueStrOK):
            valueFloat= float (valueStrOK)
            print ("py: Paros1 data received is convertible to float and is ", valueFloat)
            # print ("\n")
            if (connectionPort.name == self.serialDevice1Port):
                
                self.serialDevice1Data.append(valueFloat)
                
                self.lblTabParos1ActualValue.setText(str(valueFloat))
                actualTime = strftime("%Y-%m-%d %H:%M:%S", localtime())
                self.textFile.write(str(actualTime) +';'+ valueStrOK +'\n')
                print ("py: writting file !!!")
                
                # self.convertedDataQueue.put(data)
            
                if (len(self.serialDevice1Data) > self.paros1NPoints):
                    self.serialDevice1Data.pop(0)
                
                return (True)
        else:
            return (False)
    
    def readArduino2Mthd(self, ser):
        value = ser.readline() # a veces  recibo vacio CHECK
        # print ("Th1: El valor recibido es:", value)
        valueStr= value.decode('ascii').strip('\r\n')
        valueStrList = re.findall(r"[-+]?\d*\.\d+|\d+", valueStr) # https://stackoverflow.com/questions/4703390/how-to-extract-a-floating-number-from-a-string
        if len(valueStrList) > 0:
            valueStrOK = valueStrList[0]
            
            if isConvertibleTofloat(valueStrOK) and len(valueStrOK)>0:
                valueFloat = float (valueStrOK)
                print (ser.name + " Arduino: is convertible to float and is ", valueFloat)
                
                if (ser.name == self.serialDevice2Port):
                    self.serialDevice2Data.append(valueFloat)
                    # self.serialDevice2Data.append(valueFloat+float(np.random.uniform(0.01, 0.09, size=1)))
                    if (len(self.serialDevice2Data) > self.paros1NPoints):
                        self.serialDevice2Data.pop(0)
                
                if (ser.name == self.serialDevice3Port):
                    self.serialDevice3Data.append(valueFloat)
                    if (len(self.serialDevice3Data) > self.paros1NPoints):
                        self.serialDevice3Data.pop(0)
                
                return (True)
        else:
            return (False)

    def readSensor(self):
 
        while self.flagThreadAlive:
            print("Th1: Entro en el While Thread")
            #value = ser.read(bytecount)
            value = self.ser.readline()
            print ("Th1: El valor recibido es:", value)
            valueStr= value.decode('ascii').strip('\r\n')
            valueStrList = re.findall(r"[-+]?\d*\.\d+|\d+", valueStr) # https://stackoverflow.com/questions/4703390/how-to-extract-a-floating-number-from-a-string
            valueStrOK = valueStrList[0]
           
            #valueStrOK= str(float(np.random.uniform(1022.5, 10024.3, size=1)))
            
            if isConvertibleTofloat(valueStrOK) and len(valueStrOK)>0:
                self.valueFloat = float (valueStrOK)
                self.flagRecieved = 1
                self.newTimeData.emit(True)
                print ("Th1: El valor flotante es:", self.valueFloat)
            #   sleep(1) # 1 second
        print ('Closing ', self.ser.name) 
        self.ser.close()
    
    def __showArchivoWarning(self, msgDetails):
        ''' Creates a un mensaje de error 
        '''
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.setText("The serial port selected could not be open!")
        msg.setWindowTitle("Error!!!")
        msg.setInformativeText("You may probably need to reboot.")
        msg.setDetailedText("Further error message details:\n {}".format(msgDetails))
        msg.setStandardButtons(QtWidgets.QMessageBox.Close)
        return msg.exec_()
    
    def drawPlot(self):
        ''' Updates the embedded plot
        '''
        self.plotTabParos1RawParos1.setWindowTitle('++ Ambient Pressure Paros1 ++ ')
        self.plotTabParos1RawParos1.setLabel('bottom', '++ Samples ++', units='-')
                    
        # print("py: serialDevice1DataData ",(self.serialDevice1Data))
        self.curvesPlotTabParos1RawParos1[0].setData(self.serialDevice1Data)
        # self.curvesPlotTabParos1RawParos1[1].setData([element+0.2 for element in self.serialDevice1Data])
        # self.curvesPlotTabParos1RawParos1[2].setData([element-0.2 for element in self.serialDevice1Data])

        self.counter = self.counter + 1
        self.plotTabParos1NetParos1.setWindowTitle('++ Ambient Pressure Paros1 ++ ')
        self.plotTabParos1NetParos1.setLabel('bottom', '++ Net Samples ++ '+ str (self.counter) , units='-')
        netData = [(x - self.serialDevice1Data[0]) for x in self.serialDevice1Data]
        # print("py: NetData ",netData)
        self.curvesPlotTabParos1NetParos1[0].setData(netData)
        
        
def isConvertibleTofloat(value):
    try:
        float(value)
        return True
    except:
        return False        

def searchSerialPorts():
    """ Lists serial port names
        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result
        
if __name__ == "__main__":
    
    
    print("\nWelcome!!! We are searching for the connected serial ports.")
    print("This may take a while...\n")

    serialPorts= searchSerialPorts()
    print ("\nThe connected serial ports are: \n",serialPorts)
    
    app = QtWidgets.QApplication(sys.argv)
    form = PrSensors()
    form.newTimeData.connect(form.drawPlot)     # Para investigar: con una modularización mejor
                                                # se podría hacer internamente esta conexión.
    form.show()
    try:
        sys.exit(app.exec_())
    except SystemExit as e:
        del app, form
        print("The app was close with this code: " + str(e))