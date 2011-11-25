#!/usr/bin/env python
# encoding: utf-8
"""
__init__.py

Created by Danny Dannaher on 2010-11-24.
"""

###############################################################################
# The following code was added during the installation process to ensure       
# that all of the necessary modules are imported correctly. Do not modify.     

import sys, os, tempfile, re

vida_framework_modules = []
for module in sys.modules:
  if module[:2] == 'vf':
    vida_framework_modules.append(module)

for module in vida_framework_modules:
  import_cmd = 'from ' + module + ' import *'
  exec(import_cmd)

###############################################################################
# GUI setup

from PyQt4.QtCore import *
from PyQt4.QtGui  import *
from PyQt4        import uic
from openeye.oechem import *

import socket, getpass

serverData = ( '10.11.34.26', 1111 )

class JobControl2Widget(QWidget):
    """docstring for JobCrontrolWidget"""
    uifile = os.path.join(os.path.split(os.path.abspath(__file__))[0], "jobcontrol2.ui")
    #uifile = "/Users/dannydannaher/Desktop/client-server/jobcontrol/jobcontrol.ui"
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.widget = uic.loadUi(self.uifile)
        self.layout.addWidget(self.widget)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        # load the UI file and put it into a layout
        ui = self.ui = WrapPyQt(self.widget)
        self.thread = Worker()
        self.compeleteDict = {}
        self.latest = ""
        self.serverData = serverData
        self.setWindowTitle("Job Control")
        ui.doneTable.setColumnWidth(0, 70)
        ui.doneTable.setColumnWidth(1, 60)
        ui.pendingTable.hide()
        
        shortcut = QShortcut(QKeySequence("F2"), ui.doneTable)
        
        self.connect(shortcut, SIGNAL("activated()"), self.rename)
        self.connect(ui.renameBtn, SIGNAL("clicked()"), self.rename)
        self.connect(ui.retrieveBtn, SIGNAL("clicked()"), self.openJob)
        self.connect(ui.deleteBtn, SIGNAL("clicked()"), self.delete)
        self.connect(ui.connectBtn, SIGNAL("clicked()"), self.connected)
        self.connect(self, SIGNAL("runThread()"), self.thread.start)
        self.connect(self.thread, SIGNAL("updateComp(QString)"), self.updateComplete)
        self.connect(self.thread, SIGNAL("updatePend(QString)"), self.updatePend)
        self.connect(self.thread, SIGNAL("discon()"), self.disconnected)
        self.connect(self, SIGNAL("discon()"), self.disconnected)
        
        try:
            client = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
            client.connect( serverData )
            user = 'Name!:!'+ getpass.getuser()
            command = "command!:!startup"
            data = user + 'ATECDELIMITED' + command
            # Send some messages:
            client.sendall(data)
            # Close the connection
            client.close()
            ui.connectBtn.setEnabled(False)
            self.emit(SIGNAL("runThread()"))
        except Exception, e:
            self.emit(SIGNAL("discon()"), self.disconnected)
            PromptError("Apparently you are working off-line - remote services won't work")     
        
    
    
    def toggleBtn(self, enable):
        ui = self.ui
        ui.renameBtn.setEnabled(enable)
        ui.deleteBtn.setEnabled(enable)
        ui.retrieveBtn.setEnabled(enable)
        ui.connectBtn.setChecked(not enable)
        if enable:
            ui.connectBtn.setText(QString("Connected"))
            ui.connectBtn.setEnabled(not enable)
        else:
            ui.connectBtn.setText(QString("Disconnected"))
            ui.connectBtn.setEnabled(not enable)
    
            
    def connected(self):
        try:
            client = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
            client.connect ( self.serverData )
            client.close()
            self.toggleBtn(True)
            self.emit(SIGNAL("runThread()"))
        except Exception, e:
            self.toggleBtn(False)
            PromptError("Apparently you are working off-line - remote services won't work")
        
    
    def disconnected(self):
        self.toggleBtn(False)
        count = self.ui.doneTable.rowCount()
        while count != 0:
            self.ui.doneTable.removeRow(count - 1)
            count = self.ui.doneTable.rowCount()
        
    
    def rename(self):
        ui = self.ui
        dTable = ui.doneTable
        reg = re.compile("\W")
        try:
            index = dTable.currentRow()
            if index == -1:
                raise ValueError()
            fileName = str(dTable.item(index, 0).text())
            newName = str(PromptString("Enter the new name:", fileName, True, True))
            if newName != "" and newName != "Prompt Canceled":
                try:
                    client = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
                    client.connect ( self.serverData )
                    newName.replace(" ", "")
                    if ".sdf" in newName:
                        newName.replace(".sdf", "")
                    newName = reg.sub("", newName)
                    newName += ".sdf"
                    files = "oldname!:!" + fileName + "ATECDELIMITEDnewname!:!" + newName 
                    msg = "command!:!renameATECDELIMITED"+ files + "ATECDELIMITEDName!:!" + getpass.getuser() +  "ATECDELIMITEDstopsignal!:!STOPWARLINKSTOP"
                    client.sendall(msg)
                    client.close()
                    dTable.item(index, 0).setText(QString(newName))
                    dTable.resizeColumnsToContents()
                    dTable.resizeRowsToContents()
                except Exception, e:
                    pass
        except ValueError:
            PromptError("Select a file to rename")
        
        
            
    def updatePend(self, newString):
        try:
            dTable = self.ui.doneTable
            pTable = self.ui.pendingTable
            
            tmp = str(newString).split("ATECDELIMITED")
            jobNotDone = tmp[1].split("!WARLINK!")
            jobNotDone.pop()
            
            count = dTable.rowCount()
            while count != 0:
                dTable.removeRow(count - 1)
                count = dTable.rowCount()
                
            count = pTable.rowCount()
            while count != 0:
                pTable.removeRow(count - 1)
                count = pTable.rowCount()
            
            jobList = tmp[0].split("!WARLINK!")
            index = int(jobList.pop())
            for i in range(0, len(jobList)):
                items = jobList[i].split("!:!")
                if items[0] not in jobNotDone:
                    dTable.insertRow(0)
                    dTable.setItem(0,0, QTableWidgetItem(items[0]))
                    dTable.setItem(0,1, QTableWidgetItem(items[1]))
                else:
                    pTable.insertRow(0)
                    pTable.setItem(0,0, QTableWidgetItem(items[0]))
                    pTable.setItem(0,1, QTableWidgetItem(items[1]))
            
            pTable.show()
            pTable.resizeColumnsToContents()
            pTable.resizeRowsToContents()
        except Exception, e:
            pass
        
    
                
    def updateComplete(self, newString):
        try:
            dTable = self.ui.doneTable
            pTable = self.ui.pendingTable
            count = dTable.rowCount()
            while count != 0:
                dTable.removeRow(count - 1)
                count = dTable.rowCount()
                
            complete = str(newString).split("!WARLINK!")
            jobNotDone = int(complete.pop())
            if jobNotDone == 0:
                pTable.hide()
                for i in range(0, (len(complete) - (jobNotDone))):
                    items = complete[i].split("!:!")
                    dTable.insertRow(0)
                    dTable.setItem(0,0, QTableWidgetItem(items[0]))
                    dTable.setItem(0,1, QTableWidgetItem(items[1]))
            else:
                for i in range(0, (len(complete) - (jobNotDone))):
                    items = complete[i].split("!:!")
                    dTable.insertRow(0)
                    dTable.setItem(0,0, QTableWidgetItem(items[0]))
                    dTable.setItem(0,1, QTableWidgetItem(items[1]))
                    
                count = pTable.rowCount()
                while count != 0:
                    pTable.removeRow(count - 1)
                    count = pTable.rowCount()
                for i in range((len(complete) - jobNotDone), len(complete)):
                    items = complete[i].split("!:!")
                    pTable.insertRow(0)
                    pTable.setItem(0,0, QTableWidgetItem(items[0]))
                    pTable.setItem(0,1, QTableWidgetItem(items[1]))
                pTable.show()
            dTable.resizeColumnsToContents()
            dTable.resizeRowsToContents()
            pTable.resizeColumnsToContents()
            pTable.resizeRowsToContents()
        except Exception, e:
            pass
        
    
            
    def delete(self):
        """docstring for delete"""
        try:
            client = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
            client.connect ( self.serverData )
            # client.connect ( ( 'localhost', 2828 ) )
        except:
            PromptError("Can't connect to the server")
        try:
            dTable = self.ui.doneTable
            index = dTable.currentRow()
            fileName = str(dTable.item(index, 0).text())
            msg = "command!:!deletejobATECDELIMITEDfilename!:!" + fileName + "ATECDELIMITEDName!:!" + getpass.getuser()
        except:
            PromptError('please select a file to delete')
            client.close()
        try:
            client.send(msg)
            self.ui.doneTable.removeRow(index)
            if  dTable.countRow() == 0:
                self.ui.retrieveBtn.setEnabled(False)
                self.ui.deleteBtn.setEnabled(False)
            client.close()
        except:
            pass
    
    
    def openJob(self):
        """docstring for fname"""
        try:
            client = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
            client.connect ( self.serverData )
            # client.connect ( ( 'localhost', 2728 ) )
        except:
            PromptError("Can't connect to the server")
        try:	
            dTable = self.ui.doneTable
            index = dTable.currentRow()
            fileName = str(dTable.item(index, 0).text())
            msg = "command!:!retrievejobATECDELIMITEDfilename!:!" + fileName + "ATECDELIMITEDName!:!" + getpass.getuser() +  "ATECDELIMITEDstopsignal!:!STOPWARLINKSTOP"
        except:
            PromptError('please select a file to open')
            client.close()
        try:
            client.send(msg)
            data = ""
            while 1:
                if "STOPWARLINKSTOP" in data: 
                    data = data.replace("STOPWARLINKSTOP", "")
                    break
                tmp = client.recv(1024)
                if not tmp:
                    break
                else:
                    data += tmp
            if data == "NO":
                PromptError("The file you're trying to open, can not be opened \nSomething have gone wrong!")
                dTable.removeRow(index)
            else:
                if not os.path.exists("C:\\VIDATMP\\"):
                    os.mkdir("C:\\VIDATMP\\")
                tempFile = open("C:\\VIDATMP\\" + fileName, 'w')
                tempFile.write(data)
                tempFile.close()
                
                Open("C:\\VIDATMP\\" + fileName)
                command = "C:\\VIDATMP\\" + fileName
                os.remove(command)
        except:
            pass

        
###############################################################################
# Thread worker class

class Worker(QThread):
    """docstring for Worker"""
    def __init__(self, parent = None):
        QThread.__init__(self, parent)
        self.compeleteDict = {}
        self.pendingDict = {}
        
    def run(self):
        """docstring for connect"""
        try:
            client = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )
            client.connect ( ( '10.11.34.26', 1111 ) )
            msg = "Name!:!" + getpass.getuser() + "ATECDELIMITEDcommand!:!jobcontrol2" + "ATECDELIMITEDstopsignal!:!STOPWARLINKSTOP"
            client.send(msg)
            while True:
                data = ""
                while 1:
                    if "STOPWARLINKSTOP" in data: 
                        data = data.replace("STOPWARLINKSTOP", "")
                        break
                    tmp = client.recv(1024)
                    if not tmp:
                        break
                    else:
                        data += tmp
                
                if data == "":
                    self.emit(SIGNAL("discon()"))
                    break
                elif data == "NO":
                    pass
                else:
                    if "ATECDELIMITED" in data:
                        complete = QString(data)
                        self.emit(SIGNAL("updatePend(QString)"), complete)
                    else:
                        complete = QString(data)
                        self.emit(SIGNAL("updateComp(QString)"), complete)
        except socket.error:
            PromptError("Can't connect to the server")
            


#extension specific code		
widget = JobControl2Widget()
dock   = QDockWidget("JobControl")
dock.setObjectName("JobControl")
dock.setWidget(widget)
dock.layout().setContentsMargins(0,0,0,0)

dock.hide

for tw in QApplication.topLevelWidgets():
    if tw.inherits("QMainWindow"):
        tw.addDockWidget(Qt.RightDockWidgetArea, dock)
        break

menu_name = "Remote Services"
if not MenuExists(menu_name):
    menu_name = MenuAddSubmenu("MenuBar", menu_name, "Remote Services", "", False)

command = """
WindowVisibleSet("JobControl",True)
"""
MenuAddButton(menu_name, "Job Control", command)
WindowVisibleSet("JobControl",True)

