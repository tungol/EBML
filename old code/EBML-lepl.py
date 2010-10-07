import os
import re
import datetime
from lepl import Token, Separator, Delayed

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
	


class EDTD_lexer:
	# no support for block comments r'/\*[^(/*)]*\*/'
	t_comment = Token(r'//[^\n\r]*(\n|\r)')
	t_float = Token(r'\b-?\d+\.\d+(e(\+|-)\d+)?\b')
	t_int = Token(r'\b-?\d+\b', self.int)
	t_string = Token(r'"[ -~]*"')
	t_binary = Token(r'\b0x([A-Fa-f0-9]{2})+\b')
	t_id = Token(r'\b([A-Fa-f0-9]{2})+\b')
	t_name = Token(r'\b[A-Za-z_][A-Za-z_0-9]+\b')
	t_date = Token(r'\b\d{8}T\d{2}:\d{2}\d{2}(\.\d+)?\b')
	t_rcurly = Token(r'{')
	t_lcurly = Token(r'}')
	t_rsquare = Token(r'\[')
	t_lsquare = Token(r']')
	t_setter = Token(r':=')
	t_range = Token(r'\.\.')
	t_equality = Token(r'<=|>=|<|>')
	t_cardnality = Token(r'\*|\?|\+')
	t_colon = Token(r':')
	t_comma = Token(r',')
	t_semicolon = Token(r';')
	t_percent = Token(r'%')
	t_whitespace = Token(r'\s')
	skip = t_whitespace | t_comment
	delement = Delayed()
	with Separator(skip[:]):
		define_eblock = name('define') & name('elements')
		eblock = define_eblock & rcurly & delement[:] % lcurly
		estatement = 

		
class EDTD_Scanner:	
	def binary(self, scanner, token):
		token = token.decode('hex')
		return TokenClass('binary', token)
	
	def id(self, scanner, token):
		token = token.decode('hex')
		return TokenClass('id', token)
	
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
	


EDTD('matroska')