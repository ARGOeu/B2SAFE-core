#!/usr/bin/env python

import httplib2
import simplejson
from xml.dom import minidom, Node

import uuid
import argparse
import sys

"""
httplib2
download from http://code.google.com/p/httplib2
python setup.py install

simplejson
download from http://pypi.python.org/pypi/simplejson/
python setup.py install

ubuntu: apt-get install python-httplib2 python-simplejson
"""

################################################################################
# Epic Client Class #
################################################################################

class EpicClient():
    """Class implementing an EPIC client."""
    
    def __init__(self, cred):
	"""Initialize object with connection parameters."""
	
        self.cred  = cred
        self.debug = cred.debug
	self.http = httplib2.Http(disable_ssl_certificate_validation=True)
	self.http.add_credentials(cred.username, cred.password)
	
	
    def _debugMsg(self,method,msg):
	"""Internal: Print a debug message if debug is enabled."""
	
	if self.debug: print "[",method,"]",msg

    
    # Public methods
	    
    def searchHandle(self,prefix,key,value):
        """Search for handles containing the specified key with the specified value.
	
	Parameters:
	prefix: URI to the resource, or the prefix if suffix is not ''.
	url: The URL to search for.
	Returns the searched data field, or None if not found.
	
	"""
        if self.cred.baseuri.endswith('/'):
            uri = self.cred.baseuri + prefix + '/?'+key+'='+value
        else:
            uri = self.cred.baseuri + '/' + prefix + '/?'+key+'='+value
		
	self._debugMsg('searchHandle',"URI " + uri)
	
	hdrs = None
	if self.cred.accept_format: hdrs = {'Accept': self.cred.accept_format}
	try:
	    response, content = self.http.request(uri,method='GET',headers=hdrs)
	except:
	    self._debugMsg('searchHandle', "An Exception occurred during request")
	    return None
	else:
	    self._debugMsg('searchHandle', "Request completed")
	    
	if response.status != 200:
	    self._debugMsg('searchHandle', "Response status: "+str(response.status))
	    return None

        if not content: return None
	handle = simplejson.loads(content)
        if not handle:
            return 'empty'
        
        """
        make sure to only return the handle and strip off the baseuri if it is included
        """
        hdl = handle[0]
        if hdl.startswith(self.cred.baseuri):
            return hdl[len(self.cred.baseuri):len(hdl)]
        elif hdl.startswith(self.cred.baseuri + '/'):
            return hdl[len(self.cred.baseuri + '/'):len(hdl)]
	return prefix + '/' + hdl

    def retrieveHandle(self,prefix,suffix=''):
	"""Retrieve a handle from the PID service. 
	
	Parameters:
	prefix: URI to the resource, or the prefix if suffix is not ''.
	suffix: The suffix of the handle. Default: ''.
	Returns the content of the handle in JSON, None on error.
	
	"""
	if self.cred.baseuri.endswith('/'):
            uri = self.cred.baseuri + prefix
        else:
            uri = self.cred.baseuri + '/' + prefix
	if suffix != '': uri += "/" + suffix.partition("/")[2]
	
	self._debugMsg('retrieveHandle',"URI " + uri)
	hdrs = None
	if self.cred.accept_format: hdrs = {'Accept': self.cred.accept_format}
	try:
	    response, content = self.http.request(uri,method='GET',headers=hdrs)
	except:
	    self._debugMsg('retrieveHandle', "An Exception occurred during request")
	    return None
	else:
	    self._debugMsg('retrieveHandle', "Request completed")
	    
	if response.status != 200:
	    self._debugMsg('retrieveHandle', "Response status: "+str(response.status))
	    return None
	return content

	
    def getValueFromHandle(self,prefix,key,suffix=''):
	"""Retrieve a value from a handle.
	
	Parameters:
	prefix: URI to the resource, or the prefix if suffix is not ''.
	key: The key to search (in type parameter).
	suffix: The suffix of the handle. Default: ''.
	Returns the searched data field, or None if not found.
	
	"""
	
	jsonhandle = self.retrieveHandle(prefix,suffix)
	if not jsonhandle: return None
	handle = simplejson.loads(jsonhandle)
	KeyFound = False
	Value =''
	for item in handle:
	   if 'type' in item and item['type']==key:
		KeyFound = True
		self._debugMsg('getValueFromHandle', "Found key " + key + " value=" + str(item['parsed_data']) )
		Value=str(item['parsed_data'])
		break;

	if KeyFound is False:
	    self._debugMsg('getValueFromHandle', "Value for key " + key + " not found")
	    return None
	else:
	    
	    self._debugMsg('getValueFromHandle', "Found value for key " + key )
	    return Value
	
	
    def createHandle(self,prefix,location,checksum=None,suffix=''):
	"""Create a new handle for a file.
	
	Parameters:
	prefix: URI to the resource, or the prefix if suffix is not ''.
	location: The location (URL) of the file.
	checksum: Optional parameter, store the checksum of the file as well.
	suffix: The suffix of the handle. Default: ''.
	Returns the URI of the new handle, None if an error occurred.
	
	"""
	
        if self.cred.baseuri.endswith('/'):
            uri = self.cred.baseuri + prefix
        else:
            uri = self.cred.baseuri + '/' + prefix

	if suffix != '': uri += "/" + suffix.partition("/")[2]
	self._debugMsg('createHandleWithLocation',"URI " + uri)
	hdrs = {'If-None-Match': '*','Content-Type':'application/json'}

	if checksum:
	    new_handle_json = simplejson.dumps([{'type':'URL','parsed_data':location}, {'type':'CHECKSUM','parsed_data': checksum}])
	else:
	    new_handle_json = simplejson.dumps([{'type':'URL','parsed_data':location}])

	    
	try:
	    response, content = self.http.request(uri,method='PUT',headers=hdrs,body=new_handle_json)
	except:
	    self._debugMsg('createHandleWithLocation', "An Exception occurred during Creation of " + uri)
	    return None
	else:
	    self._debugMsg('createHandleWithLocation', "Request completed")
	    
	if response.status != 201:
	    self._debugMsg('createHandleWithLocation', "Not Created: Response status: "+str(response.status))
            if response.status == 400:
                self._debugMsg('createHandleWithLocation', 'body josn:' + new_handle_json)
	    return None

        
	
        """
        make sure to only return the handle and strip off the baseuri if it is included
        """
        hdl = response['location']

        self.updateHandleWithLocation(hdl,location)

	self._debugMsg('hdl', hdl)
        if hdl.startswith(self.cred.baseuri):
            return hdl[len(self.cred.baseuri):len(hdl)]
        elif hdl.startswith(self.cred.baseuri + '/'):
            return hdl[len(self.cred.baseuri + '/'):len(hdl)]
   	
    	self._debugMsg('final hdl', hdl)
	return hdl
	
	
    def modifyHandle(self,prefix,key,value,suffix=''):
	"""Modify a parameter of a handle
	
	Parameters:
	prefix: URI to the resource, or the prefix if suffix is not ''.
	key: The parameter "type" wanted to change
	value: New value to store in "data"
	suffix: The suffix of the handle. Default: ''.
	Returns True if modified or parameter not found, False otherwise.
	
	"""

        if prefix.startswith(self.cred.baseuri): 
	    prefix = prefix[len(self.cred.baseuri):] 
	
        if self.cred.baseuri.endswith('/'):
            uri = self.cred.baseuri + prefix
        else:
            uri = self.cred.baseuri + '/' + prefix

	if suffix != '': uri += "/" + suffix.partition("/")[2]
	
	self._debugMsg('modifyHandle',"URI " + uri)
	hdrs = {'Content-Type' : 'application/json'}
	
	if not key: return False
	

	handle_json = self.retrieveHandle(prefix,suffix)
	if not handle_json: 
	    self._debugMsg('modifyHandle', "Cannot modify an unexisting handle: " + uri)
	    return False
	    
	handle = simplejson.loads(handle_json)
	KeyFound = False
	if value is None:
		for item in handle:
			if item.has_key('type') and item['type'] == key:
				self._debugMsg('modifyHandle','Remove item ' + key)
				handle.remove(item)
				break
	else:    
		for item in handle:
		   if item.has_key('type') and item['type']==key:
			KeyFound = True
			self._debugMsg('modifyHandle', "Found key " + key + " value=" + str(item['parsed_data']) )
			item['parsed_data']=value
			del item['data']
			break
	
		if KeyFound is False:
		    if value is None:
			self._debugMsg('modifyHandle', "No value for Key " + key + " . Quiting")
			return True
		 		    
		    self._debugMsg('modifyHandle', "Key " + key + " not found. Generating new hash")
		    handleItem={'type': key, 'parsed_data' : value}
		    handle.append(handleItem)
			
	handle_json = simplejson.dumps(handle)
	self._debugMsg('modifyHandle', "JSON: " + str(handle_json))    
	
	try:
	    response, content = self.http.request(uri,method='PUT',headers=hdrs,body=handle_json)
	except:
	    self._debugMsg('modifyHandle', "An Exception occurred during Creation of " + uri)
	    return False
	else:
	    self._debugMsg('modifyHandle', "Request completed")
		    
	if response.status < 200 or response.status >= 300:
	    self._debugMsg('modifyHandle', "Not Modified: Response status: "+str(response.status))
	    return False
	    
	return True
	
	
    def deleteHandle(self,prefix,suffix=''):
	"""Delete a handle from the server.
	
	Parameters:
	prefix: URI to the resource, or the prefix if suffix is not ''.
	suffix: The suffix of the handle. Default: ''.
	Returns True if deleted, False otherwise.
	
	"""
	
	if self.cred.baseuri.endswith('/'):
            uri = self.cred.baseuri + prefix
        else:
            uri = self.cred.baseuri + '/' + prefix

	if suffix != '': uri += "/" + suffix.partition("/")[2]
	self._debugMsg('deleteHandle',"DELETE URI " + uri)
	
	try:
	    response, content = self.http.request(uri,method='DELETE')
	except:
	    self._debugMsg('deleteHandle', "An Exception iccurred during deletion of " + uri)
	    return False
	else:
	    self._debugMsg('deleteHandle', "Request completed")
	    
	if response.status < 200 or response.status >= 300:
	    self._debugMsg('deleteHandle', "Not Deleted: Response status: "+str(response.status))
	    return False
	    
	return True    


    def updateHandleWithLocation(self,prefix,value,suffix=''):
	"""Update the 10320/LOC handle type field of the handle record.
         
        Parameters:
        prefix: URI to the resource, or the prefix if suffix is not ''.
	value: New value to store in "10320/LOC"
        suffix: The suffix of the handle. Default: ''.
        Returns True if updated, False otherwise.
         
        """

	if self.cred.baseuri.endswith('/'):
		uri = self.cred.baseuri + prefix
	else:
	        uri = self.cred.baseuri + '/' + prefix

	if suffix != '': uri += "/" + suffix.partition("/")[2]

	loc10320 = self.getValueFromHandle(prefix,"10320/LOC",suffix)
	self._debugMsg('updateHandleWithLocation', "found 10320/LOC: " +str(loc10320))
	if loc10320 is None:
		loc10320 = '<locations><location id="0" href="'+value+'" /></locations>'
		response = self.modifyHandle(prefix,"10320/LOC",loc10320,suffix)
		if not response:
			self._debugMsg('updateHandleWithLocation', "Cannot update handle: " + uri \
					+ " with location: " + value)
             		return False
	else:
		lt = LocationType(loc10320,self.debug)
		response = lt.checkInclusion(value)
		if response:
			self._debugMsg('updateHandleWithLocation', "the location "+value+" is already included!")
		else:
			resp, content = lt.addLocation(value)
			if not resp: 
				self._debugMsg('updateHandleWithLocation', "the location "+value \
						+" cannot be added")
			else:
				if not self.modifyHandle(prefix,"10320/LOC",content,suffix):
				        self._debugMsg('updateHandleWithLocation', "Cannot update handle: " \
							+uri+ " with location: " + value)
				else:
					self._debugMsg('updateHandleWithLocation', "location added")
					return True
		return False 

	return True


    def removeLocationFromHandle(self,prefix,value,suffix=''):
        """Remove one of the 10320/LOC handle type values from the handle record.
	
	Parameters:
	prefix: URI to the resource, or the prefix if suffix is not ''.
	value: Value to be deleted from the "10320/LOC".
	suffix: The suffix of the handle. Default: ''.
	Returns True if removed, False otherwise.
	"""
	
	if self.cred.baseuri.endswith('/'):
		uri = self.cred.baseuri + prefix
	else:
	        uri = self.cred.baseuri + '/' + prefix
	
	if suffix != '': uri += "/" + suffix.partition("/")[2]

        loc10320 = self.getValueFromHandle(prefix,"10320/LOC",suffix)
        if loc10320 is None:
		self._debugMsg('removeLocationFromHandle', "Cannot remove location: " +value \
		                + " from handle: " +uri+ ", the field 10320/LOC does not exists")
		return False
	else:
	        lt = LocationType(loc10320,self.debug)
		if not lt.checkInclusion(value):
			self._debugMsg('removeLocationFromHandle', "the location "+value+" is not included!")
		else:
			response, content = lt.removeLocation(value)
		        if response:
				if self.modifyHandle(prefix,"10320/LOC",content,suffix):
					return True
			self._debugMsg('removeLocationFromHandle', "the location " +value \
			                + " cannot be removed")
		return False
			
	return True

################################################################################
# EPIC Client Location Type Class #
################################################################################

class LocationType():
	"""Class implementing a 10320/LOC handle type."""
	# Expected format for 10320/LOC handle type:
	# <locations><location id="0" href="location" country="xx" weight="0" /></locations>


	def __init__(self,field,debug=False):
		self.domfield = minidom.parseString(field)
		self.debug = debug


	def _debugMsg(self,method,msg):
		"""Internal: Print a debug message if debug is enabled."""
		 
		if self.debug: print "[",method,"]",msg


	def isEmpty(self):
		"""Check if the 10320/LOC handle type field is empty.
			     
		Parameters:
	        Returns True and 0 if empty, False and the number of locations otherwise.
	        """

		locations = self.domfield.getElementsByTagName("location")
		if locations.length == 0: 
			self._debugMsg('isEmpty', "the 10320/LOC field is empty")
			return True, 0
		self._debugMsg('isEmpty', "the 10320/LOC field contains " +str(locations.length)+ " locations")
		return False, str(locations.length)


	def checkInclusion(self,loc):
		"""Check if a 10320/LOC handle type value is included.
                              
                Parameters:
		loc: The replica location PID value.
                Returns True if it is included, False otherwise.
                """

		locations = self.domfield.getElementsByTagName("location")
		for url in locations:
			if ( url.getAttribute('href') == loc ):
				self._debugMsg('checkInclusion', "the location (" +loc+ ") is included")
				return True
		self._debugMsg('checkInclusion', "the location (" +loc+ ") is not included")
		return False


	def removeLocation(self,loc):
		"""Remove a replica PID from the 10320/LOC handle type field.
		                              
		Parameters:
		loc: The replica location PID value.
		Returns True and the 10320/LOC handle type field itself if the value is removed, False and None otherwise.
                """

		main = self.domfield.childNodes[0]
		locations = self.domfield.getElementsByTagName("location")
		for url in locations:
			if ( url.getAttribute('href') == loc ):
				main.removeChild(url)
				self._debugMsg('removeLocation', "removed location: " +loc)
				return True, main.toxml()
		self._debugMsg('removeLocation', "cannot remove location: " +loc)
		return False, None
	

	def addLocation(self,loc):
		"""Add a replica PID to the 10320/LOC handle type field.
                              
                Parameters:
                loc: The replica location PID value.
                Returns True and the 10320/LOC handle type field itself if the value is added, False and None otherwise.
                """

		try:
			newurl = self.domfield.createElement("location")
			response, content = self.isEmpty()
			newurl.setAttribute('id', content)
			newurl.setAttribute('href', loc)
			self.domfield.childNodes[0].appendChild(newurl)
			main = self.domfield.childNodes[0]
			self._debugMsg('addLocation', "added new location: " +loc)
			return True, main.toxml()
		except:
			self._debugMsg('addLocation', "an exception occurred, adding the new location: " +loc)
			return False, None

################################################################################
# EPIC Client Credentials Class #
################################################################################

class Credentials():
    """
        get credentials from different storages, right now irods or filesystem

        Please store credentials in the following format, otherwise there are problems...
        {
        "baseuri": "https://epic_api_endpoint here", 
        "username": "XXX",
        "password": "YYYYYYYY",
        "accept_format": "application/json"
        }

    """
    def __init__(self,store, file):
        self.store = store
        self.file = file

        self.debug = False
        """
        The following default values should be set via the credentials files.
        These example values will be overwritten
        """
        self.baseuri = 'https://epic.sara.nl/v2_test/handles/'
        self.username = 'XXX'
        self.prefix = self.username
        self.password = 'YYYYYY'
        self.accept_format = 'application/json'


    def parse(self):        
        if ((self.store!="os" and self.store!="irods") or self.file =="NULL"):
            if self.debug: print "credential store or path not given/valid, using:%s %s %s" % (self.baseuri,self.username,self.accept_format)
            return

        if self.store=="os":
            try:
                filehandle=open(self.file,"r")
                tmp=eval(filehandle.read())
                filehandle.close()                
            except Exception, e:
                print "problem while getting credentials from filespace"
                print "Error:", e
        elif self.store=="irods":
            try:
                from irods import getRodsEnv,rcConnect,clientLogin,iRodsOpen
                myEnv, status = getRodsEnv()
                conn, errMsg = rcConnect(myEnv.getRodsHost(), myEnv.getRodsPort(), myEnv.getRodsUserName(), myEnv.getRodsZone())
                if debug: print myEnv.getRodsHost(), myEnv.getRodsPort(), myEnv.getRodsUserName(), myEnv.getRodsZone()
                status = clientLogin(conn)
                test = iRodsOpen(conn, self.file, 'r')

                tmp = eval(test.read())    
                test.close()
                conn.disconnect()
            except Exception, e:
                print "problem while getting credentials from irods"
        else:
            print "this should not happen..."

        self.baseuri=tmp['baseuri']
        self.username=tmp['username']
        self.prefix = self.username
        self.password=tmp['password']
        self.accept_format=tmp['accept_format']
        self.debug=tmp['debug']
        if self.debug: print "credentials from %s:%s %s %s" % (self.store,self.baseuri,self.username,self.accept_format)

################################################################################
# EPIC Client Command Line Interface #
################################################################################

def search(args):
    credentials = Credentials(args.credstore,args.credpath)
    credentials.parse();

    ec = EpicClient(credentials)
    result = ec.searchHandle(credentials.prefix, args.key, args.value)

    sys.stdout.write(str(result))

def read(args):
    credentials = Credentials(args.credstore,args.credpath)
    credentials.parse();

    ec = EpicClient(credentials)
    if args.key == None:
        result = ec.retrieveHandle(credentials.prefix, args.handle)
    else:
        result = ec.getValueFromHandle(args.handle,args.key)

    sys.stdout.write(str(result))

def create(args):
    credentials = Credentials(args.credstore,args.credpath)
    credentials.parse();
    
    uid = uuid.uuid1();
    pid = credentials.username + "/" + str(uid)

    ec = EpicClient(credentials)
    result = ec.createHandle(pid,args.location)
    
    if result == None:
        sys.stdout.write("error")
    else:
        sys.stdout.write(result)

def modify(args):
    credentials = Credentials(args.credstore,args.credpath)
    credentials.parse();

    ec = EpicClient(credentials)
    result = ec.modifyHandle(args.handle,args.key,args.value)

    sys.stdout.write(str(result))

def delete(args):
    credentials = Credentials(args.credstore,args.credpath)
    credentials.parse();

    ec = EpicClient(credentials)
    result = ec.deleteHandle(args.handle)

    sys.stdout.write(str(result))

def relation(args):
    credentials = Credentials(args.credstore,args.credpath)
    credentials.parse();

    ec = EpicClient(credentials)
    result = ec.updateHandleWithLocation(args.ppid,args.cpid)
    sys.stdout.write(str(result))

def test(args):
    credentials = Credentials(args.credstore,args.credpath)
    credentials.parse();
    
    ec = EpicClient(credentials)
    
    print ""
    print "Retrieving Value of FOO from " + credentials.prefix + "/NONEXISTING (should be None)"
    print ec.getValueFromHandle(credentials.prefix,"FOO","NONEXISTING")
    
    print ""
    print "Creating handle " + credentials.prefix + "/TEST_CR1 (should be True)"
    print ec.createHandle(credentials.prefix + "/TEST_CR1","http://www.test.com/1") #,"335f4dea94ef48c644a3f708283f9c54"
    
    print ""
    print "Retrieving handle info from " + credentials.prefix + "/TEST_CR1"
    print ec.retrieveHandle(credentials.prefix +"/TEST_CR1")
    
    print ""
    print "Retrieving handle by url"
    result = ec.searchHandle(credentials.prefix, "URL", "http://www.test.com/1")
    print result

    print ""
    print "Modifying handle info from " + credentials.prefix + "/TEST_CR1 (should be True)"
    print ec.modifyHandle(credentials.prefix +"/TEST_CR1","uri","http://www.test.com/2")
    
    print ""
    print "Retrieving Value of EMAIL from " + credentials.prefix + "/TEST_CR1 (should be None)"
    print ec.getValueFromHandle("" + credentials.prefix +"/TEST_CR1","EMAIL")

    print ""
    print "Adding new info to " + credentials.prefix + "/TEST_CR1 (should be True)"
    print ec.modifyHandle(credentials.prefix + "/TEST_CR1","EMAIL","test@te.st")    

    print ""
    print "Retrieving Value of EMAIL from " + credentials.prefix + "/TEST_CR1 (should be test@te.st)"
    print ec.getValueFromHandle("" + credentials.prefix +"/TEST_CR1","EMAIL")

    print ""
    print "Updating handle info with a new 10320/loc type location 846/157c344a-0179-11e2-9511-00215ec779a8"
    print "(should be True)"
    print ec.updateHandleWithLocation(credentials.prefix + "/TEST_CR1","846/157c344a-0179-11e2-9511-00215ec779a8")

    print ""
    print "Updating handle info with a new 10320/loc type location 846/157c344a-0179-11e2-9511-00215ec779a9"
    print "(should be True)"
    print ec.updateHandleWithLocation(credentials.prefix + "/TEST_CR1","846/157c344a-0179-11e2-9511-00215ec779a9")
    
    print ""
    print "Retrieving handle info from " + credentials.prefix + "/TEST_CR1"
    print ec.retrieveHandle(credentials.prefix + "/TEST_CR1")
    
    print ""
    print "Deleting EMAIL parameter from " + credentials.prefix + "/TEST_CR1 (should be True)"
    print ec.modifyHandle(credentials.prefix + "/TEST_CR1","EMAIL",None)  

    print ""
    print "Retrieving Value of EMAIL from " + credentials.prefix + "/TEST_CR1 (should be None)"
    print ec.getValueFromHandle("" + credentials.prefix +"/TEST_CR1","EMAIL")

    print ""
    print "Updating handle info with a new 10320/loc type location 846/157c344a-0179-11e2-9511-00215ec779a8"
    print "(should be False)"
    print ec.updateHandleWithLocation(credentials.prefix + "/TEST_CR1","846/157c344a-0179-11e2-9511-00215ec779a8")

    print ""
    print "Removing 10320/loc type location 846/157c344a-0179-11e2-9511-00215ec779a8"
    print "(should be True)"
    print ec.removeLocationFromHandle(credentials.prefix + "/TEST_CR1","846/157c344a-0179-11e2-9511-00215ec779a8")

    print ""
    print "Removing 10320/loc type location 846/157c344a-0179-11e2-9511-00215ec779a8"
    print "(should be False)"
    print ec.removeLocationFromHandle(credentials.prefix + "/TEST_CR1","846/157c344a-0179-11e2-9511-00215ec779a8")
    
    print ""
    print "Retrieving handle info from " + credentials.prefix + "/TEST_CR1"
    print ec.retrieveHandle(credentials.prefix + "/TEST_CR1")
    
    print ""
    print "Deleting " + credentials.prefix + "/TEST_CR1 (should be True)"
    print ec.deleteHandle(credentials.prefix + "/TEST_CR1")  
    
    print ""
    print "Deleting (again) " + credentials.prefix + "/TEST_CR1 (should be False)"
    print ec.deleteHandle(credentials.prefix + "/TEST_CR1")  
    
    print ""
    print "Retrieving handle info from non existing " + credentials.prefix + "/TEST_CR1 (should be None)"
    print ec.retrieveHandle(credentials.prefix + "/TEST_CR1")   

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='EUDAT EPIC client API. Supports reading, querying, creating, modifying and deleting handle records.')
    parser.add_argument("credstore",choices=['os','irods'],default="NULL",help="the used credential storage (os=filespace,irods=iRODS storage)")
    parser.add_argument("credpath",default="NULL",help="path to the credentials")
    """parser.add_argument("-d", "--debug", help="Show debug output")"""
    
    subparsers = parser.add_subparsers(title='Actions',description='Handle record management actions',help='additional help')

    parser_create = subparsers.add_parser('create', help='creating handle records')
    parser_create.add_argument("location", help="location to store in the new handle record")
    parser_create.set_defaults(func=create)

    parser_modify = subparsers.add_parser('modify', help='modifying handle records')
    parser_modify.add_argument("handle", help="the handle value")
    parser_modify.add_argument("key", help="the key of the field to change in the pid record")
    parser_modify.add_argument("value", help="the new value to store in the pid record identified with the supplied key")
    parser_modify.set_defaults(func=modify)

    parser_delete = subparsers.add_parser('delete', help='Deleting handle records')
    parser_delete.add_argument("handle", help="the handle value of the digital object instance to delete")
    parser_delete.set_defaults(func=delete)

    parser_read = subparsers.add_parser('read', help='Read handle record')
    parser_read.add_argument("handle", help="the handle value")
    parser_read.add_argument("--key", help="only read this key instead of the full handle record")
    parser_read.set_defaults(func=read)

    parser_search = subparsers.add_parser('search', help='Search for handle records')
    parser_search.add_argument("key", choices=['URL'],help="the key to search")
    parser_search.add_argument("value", help="the value to search")
    parser_search.set_defaults(func=search)

    parser_relation = subparsers.add_parser('relation', help='Add a (parent,child) relationship between the specified handle records')
    parser_relation.add_argument("ppid", help="parent handle value")
    parser_relation.add_argument("cpid", help="child handle value")
    parser_relation.set_defaults(func=relation)

    parser_test = subparsers.add_parser('test', help='Run test suite')
    parser_test.set_defaults(func=test)

    args = parser.parse_args()
    args.func(args)
