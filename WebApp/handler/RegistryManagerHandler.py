
from WebAppDIRAC.Lib.WebHandler import WebHandler, WebSocketHandler, WErr, WOK, asyncGen
from DIRAC.Core.DISET.RPCClient import RPCClient
from DIRAC import gConfig, S_OK, S_ERROR, gLogger
from DIRAC.Core.Utilities import Time, List, DictCache
from DIRAC.Core.Utilities.CFG import CFG
from DIRAC.ConfigurationSystem.private.Modificator import Modificator

import json
import types
import time

class RegistryManagerHandler(WebSocketHandler):

  AUTH_PROPS = "authenticated"

  def on_open(self):
    self.__configData = {}

  @asyncGen
  def on_message(self, msg):

    self.log.info("RECEIVED %s" % msg)
    try:
      params = json.loads(msg)
    except:
      gLogger.exception("No op defined")

    res = False
    if params["op"] == "init":
      res = self.__getRemoteConfiguration("init")
    elif params["op"] == "getData":
      res = self.__getData(params)
    elif params["op"] == "deleteItem":
      res = self.__deleteItem(params)
    elif params["op"] == "addItem":
      res = self.__addItem(params)
    elif params["op"] == "editItem":
      res = self.__editItem(params)
    elif params["op"] == "resetConfiguration":
      res = self.__getRemoteConfiguration("resetConfiguration")
      
    if res:
      self.write_message(res)

  def __getRemoteConfiguration(self, funcName):
    rpcClient = RPCClient(gConfig.getValue("/DIRAC/Configuration/MasterServer", "Configuration/Server"))
    modCfg = Modificator(rpcClient)
    retVal = modCfg.loadFromRemote()

    if not retVal[ 'OK' ]:
      return {"success":0, "op":"getSubnodes", "message":"The configuration cannot be read from the remote !"}

    self.__configData[ 'cfgData' ] = modCfg
    self.__configData[ 'strCfgData' ] = str(modCfg)
    
    version = str(modCfg.getCFG()["DIRAC"]["Configuration"]["Version"])
    configName = str(modCfg.getCFG()["DIRAC"]["Configuration"]["Name"])
    return {"success":1, "op":funcName, "version":version, "name":configName}
  
  def __getData(self, params):
    data = []
    if params["type"] == "users":
      
      sectionPath = "/Registry/Users"
      sectionCfg = self.getSectionCfg(sectionPath)
      
      for username in sectionCfg.listAll():
        
        item = {}
        item["name"] = username
        props = sectionCfg[username]
        
        item["dn"] = self.getIfExists("DN", props)
        item["ca"] = self.getIfExists("CA", props)
        item["email"] = self.getIfExists("Email", props)
        
        data.append(item)
      
    elif params["type"] == "groups":
      sectionPath = "/Registry/Groups"
      sectionCfg = self.getSectionCfg(sectionPath)
      
      for group in sectionCfg.listAll():
        item = {}
        item["name"] = group
        props = sectionCfg[group]
        
        item["users"] = self.getIfExists("Users", props)
        item["properties"] = self.getIfExists("Properties", props)
        item["vomsrole"] = self.getIfExists("VOMSRole", props)
        
        item["autouploadproxy"] = self.getIfExists("AutoUploadProxy", props)
        item["autouploadpilotproxy"] = self.getIfExists("AutoUploadPilotProxy", props)
        item["autoaddvoms"] = self.getIfExists("AutoAddVOMS", props)
        item["jobshare"] = self.getIfExists("JobShare", props)
        
        data.append(item)
        
    elif params["type"] == "hosts":
      sectionPath = "/Registry/Hosts"
      sectionCfg = self.getSectionCfg(sectionPath)
      
      for host in sectionCfg.listAll():
        item = {}
        item["name"] = host
        props = sectionCfg[host]
        
        item["dn"] = self.getIfExists("DN", props)
        item["properties"] = self.getIfExists("Properties", props)
        
        data.append(item)
    
    return {"op":"getData", "success":1, "type": params["type"], "data": data}
  
  def getSectionCfg(self, sectionPath):
    sectionCfg = None
    try:
      sectionCfg = self.__configData[ 'cfgData' ].getCFG()
      for section in [ section for section in sectionPath.split("/") if not section.strip() == "" ]:
        sectionCfg = sectionCfg[ section ]
    except Exception, v:
      return False
    return sectionCfg
  
  def getIfExists(self, elem, propsList):
    if elem in propsList.listAll():
      return propsList[elem]
    else:
      return ""
    
  def __addItem(self, params):
   
    sectionPath = "/Registry/"
    configText = ""
    if params["type"] == "users":
      
      sectionPath = sectionPath + "Users"
      if params["dn"].strip() != "":
        configText = "DN = " + params["dn"].strip() + "\n"
        
      if params["ca"].strip() != "":
        configText = configText + "CA = " + params["ca"].strip() + "\n"
        
      if params["email"].strip() != "":
        configText = configText + "Email = " + params["email"].strip()
        
    elif params["type"] == "groups":
        
      sectionPath = sectionPath + "Groups"
      if params["users"].strip() != "":
        configText = "Users = " + params["users"].strip() + "\n"
        
      if params["properties"].strip() != "":
        configText = configText + "Properties = " + params["properties"].strip() + "\n"
      
      if str(params["jobshare"]).strip() != "":
        configText = configText + "JobShare = " + str(params["jobshare"]) + "\n"
      
      if params["autouploadproxy"].strip() != "":
        configText = configText + "AutoUploadProxy = " + params["autouploadproxy"].strip() + "\n"
      
      if params["autouploadpilotproxy"].strip() != "":
        configText = configText + "AutoUploadPilotProxy = " + params["autouploadpilotproxy"].strip() + "\n"
      
      if params["autoaddvoms"].strip() != "":
        configText = configText + "AutoAddVOMS = " + params["autoaddvoms"].strip()
      
    elif params["type"] == "hosts":
      
      sectionPath = sectionPath + "Hosts"
      if params["dn"].strip() != "":
        configText = "DN = " + params["dn"].strip() + "\n"
        
      if params["properties"].strip() != "":
        configText = configText + "Properties = " + params["properties"].strip()
    
    sectionPath = sectionPath + "/" + params["name"]
    
    if self.__configData[ 'cfgData' ].createSection(sectionPath):
      cfgData = self.__configData[ 'cfgData' ].getCFG()
      newCFG = CFG()
      newCFG.loadFromBuffer(configText)
      self.__configData[ 'cfgData' ].mergeSectionFromCFG(sectionPath, newCFG)
      return {"success":1, "op": "addItem"}
    else:
      return {"success":0, "op":"addItem", "message":"Section can't be created. It already exists?"}
      
  def __editItem(self, params):
    
    ret = self.__deleteItem(params)
    if ret["success"] == 1:
      ret = self.__addItem(params)
      return ret
    return ret
    
    sectionPath = "/Registry/"
    configText = ""
    if params["type"] == "users":
      
      sectionPath = sectionPath + "Users"
      if params["dn"].strip() != "":
        configText = "DN = " + params["dn"].strip() + "\n"
        
      if params["ca"].strip() != "":
        configText = configText + "CA = " + params["ca"].strip() + "\n"
        
      if params["email"].strip() != "":
        configText = configText + "Email = " + params["email"].strip()
        
    elif params["type"] == "groups":
        
      sectionPath = sectionPath + "Groups"
      if params["users"].strip() != "":
        configText = "Users = " + params["users"].strip() + "\n"
        
      if params["properties"].strip() != "":
        configText = configText + "Properties = " + params["properties"].strip() + "\n"
      
      if str(params["jobshare"]).strip() != "":
        configText = configText + "JobShare = " + str(params["jobshare"]) + "\n"
      
      if params["autouploadproxy"].strip() != "":
        configText = configText + "AutoUploadProxy = " + params["autouploadproxy"].strip() + "\n"
      
      if params["autouploadpilotproxy"].strip() != "":
        configText = configText + "AutoUploadPilotProxy = " + params["autouploadpilotproxy"].strip() + "\n"
      
      if params["autoaddvoms"].strip() != "":
        configText = configText + "AutoAddVOMS = " + params["autoaddvoms"].strip()
      
    elif params["type"] == "hosts":
      
      sectionPath = sectionPath + "Hosts"
      if params["dn"].strip() != "":
        configText = "DN = " + params["dn"].strip() + "\n"
        
      if params["properties"].strip() != "":
        configText = configText + "Properties = " + params["properties"].strip()
    
    sectionPath = sectionPath + "/" + params["name"]
    
#   deleting the options underneath 
    sectionCfg = self.getSectionCfg(sectionPath)
      
    for opt in sectionCfg.listAll():
      print "deleting "+opt+"\n"
      self.__configData[ 'cfgData' ].removeOption(sectionPath+"/"+opt)
    
    cfgData = self.__configData[ 'cfgData' ].getCFG()
    newCFG = CFG()
    newCFG.loadFromBuffer(configText)
    self.__configData[ 'cfgData' ].mergeSectionFromCFG(sectionPath, newCFG)
    return {"success":1, "op": "editItem"}  
        
    
  
  def __deleteItem(self, params):
    sectionPath = "/Registry/"
    
    if params["type"] == "users":
      sectionPath = sectionPath + "Users"
    elif params["type"] == "groups":
      sectionPath = sectionPath + "Groups"
    elif params["type"] == "hosts":
      sectionPath = sectionPath + "Hosts"
    
    sectionPath = sectionPath + "/" + params["name"]
    if self.__configData[ 'cfgData' ].removeOption(sectionPath) or self.__configData[ 'cfgData' ].removeSection(sectionPath):
      return {"success":1, "op":"deleteItem"}
    else:
      return {"success":0, "op":"deleteItem", "message":"Entity doesn't exist"}
  
