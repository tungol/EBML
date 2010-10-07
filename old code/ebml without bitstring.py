from __future__ import print_function

import os
import dtd
from binary_encoders import *
import bitstring

class Reference(object):
	def __init__(self, doctype, filename, offset):
		self.doctype = doctype
		self.filename = filename
		self.hexid_offset = offset
	
	def __repr__(self):
		return "Reference(%r, %r, %r)" % (self.doctype, self.filename, 
			self.hexid_offset)
	
	def __str__(self):
		if 'payload' in dir(self):
			return str(self.payload)
		else:
			return "%s bytes at offset %s in file %s" % (self.full_length, 
				self.hexid_offset, self.filename)
	
	def __iter__(self):
		if self.valtype == 'container':
			return iter(self.payload)
	
	def __getattr__(self, name):
		if name == 'hexid':
			return self.get_hexid()
		elif name == 'size':
			return self.get_size()
		elif name == 'name':
			self.name = self.doctype.lookup(self.hexid).name
			return self.name
		elif name == 'end':
			self.end = self.full_length + self.hexid_offset
			return self.end
		elif name == 'payload':
			return self.get_payload()
		elif name == 'valtype':
			self.valtype = self.doctype.lookup(self.hexid).valtype
			return self.valtype
		elif name == 'hexid_length':
			self.get_hexid()
			return self.hexid_length
		elif name == 'size_offset':
			self.get_hexid()
			return self.size_offset
		elif name == 'size_length':
			self.get_size()
			return self.size_length
		elif name == 'payload_offset':
			self.get_size()
			return self.payload_offset
		elif name == 'full_length':
			self.full_length = self.hexid_length + self.size_length + self.size
			return self.full_length
		else:
			raise AttributeError
	
	def get_hexid(self):
		if 'hexid' in dir(self):
			return self.hexid
		hexid = ''
		with open(self.filename, 'rb') as file:
			file.seek(self.hexid_offset)
			while True:
				byte = file.read(1)
				if byte == '':
					raise SyntaxError('Unexpected EOF.')
				hexid += byte
				if len(hexid) > 8:
					raise SyntaxError('Should have found an id by now: %r') % hexid
				if hexid in self.doctype.get_ids():
					break
		self.hexid = hexid
		self.hexid_length = len(hexid)
		self.size_offset = self.hexid_offset + self.hexid_length
		return hexid
	
	def get_size(self):
		if 'size' in dir(self):
			return self.size
		bits = []
		bytecount = 0
		bytes = ''
		with open(self.filename, 'rb') as file:
			file.seek(self.size_offset)
			while True:
				byte = file.read(1)
				bytes += byte
				if byte == '':
					raise SyntaxError('Unexpected EOF.')
				bytecount += 1
				bits += self.get_bits(byte)
				bitcount = 0
				one_found = False
				for bit in bits:
					bitcount += 1
					if bit == '1':
						one_found = True
						break
				if one_found:
					break
			extra_bytes = file.read(bitcount - bytecount)
		bits += self.get_bits(extra_bytes)
		index = bits.index('1')
		del bits[:index + 1]
		bitstring = '0b' + ''.join(bits)
		size = int(bitstring, 2)
		self.size = size
		self.size_length = bitcount
		self.payload_offset = self.size_offset + self.size_length
		return size
	
	def get_bits(self, hexstring):
		allbits = []
		for byte in hexstring:
			b = bin(ord(byte))
			bits = [x for x in b[2:]]
			while len(bits) < 8:
				bits.insert(0, '0')
			allbits += bits
		return allbits
	
	def get_payload(self):
		with open(self.filename, 'rb') as file:
			file.seek(self.payload_offset)
			if self.valtype == 'container':
				self.payload = []
				while True:
					offset = file.tell()
					if offset == self.end:
						break
					elif offset > self.end:
						raise SyntaxError('Went too far, file is damaged.')
					reference = Reference(self.doctype, self.filename, offset)
					self.payload.append(reference)
					file.seek(reference.end)
			else:
				raw = file.read(self.size)
				if self.valtype == 'uint':
					self.payload = decode_uint(raw)
				elif self.valtype == 'int':
					self.payload = decode_twos_complement(raw)
				elif self.valtype == 'float':
					self.payload = decode_ieee_float(raw)
				elif self.valtype == 'string':
					self.payload = raw
				elif self.valtype == 'date':
					self.payload = decode_date(raw)
				elif self.valtype == 'binary':
					self.payload = raw
			return self.payload
	

class Element(object):
	def __init__(self, doctype, hexid, payload):
		self.doctype = doctype
		self.hexid = hexid
		self.payload = payload

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
		first_element = Reference(self.doctype, self.filename, 0)
		doctype_name = 'DocType'
		found = False
		for element in first_element:
			if element.name == doctype_name:
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
				raise SyntaxError('Went too far, file is damaged.')
			reference = Reference(self.doctype, self.filename, offset)
			self.children.append(reference)
			offset = reference.end
		print(self.children)
	


EBML('test.mkv')
EBML('test2.mkv')
EBML('test3.mkv')
EBML('test4.mkv')
