from __future__ import print_function

import os
import dtd
import bitstring

class EOFError(Exception):
	pass

class Reference(object):
	def __init__(self, filename, offset):
		self.filename = filename
		self.hexid_offset = offset
	
	def __repr__(self):
		return "Reference(%r, %r)" % (self.filename, 
			self.hexid_offset)
	
	def __str__(self):
		return "%s bytes at offset %s in file %s" % (self.total_length, 
				self.hexid_offset, self.filename)
	
	def __getattr__(self, name):
		if name == 'payload_length':
			return self.get_payload_length()
		elif name == 'end':
			self.end = self.total_length + self.hexid_offset
			return self.end
		elif name == 'size_offset':
			self.size_offset = self.hexid_offset + self.hexid_length
			return self.size_offset
		elif name == 'size_length':
			return self.get_size_length()
		elif name == 'payload_offset':
			self.payload_offset = self.size_offset + self.size_length
			return self.payload_offset
		elif name == 'total_length':
			self.total_length = self.hexid_length + self.size_length + self.payload_length
			return self.total_length
		else:
			raise AttributeError
	
	def get_hexid(self, ids):
		hexid = ''
		with open(self.filename, 'rb') as file:
			file.seek(self.hexid_offset)
			while True:
				byte = file.read(1)
				if byte == '':
					raise EOFError('Unexpected EOF.')
				hexid += byte
				if len(hexid) > 8:
					raise EOFError('Should have found an id by now: %r') % hexid
				if hexid in ids:
					break
		self.hexid_length = len(hexid)
		return hexid
	
	def get_size_length(self):
		if 'size_length' in dir(self):
			return self.size_length
		bits = bitstring.Bits(filename=self.filename, offset=self.size_offset*8)
		bitcount = 0
		bit = 0
		while not bit:
			bit = bits.read(1)
			if bit == '':
				raise EOFError('Unexpected EOF.')
			bitcount += 1
		self.size_length = bitcount
		return self.size_length		
	
	def get_payload_length(self):
		if 'payload_length' in dir(self):
			return self.payload_length
		bits = bitstring.BitString(filename=self.filename, offset=self.size_offset*8,
			length=self.size_length*8)
		for pos, bit in enumerate(bits):
			if bit == 1:
				index = pos
				break
		del bits[:index + 1]
		self.payload_length = bits.uint
		return self.payload_length
	
	def get_payload(self, valtype):
		raw_payload = bitstring.Bits(filename=self.filename, 
			offset=self.payload_offset*8, length=self.payload_length*8)
		if valtype == 'uint':
			payload = raw_payload.uint
		elif valtype == 'int':
			payload = raw_payload.int
		elif valtype == 'float':
			payload = raw_payload.float
		elif valtype == 'string':
			payload = raw_payload.bytes
		elif valtype == 'date':
			payload = raw_payload.int
		elif valtype == 'binary':
			payload = raw_payload.bytes
		return payload
	
	def get_container_payload(self, doctype):
		payload = []
		offset = self.payload_offset
		while offset != self.end:
			if offset > self.end:
				raise EOFError('Went too far, file is damaged.')
			reference = Reference(self.filename, offset)
			element = Element(doctype, reference)
			payload.append(element)
			offset += reference.total_length
		return payload
	

class Element(object):
	def __init__(self, *args):
		if len(args) == 2:
			self.doctype = args[0]
			self.reference = args[1]
			self.hexid = self.reference.get_hexid(self.doctype.get_ids())
			if self.valtype != 'container':
				if self.reference.payload_length < 16:
					self.set_payload()
		elif len(args) == 3:
			self.doctype = args[0]
			self.hexid = hexid[1]
			self.payload = payload[2]
		else:
			raise SyntaxError
	
	def __repr__(self):
		if 'reference' in dir(self):
			return 'Element(%r, %r)' % (self.doctype, self.reference)
		else:
			return 'Element(%r, %r, %r)' % (self.doctype, self.hexid, self.payload)
	
	def __getattr__(self, key):
		if key == 'name':
			self.name = self.doctype.lookup(self.hexid).name
			return self.name
		elif key == 'payload':
			self.set_payload()
			return self.payload
		elif key == 'valtype':
			self.valtype = self.doctype.lookup(self.hexid).valtype
			return self.valtype
		else:
			raise AttributeError
	
	def __iter__(self):
		if self.valtype == 'container':
			return iter(self.payload)
	
	def set_payload(self):
		if self.valtype == 'container':
			self.payload = self.reference.get_container_payload(self.doctype)
		else:
			self.payload = self.reference.get_payload(self.valtype)
	


class EBML(object):
	def __init__(self, filename, doctype=None):
		self.filename = filename
		if doctype:
			self.doctype == dtd.Doctype(doctype)
		else:
			self.doctype = dtd.DoctypeBase()
			self.find_document_type()
		self.build_document()
	
	def find_document_type(self):
		file = open(self.filename, 'rb')
		reference = Reference(self.filename, 0)
		first_element = Element(self.doctype, reference)
		doctype_element_name = 'DocType'
		found = False
		for element in first_element:
			if element.name == doctype_element_name:
				type_name = element.payload
				self.doctype = dtd.Doctype(type_name)
				found = True
				break
		if not found:
			raise SyntaxError("Didn't find a document type declaration.")
	
	def build_document(self):
		self.children = []
		offset = 0
		end = os.stat(self.filename).st_size
		while True:
			if offset == end:
				break
			elif offset > end:
				raise EOFError('Went too far, file is damaged.')
			reference = Reference(self.filename, offset)
			element = Element(self.doctype, reference)
			self.children.append(element)
			offset = reference.end
	


#EBML('test.mkv')
#EBML('test2.mkv')
#EBML('test3.mkv')
#EBML('test4.mkv')
