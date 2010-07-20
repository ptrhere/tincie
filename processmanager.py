from twisted.internet import reactor 
from twisted.web import static, server 
from twisted.web.resource import Resource 
import subprocess
import time
import random

import os 
from os import path
import socket
import uuid
import pickle 
import string

import stat

class Host():
  def __init__(self):
    self.pubkey = ""
    self.privkey = ""
    self.port = None
    self.address = None
 
  def printable(self):
    return "Host:"+self.name

  def getName(self):
    return self.name


  def generate(self):
    len = 10 
    self.name = ''.join(random.choice(string.letters) for i in xrange(len))
    proc = subprocess.Popen(['openssl genrsa'], 
                        shell=True, 
                        stdout=subprocess.PIPE,
                        )
    self.privkey = proc.communicate()[0]
    proc = subprocess.Popen(['openssl rsa -pubout'], 
                        shell=True, 
			stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        )
    self.pubkey = proc.communicate(self.privkey)[0]
    self.localip = str(192) + "." + str(168) + "." + str(23) + "." +  str(random.randint(1,253)) 
    self.netmask = "255.255.255.0"
    
def pickleConfigFile(key):
  return path.abspath(path.join("/tmp", key, "config.pickle"))


class TincConf():

  def __init__(self):
    self.basedir="/tmp/"

  def printable(self):
    return "TincConf:"+self.key 


  def generateServerConfig(self):
    self.key='tinc'+str(uuid.uuid1());
    self.hosts = {}

    if os.path.exists(self.getBaseConfigDir()): 
      raise "key already in use, cannot generate config with same key"

    self.setupBaseConfigDir()

    host = self.addTincHost("alpha")
    host.port = 1025 + int( random.random() * 4000)
    host.address = socket.gethostname()


    pickle.dump(self, file(pickleConfigFile(self.key),'w'))

  def getBaseConfigDir(self):
    return path.abspath(path.join(self.basedir, self.key))

  def setupBaseConfigDir(self):
    filename = path.abspath(path.join(self.basedir, self.key))
    os.mkdir(filename)
    filename = self.confDir()
    os.mkdir(filename)


  def pidFile(self):
    return path.abspath(path.join(self.basedir, "pid"+self.key))


  def writeTincConfig(self,index,basepath):

    if not os.path.exists(self.getBaseConfigDir()): 
      raise "configuration not properly initialized, please generate a vpn first"


    filename = path.abspath(path.join(basepath,"tinc.conf"))
    f = open(filename,"w")
    f.write("\nName = " + self.hosts[index].name)
    f.write("\nMode = switch")
    f.write("\nTCPOnly = yes")
    if not index is "alpha": 
      f.write("\nConnectTo = " + self.getServerHost().getName())
    f.close()

    if not index is "alpha":
      filename = path.abspath(path.join(basepath,"tinc-down"))
      f = open(filename,"w")
      f.write("#!/bin/sh\n")
      f.write("ifconfig $INTERFACE down\n")
      f.close()
      statinfo = os.stat(filename)
      statperm = statinfo[0]
      os.chmod(filename,stat.S_IXOTH | stat.S_IXUSR | stat.S_IXGRP | statperm);
      
      filename = path.abspath(path.join(basepath,"tinc-up"))
      f = open(filename,"w")
      f.write("#!/bin/sh\n")
      f.write("ifconfig $INTERFACE %s netmask %s\n" % (self.hosts[index].localip, self.hosts[index].netmask) )
      f.close()
      statinfo = os.stat(filename)
      statperm = statinfo[0]
      os.chmod(filename,stat.S_IXOTH | stat.S_IXUSR | stat.S_IXGRP | statperm);

      filename = path.abspath(path.join(basepath,"runthis.sh"))
      f = open(filename,"w")
      f.write("#!/bin/sh\n")
      f.write("sudo tincd -c . -D" )
      f.close()
      statinfo = os.stat(filename)
      statperm = statinfo[0]
      os.chmod(filename,stat.S_IXOTH | stat.S_IXUSR | stat.S_IXGRP | statperm);

    filename = path.abspath(path.join(basepath,"rsa_key.priv"))

    filename = path.abspath(path.join(basepath,"rsa_key.priv"))
    f = open(filename,"w")
    f.write(self.hosts[index].privkey)
    f.close()

    filename = path.abspath(path.join(basepath,"rsa_key.pub"))
    f = open(filename,"w")
    f.write(self.hosts[index].pubkey)
    f.close()

    filename = path.abspath(path.join(basepath,"hosts"))
    if not os.path.exists(filename):
      os.mkdir(filename)
    
    for key,all in self.hosts.items():
      print "writing tinc host file ", key
      filename = path.abspath(path.join(basepath,"hosts", self.hosts[key].name))
      f = open(filename,"w")
      if(all.address != None):
        f.write("\nAddress = " + str(all.address))
      if(all.port != None):
        f.write("\nPort = " + str(all.port))
      f.write("\n")
      f.write(all.pubkey)
      f.write("\n")
      
      f.close()

  def getKey(self):
    return self.key

  def confDir(self):
    return path.abspath(path.join(self.basedir, self.key, "conf"))

  def writeServerConfig(self):
   print("writing server config")
   return self.writeTincConfig("alpha",self.confDir())

  def getServerHost(self):
    return self.hosts["alpha"]
    
  def addTincHost(self,name = None):
    host = Host()
    host.generate()
    if name is None:
      #do nothing
      host.name = host.name
    else:
      host.name = name
    print( "add host named "+host.getName())
    self.hosts[host.getName()] = host
    pickle.dump(self, file(pickleConfigFile(self.key),'w'))
    self.writeServerConfig()
    return host


    
def readServerConfig(key):
    print("reading server config "+key)
    return pickle.load(file(pickleConfigFile(key),'r'))
    


class CreateVPN(Resource):
    def getChild(self, name, request):
        print ('getChild %s, %s' % (name, request))
        return self

    def __init__(self):
        Resource.__init__(self)

    def render_GET(self, request):
        print('render GET %r' % (request))
        request.setResponseCode(200)
        request.write('')

        print('starting subprocess')

        t = TincConf()
        t.generateServerConfig()
        t.writeServerConfig()

        callstring = './tincd -c '+ t.confDir()+ ' --pidfile '+t.pidFile()
        print callstring

        process = subprocess.Popen(callstring, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process.poll()
        request.write( process.communicate()[0] )
        # it shouldn't return anything if all went well

        request.write("created vpn entry point")
        request.write(t.printable())
        request.write("<br>")
        request.write("create a host: <a href='/addhost?key=%s'> here</a>" % t.getKey())
        request.write("<br>")
        request.write("copy this URL & send it to your peers:")
        request.write("<br>")
        request.write("http://okno.be:18001/addhost?key=%s" % t.getKey())
        request.write("<br>")
        request.write("or list hosts: <a href='/list?key=%s'> here</a>" % t.getKey())
        request.write("<br>")
        return ""


import pprint 

class AddHost(Resource):
    def getChild(self, name, request):
        print ('getChild %s, %s' % (name, request))
        return self

    def __init__(self):
        Resource.__init__(self)

    def render_GET(self, request):
        print('render GET %r' % (request))
        request.setResponseCode(200)
        request.write('')
        key =  request.args['key'][0]

        t = readServerConfig(key);
        newhost=t.addTincHost()

        request.write("created your host")
        request.write(newhost.printable())
        request.write("<br>")

        request.write("created your host: get your tincd <a href='/getconfig?key=%s&host=%s'>config files</a>" % (t.getKey(), newhost.getName() ))
        request.write("<br>")
        request.write("or list hosts: <a href='/list?key=%s'> here</a>" % t.getKey())
        request.write("<br>")


        return ""

import zipfile
import glob, os
import tempfile
def zip_dir(dirpath, zippath):
 fzip = zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED)
 basedir = os.path.dirname(dirpath) + '/' 
 for root, dirs, files in os.walk(dirpath):
   if os.path.basename(root)[0] == '.':
     continue #skip hidden directories        
   dirname = root.replace(basedir, '')
   for f in files:
     if f[-1] == '~' or (f[0] == '.' and f != '.htaccess'):
       #skip backup files and all hidden files except .htaccess
       continue
     fzip.write(root + '/' + f, dirname + '/' + f)
 fzip.close()

class GetConfig(Resource):
    def getChild(self, name, request):
        print ('getChild %s, %s' % (name, request))
        return self

    def __init__(self):
        Resource.__init__(self)

    def render_GET(self, request):
        print('render GET %r' % (request))
        request.setResponseCode(200)
        request.setHeader("Content-Type","application/octet-stream")
        request.setHeader("Content-disposition","attachment; filename=tincd_config.zip"); 
        #request.setHeader("Content-Transfer-Encoding","binary");

        key =  request.args['key'][0]
        hostname =  request.args['host'][0]
        
        t=readServerConfig(key);

        self.tmpdir=  "/tmp/conf"+hostname+key+str(uuid.uuid1())
        os.mkdir(self.tmpdir)
        self.tmpdir = self.tmpdir +"/conf"
        os.mkdir(self.tmpdir)
        
	t.writeTincConfig(hostname,self.tmpdir)

        self.tempzipfile = "/tmp/zip"+hostname+key+str(uuid.uuid1())
        
        zip_dir(self.tmpdir, self.tempzipfile)

        size = os.path.getsize(self.tempzipfile)
        request.write('')
        print size
        f = open(self.tempzipfile, "rb")
        try:
          byte = f.read()
          request.write(byte)
        finally:
          f.close()

        return 



class ListHosts(Resource):
    def getChild(self, name, request):
        print ('getChild %s, %s' % (name, request))
        return self

    def __init__(self):
        Resource.__init__(self)

    def render_GET(self, request):
        print('render GET %r' % (request))
        request.setResponseCode(200)
        request.write('')
        key =  request.args['key'][0]

        t = readServerConfig(key);

        request.write("ip configurations which have been generated:")
        request.write("<br>")
        request.write("<ul>")
        for key,value in t.hosts.items():
          request.write("<li>local ip:" + value.localip)
        request.write("</ul>")

        return ""


rocknroll = Resource()
rocknroll.putChild("create", CreateVPN())
rocknroll.putChild("addhost", AddHost())
rocknroll.putChild("getconfig", GetConfig())
rocknroll.putChild("list", ListHosts())

site = server.Site(rocknroll) 
reactor.listenTCP(18001, site) 
reactor.run() 

