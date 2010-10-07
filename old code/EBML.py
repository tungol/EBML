import os
import re
import datetime

class EBMLParser:
	pass


class ElementClass(BaseType):
	self.add_property('id')
	self.add_property('parent')
	self.add_property('level')
	self.add_property('cardnality')
	def __init__(self, name, id, basetype):
		self.name = name
		self.id = id
		self.set_properties(basetype.get_properties())
	


class IntType(BaseType):
	self.add_property('default')
	self.name = 'int'
	self.valtype = 'int'
	self.default = None
	self.range = None
	self.size = range(0,8)

class UintType(BaseType):
	self.add_property('default')
	self.name = 'uint'
	self.valtype = 'uint'
	self.default = None
	self.range = None
	self.size = range(0,8)

class FloatType(BaseType):
	self.add_property('default')
	self.name = 'float'
	self.valtype = 'float'
	self.default = None
	self.range = None
	self.size = [0,4,8,10]

class StringType(BaseType):
	self.add_property('default')
	self.name = 'string'
	self.valtype = 'string'
	self.default = None
	self.range = None
	self.size = None

class DateType(BaseType):
	self.add_property('default')
	self.name = 'date'
	self.valtype = 'date'
	self.default = None
	self.range = None
	self.size = 8

class BinaryType(BaseType):
	self.add_property('default')
	self.name = 'binary'
	self.valtype = 'binary'
	self.default = None
	self.range = range(0,255)
	self.size = None

class ContainerType(BaseType):
	self.add_property('ordered')
	self.name = 'container'
	self.valtype = 'container'
	self.range = None
	self.size = None
	self.ordered = True


class BaseType:
	self.valid_prop = ('name', 'valtype', 'id', 'default', 'parent', 'level',
		'cardnality', 'ordered', 'range', 'size')
	self.has_prop = set(('name', 'valtype', 'range', 'size'))
	def add_property(self, kind):
		if kind in self.valid_prop:
			self.has_prop.add(kind)
		else:
			print "Invalid property: %s" % kind
			raise ValueError
	
	def get_properties(self):
		return zip(self.has_prop, [self.__dict__[x] for x in self.has_prop])
	
	def set_properties(self, properties):
		for kind, value in properties:
			self.setter(kind, value)
	
	def is_container(self):
		if self.valtype == 'container':
			return True
		return False
	
	def set_name(self, name):
		self.name = name
	
	def setter(self, kind, value):
		if  self.has_property(kind):
			self.__dict__.update({kind: value})
		else:
			print "%s has no property %s" % (self.name, 'kind')
	
	def set_valtype(self, valtype):
		self.setter('valtype', valtype)
	
	def set_id(self, id):
		self.setter('id', id)
	
	def set_default(self, default):
		self.setter('default', default)
	
	def set_parent(self, parent):
		self.setter('parent', parent)
	
	def set_level(self, level):
		self.setter('level', level)
	
	def set_cardnality(self, cardnality):
		self.setter('cardnality', cardnality)
	
	def set_ordered(self, ordered):
		self.setter('ordered', ordered)
	
	def set_range(self, range):
		self.setter('range', range)
	
	def set_size(self, size):
		self.setter('size', size)
	

class DerivedType(BaseType):
	def __init__(self, name, basetype):
		self.name = name
		self.set_properties(basetype.get_properties())
	


class EDTD:
	def __init__(self, doctype):
		self.types = {
			'int': IntType(),
			'uint': UintType(),
			'float': FloatType(),
			'string': StringType(),
			'date': DateType(),
			'binary': BinaryType(),
			'container': ContainerType()
		}
		self.elements = {}
		#for use in checking to see if more then header block happens
		self.header_done = False 
		self.add_doctype('EBML')
		#self.add_doctype(doctype)
	
	def get_doctype_file(self, doctype):
		doctype_dir = os.path.expanduser('~/doctypes/')
		fn = os.path.join(doctype_dir, '%s.dtd' % doctype)
		return fn
	
	def add_doctype(self, doctype):
		# at the end of this, I want:
		# self.doctype
		# self.header (or something)
		# self.types
		# self.elements
		doctype_file = self.get_doctype_file(doctype)
		scanner = EDTD_Scanner()
		with open(doctype_file, 'r') as f:
			raw = f.read()
		tokens, remainder = scanner.scan(raw)
		if remainder != '':
			print "Failed to parse EDTD file."
			raise SyntaxError
		self.parse_tokens(tokens)
	
	def parse_base(self, tokens):
		while tokens.is_not_empty():
			block_token = tokens.get_next_token()
			if block_token.type == 'name':
				if block_token.string == 'declare':
					next = tokens.get_next_token()
					if next.type == 'name' and next.string == 'header':
						self.parse_header(tokens)
					else:
						print "Was expecting 'header', got %s" % next.string
						raise SyntaxError
				elif block_token.string == 'define':
					next = tokens.get_next_token()
					if next.type == 'name' and next.string == 'types':
						self.parse_types(tokens)
					elif next.type == 'name' and next.string == 'elements':
						self.parse_elements(tokens)
					else:
						print "Was expecting 'types' or 'elements'"
						print "got %s" % next.string
						raise SyntaxError
				else:
					print "Was expecting 'declare' or 'define',"
					print "got %s" % block_token.string
					raise SyntaxError
			else:
				print "Was expecting 'declare' or 'define',"
				print "got %s" % block_token.string
				raise SyntaxError
	
	def parse_header(self, tokens):
		if self.header_done == True:
			print "There can only be one header block."
			raise SyntaxError
		bracket_token = tokens.get_next_token()
		empty_header = True
		if bracket_token.type == 'rcurly':
			while True:
				name_token = tokens.get_next_token()
				if name_token.type == 'lcurly':
					if empty_header == True:
						print "Header block was empty."
						raise SyntaxError
					else:
						break
				empty_header = False
				if name_token.type  == 'name':
					if name_token.string in self.elements:
						setter = tokens.get_next_token()
						if setter.type == 'setter':
							value_token = tokens.get_next_token()
							if value_token.type in ('float', 'int', 'string'
								'date', 'binary'):
								self.elements[name_token].set_default(
									value_token)
							else:
								print 'Invalid type for a default: %s' % (
									value_token.type)
								raise SyntaxError
						else:
							print 'Was expecting ":=", got %s' % setter.string
							raise SyntaxError
					else:
						print "%s not already in elements." % name_token.string
						raise SyntaxError
				else:
					print 'Was expecting a name, got %s' % name_token.string
					raise SyntaxError
				end_token = tokens.get_next_token()
				if end_token.type == 'semicolon':
					pass
				else:
					print 'Was expecting a semicolon, got %s' % end_token.string
					raise SyntaxError
		else:
			print "Was expecting '{', got %s" % bracket_token.string
			raise SyntaxError
		self.header_done = True
	
	def parse_types(self, tokens):
		bracket_token = tokens.get_next_token()
		empty_types = True
		first = True
		if bracket_token.type == 'lcurly':
			while True:
				name_token = tokens.get_next_token()
				if name_token.type == 'semicolon':
					if first == True:
						print 'Was expecting a name, found ";"'
						raise SyntaxError
					else:
						name_token = tokens.get_next_token()
				if name_token.type == 'rcurly':
					if empty_types == True:
						print "Types block was empty."
						raise SyntaxError
					else:
						break
				empty_types = False
				if name_token.type == 'name':
					if name_token.string in self.types:
						setter_token = tokens.get_next_token()
						if setter_token.type = 'setter':
							base_token = tokens.get_next_token()
							if base_token.type = 'name':
								if base_token.string in self.types:
									self.types.update
								else:
									print "Unknown type: %s" % base_token.string
									raise SyntaxError
							else:
								print "Was expecting a name, got %s" % base_token.string
								raise SyntaxError
						else:
							print "Was expecting ':=', got %s" % setter.string
							raise SyntaxError
					else:
						print 'Unknown type: %s' % name_token.string
						raise SyntaxError
				else:
					print 'Was expecting a name, got %s' % name_token.string
					raise SyntaxError
				first = False
		else:
			print 'Was expecting "{", got %s' % bracket_token.string
			raise SyntaxError


class TokenClass:
	def __init__(self, kind, token):
		self.type = kind
		self.string = token
	
	def __repr__(self):
		return self.token
	
	def __cmp__(self, other):
		if self.token < other:
			return -1
		if self.token == other:
			return 0
		if self.token > other:
			return 1
	

class TokenList:
	def __init__(self, tlist):
		self.tlist = tlist
	
	def get_next_token(self):
		try:
			while True:
				next = self.tlist.pop(0)
				if next.type in ('whitespace', 'comment'):
					pass
				else:
					break
		except IndexError:
			print "Unexpectedly ran out of tokens."
			raise SyntaxError
		return next
	
	def is_not_empty(self):
		if self.tlist != []:
			return True
		return False
	

		
class EDTD_Scanner:
	def __init__(self):
		self.scanner = re.Scanner([
			(r'//[^\n\r]*(\n|\r)', self.comment),
			(r'/\*[^(/*)]*\*/', self.comment),
			(r'\b-?\d+\.\d+(e(\+|-)\d+)?\b', self.float),
			(r'\b-?\d+\b', self.int),
			(r'"[ -~]*"', self.string),
			(r'\b0x([A-Fa-f0-9]{2})+\b', self.binary),
			(r'\b([A-Fa-f0-9]{2})+\b', self.id),
			(r'\b[A-Za-z_][A-Za-z_0-9]+\b', self.name),
			(r'\b\d{8}T\d{2}:\d{2}\d{2}(\.\d+)?\b', self.date),
			(r'{', self.rcurly),
			(r'}', self.lcurly),
			(r'\[', self.rsquare),
			(r']', self.lsquare),
			(r':=', self.setter),
			(r'\.\.', self.range),
			(r'<=|>=|<|>', self.equality),
			(r'\*|\?|\+', self.cardnality),
			(r':', self.colon),
			(r',', self.comma),
			(r';', self.semicolon),
			(r'%', self.percent),
			(r'\s', self.whitespace)
		])
	
	def comment(self, scanner, token):
		return TokenClass('comment', token)
	
	def float(self, scanner, token):
		return TokenClass('float', float(token))
	
	def int(self, scanner, token):
		return TokenClass('int', int(token))
	
	def string(self, scanner, token):
		return TokenClass('string', token)
	
	def binary(self, scanner, token):
		token = token.decode('hex')
		return TokenClass('binary', token)
	
	def id(self, scanner, token):
		token = token.decode('hex')
		return TokenClass('id', token)
	
	def name(self, scanner, token):
		return TokenClass('name', token)
	
	def date(self, scanner, token):
		year = int(token[:4])
		month = int(token[4:6])
		day = int(token[6:8])
		hour = int(token[9:11])
		minute = int(token[12:14])
		second = int(token[15:17])
		if len(token) > 17:
			fraction = 	float(token[17:]) * 1000000
		else:
			fraction = 0
		epoch = datetime.datetime(2001, 1, 1, 0, 0, 0, 0)
		date = datetime.datetime(year, month, day, hour, minute, second, fraction)
		delta = date - epoch
		nano = 864 * 10**11 * delta.days
		nano += 10**9 delta.seconds
		nano += 10**3 delta.microseconds
		return TokenClass('date', nano)
	
	def rcurly(self, scanner, token):
		return TokenClass('rcurly', token)
	
	def lcurly(self, scanner, token):
		return TokenClass('lcurly', token)
	
	def rsquare(self, scanner, token):
		return TokenClass('rsquare', token)
	
	def lsquare(self, scanner, token):
		return TokenClass('lsquare', token)
	
	def setter(self, scanner, token):
		return TokenClass('setter', token)
	
	def range(self, scanner, token):
		return TokenClass('range', token)
	
	def equality(self, scanner, token):
		return TokenClass('equality', token)
	
	def cardnality(self, scanner, token):
		return TokenClass('cardnality', token)
	
	def colon(self, scanner, token):
		return TokenClass('colon', token)
	
	def comma(self, scanner, token):
		return TokenClass('comma', token)
	
	def semicolon(self, scanner, token):
		return TokenClass('semicolon', token)
	
	def percent(self, scanner, token):
		return TokenClass('percent', token)
	
	def whitespace(self, scanner, token):
		return TokenClass('whitespce', token)
	
	
	def scan(self, input):
		tokens, remainder = self.scanner.scan(input)
		return tokens, remainder
	


EDTD('matroska')