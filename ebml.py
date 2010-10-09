from __future__ import print_function
from __future__ import division

import os
import dtd
import bitstring
import math

class ContainerPayload(list):
	def __init__(self, *args, **kwargs):
		list.__init__(self, *args, **kwargs)
	
	def append(self, item, keep_reference=False):
		if keep_reference:
			list.append(self, item)
		else:
			item.destroy_reference()
			list.append(self, item)
	
	def __delitem__(self, item):
		if item.has_reference():
			item.void()
		else:
			list.__delitem__(item)
	

class EOFError(Exception):
	pass

class Reference(object):
	def __init__(self, doctype, filename=None, offset=None):
		self.doctype = doctype
		self.filename = filename
		self.hexid_offset = offset
		if filename == offset == None:
			self.dummy = True
	
	def __repr__(self):
		return "Reference(%r, %r, %r)" % (self.doctype, self.filename, 
			self.hexid_offset)
	
	def __str__(self):
		return "<%s bytes at offset %s in file %s>" % (self.total_length, 
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
		elif name == 'valtype':
			self.valtype = self.doctype.lookup(self.hexid).valtype
			return self.valtype
		elif name == 'payload':
			return self.get_payload()
		elif name == 'hexid':
			return self.get_hexid()
		else:
			raise AttributeError
	
	def get_hexid(self):
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
				if hexid in self.doctype.get_ids():
					break
		self.hexid_length = len(hexid)
		self.hexid = hexid
		return self.hexid
	
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
	
	def get_payload(self):
		if self.valtype == 'container':
			return self.get_container_payload()
		raw_payload = bitstring.Bits(filename=self.filename, 
			offset=self.payload_offset*8, length=self.payload_length*8)
		if self.valtype == 'uint':
			self.payload = raw_payload.uint
		elif self.valtype == 'int':
			self.payload = raw_payload.int
		elif self.valtype == 'float':
			self.payload = raw_payload.float
		elif self.valtype == 'string':
			self.payload = raw_payload.bytes
		elif self.valtype == 'date':
			self.payload = raw_payload.int
		elif self.valtype == 'binary':
			self.payload = raw_payload.bytes
		return self.payload
	
	def get_container_payload(self):
		self.payload = ContainerPayload()
		offset = self.payload_offset
		while offset != self.end:
			if offset > self.end:
				raise EOFError('Went too far, file is damaged.')
			reference = Reference(self.doctype, self.filename, offset)
			element = Element(self.doctype, reference)
			self.payload.append(element, keep_reference=True)
			offset += reference.total_length
		return self.payload[:]
	
	def get_delta_size(self, new_payload):
		if self.valtype == 'container':
			payload_delta = sum([item.get_delta_size() for item in new_payload])
			new_payload_length = self.payload_length + payload_delta
		else:
			new_payload_length = len(self.get_binary_payload(new_payload))
			payload_delta = new_payload_length - self.payload_length
		new_size_length = len(self.convert_size(new_payload_length))
		size_delta = new_size_length - self.size_length
		return payload_delta + size_delta
	
	def get_binary_payload(self, payload=None):
		if payload == None:
			payload = self.payload
		if self.valtype == 'uint':
			if payload == 0 and self.payload_length == 0:
				return bitstring.Bits()
			minlength = math.ceil(math.log(payload+1, 2)/8)
			if minlength > self.payload_length:
				return bitstring.Bits(uint=payload, 
					length=self.payload_length*8)
			else:
				return bitstring.Bits(uint=payload, length=minlength*8)
		elif self.valtype == 'int':
			if payload == 0 and self.payload_length == 0:
				return bitstring.Bits()
			elif payload < 0:
				minlength = math.ceil(math.log(math.abs(payload), 2)/8) + 1
			else:
				minlength = math.ceil(math.log(payload+1, 2)/8) + 1
			if minlength > self.payload_length:
				return bitstring.Bits(int=payload, length=self.payload_length*8)
			else:
				return bitstring.Bits(int=payload, length=minlength*8)
		elif self.valtype == 'float':
			if payload == 0.0 and self.payload_length == 0:
				return bitstring.Bits()
			else:
				return bitstring.Bits(float=payload, 
					length=self.payload_length*8)
		elif self.valtype == 'string':
			if len(payload) < self.payload_length: #add padding
				payload += '\x00' * self.payload_length - len(payload)
			return bitstring.Bits(bytes=payload)
		elif self.valtype == 'date':
			return bitstring.Bits(int=payload, length=64)
		elif self.valtype == 'binary':
			return bitstring.Bits(bytes=payload)
	

class Element(object):
	def __init__(self, *args):
		if len(args) == 2:
			self.doctype = args[0]
			self.reference = args[1]
			self.hexid = self.reference.get_hexid()
			if self.valtype != 'container':
				if self.reference.payload_length < 16:
					self.payload = self.reference.get_payload()
		elif len(args) == 3:
			self.doctype = args[0]
			self.hexid = hexid[1]
			self.payload = payload[2]
		elif len(args) < 2:
			raise TypeError('__init__() takes at least 2 arguments (%s given)' % len(args))
		else:
			raise TypeError('__init__() takes at most 3 arguments (%s given)' % len(args))
	
	def __repr__(self):
		if self.has_reference():
			return 'Element(%r, %r)' % (self.doctype, self.reference)
		else:
			return 'Element(%r, %r, %r)' % (self.doctype, self.hexid, self.payload)
	
	def __str__(self):
		if 'payload' in dir(self):
			return '<%s element with value %r>' % (self.name, self.payload)
		else:
			return '<%s element, %s>' % (self.name, self.reference)
	
	def __getattr__(self, key):
		if key == 'name':
			self.name = self.doctype.lookup(self.hexid).name
			return self.name
		elif key == 'payload':
			self.payload = self.reference.get_payload()
			return self.payload
		elif key == 'valtype':
			self.valtype = self.doctype.lookup(self.hexid).valtype
			return self.valtype
		else:
			raise AttributeError
	
	def __iter__(self):
		if self.valtype == 'container':
			return iter(self.payload)
	
	def has_write_pending(self):
		if self.has_reference():
			if self.payload == self.reference.payload:
				if self.valtype == 'container':
					for item in self:
						if item.has_write_pending():
							return True
					return False
				return False
			return True
		return True
	
	def has_reference(self):
		if 'reference' in dir(self):
			return True
		return False
	
	def get_delta_size(self):
		if self.writes_pending():
			if self.valtype == 'container':
				payload_delta = sum([item.get_delta_size() for item in self])
				self.delta_size = self.reference.get_delta_size(self.delta_size)
			else:
				if self.has_reference():
					self.delta_size = self.reference.get_delta_size(self.payload)
				else:
					dummy_reference = Reference(self.doctype)
					self.delta_size = dummy_reference.get_delta_size(self.payload)
					self.delta_size += len(self.hexid)
				return self.delta_size
		return 0
	
	def write(starting_shift=0, max_shift=1024, commit=False, upcoming=None):
		if self.valtype == 'container':
			results = ContainerPayload()
			for index, child in enumerate(self.payload):
				if index + 1 == len(self.payload):
					next = None
				else:
					next = self.payload(index + 1)
				if child.valtype == 'container':
					result = child.write(shift, max_shift, commit, next)
				else:
					result = child.reference.write(shift, max_shift, commit, next)
				results.append(result, keep_reference=True)
				shift += result.shift_delta
			
		else:
			pass
	


class EBML(object):
	def __init__(self, filename, doctype=None):
		self.filename = filename
		if doctype:
			self.doctype == dtd.Doctype(doctype)
		else:
			self.doctype = dtd.DoctypeBase()
			self.find_document_type()
		self.build_document()
	
	def __repr__(self):
		return 'EBML(%r)' % self.filename
	
	def __str__(self):
		return str(self.children)
	
	def find_document_type(self):
		file = open(self.filename, 'rb')
		reference = Reference(self.doctype, self.filename, 0)
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
		self.children = ContainerPayload()
		offset = 0
		end = os.stat(self.filename).st_size
		while True:
			if offset == end:
				break
			elif offset > end:
				raise EOFError('Went too far, file is damaged.')
			reference = Reference(self.doctype, self.filename, offset)
			element = Element(self.doctype, reference)
			self.children.append(element, keep_reference=True)
			offset = reference.end
	
	def write(self):
		for item in self.children:
			pass
	


EBML('test.mkv')
EBML('test2.mkv')
EBML('test3.mkv')
EBML('test4.mkv')