"""
This module defines class hierarchies for parsing of EBML doctype declarations.

It should not generally be neccesary to deal directly with anything here. 
"""

__license__ = """
is whatever
"""

__version__ = '1.0'

__author__ = 'Stephen Morton'

import os
import re
import datetime
from spark import Token, GenericScanner
from spark import GenericASTBuilder, AST, GenericASTTraversal

class BaseRange(object):
	def __init__(self, value):
		if type(value) == AST:
			value = self.tuplify(value)
		self.value = value
		self.check()
		self.make_test()
		self.set_string()
	
	def in_range(self, value):
		return self.test(value)
	
	def tuplify(self, ast):
		value_list = []
		kids = ast.get_children()
		for item in kids:
			if item.type == '..':
				value_list.append('..')
			elif item.type == 'comparison':
				value_list.append(item.attr)
			elif item.type == 'date':
				date = self.convert_date(item.attr)
				value_list.append(date)
			elif item.type == 'alphanumeric':
				value_list.append(int(item.attr))
			elif item.type == 'float':
				value_list.append(float(item.attr))
			else:
				raise SyntaxError('Unknown type for conversion: %s' % item)
		return tuple(value_list)
	
	def make_test(self):
		# n, ..n, n.., c n, n..n, n c .. c n
		if len(self.value) == 1:
			self.test = lambda x: x == self.value[0]
		elif len(self.value) == 2:
			if self.value[0] == '..':
				self.test = lambda x: x <= self.value[1]
			elif self.value[0] == '<=':
				self.test = lambda x: x <= self.value[1]
			elif self.value[0] == '<':
				self.test = lambda x: x < self.value[1]
			elif self.value[0] == '>':
				self.test = lambda x: x > self.value[1]
			elif self.value[0] == '>=':
				self.test = lambda x: x >= self.value[1]
			else:
				self.test = lambda x: x >= self.value[1]
		elif len(self.value) == 3:
			self.test = lambda x: self.value[0] <= x <= self.value[2]
		elif len(self.value) == 5:
			if self.value[1] == '<' and self.value[3] == '<':
				self.test = lambda x: self.value[0] < x < self.value[4]
			elif self.value[1] == '<=' and self.value[3] == '<':
				self.test = lambda x: self.value[0] <= x < self.value[4]
			elif self.value[1] == '<' and self.value[3] == '<=':
				self.test = lambda x: self.value[0] < x <= self.value[4]
			elif self.value[1] == '<=' and self.value[3] == '<=':
				self.test = lambda x: self.value[0] <= x <= self.value[4]
	
	def set_string(self):
		s = ''
		for item in self.value:
			s += str(item)
		self.string = s
	
	def __repr__(self):
		return 'BaseRange(%s)' % self.value
	

class UintRange(BaseRange):
	def __init__(self, value):
		BaseRange.__init__(self, value)
	
	def check(self):
		v = self.value
		assert len(v) in (1, 2, 3)
		assert type(v[0]) == int
		assert v[0] >= 0
		if len(v) > 1:
			assert v[1] == '..'
			if len(v) > 2:
				assert type(v[2]) == int
				assert v[2] >= v[0]
	

class IntRange(BaseRange):
	def __init__(self, value):
		BaseRange.__init__(self, value)
	
	def check(self):
		v = self.value
		assert len(v) in (1, 2, 3)
		if len(v) == 1:
			assert type(v[0]) == int
		elif len(v) == 2:
			if v[0] == "..":
				assert v[0] == '..'
				assert type(v[1]) == int
			else:
				assert type([v0]) == int
				assert v[1] == '..'
		elif len(v) == 3:
			assert type(v[0]) == int
			assert v[1] == '..'
			assert type(v[2]) == int
	

class FloatRange(BaseRange):
	def __init__(self, value):
		BaseRange.__init__(self, value)
	
	def check(self):
		v = self.value
		assert len(v) in (2, 5)
		if len(v) == 2:
			assert v[0] in ('<=', '<', '>', '<=')
			assert type(v[1]) == float
		elif len(v) == 5:
			assert type(v[0]) == float
			assert v[1] in ('<', '<=')
			assert v[2] == '..'
			assert v[3] in ('<', '<=')
			assert type(v[4]) == float
	

class DateRange(BaseRange):
	def __init__(self, value):
		BaseRange.__init__(self, value)
	
	def check(self):
		v = self.value
		assert len(v) in (2, 3)
		if len(v) == 2:
			if v[0] == '..':
				assert v[0] == '..'
				assert type(v[1]) == int
			else:
				assert type(v[0]) == int
				assert v[1] == '..'
		elif len(v) == 3:
			assert type(v[0]) == int
			assert v[1] == '..'
			assert type(v[2]) == int
	
	def convert_date(self, isodate):
		year = int(isodate[:4])
		month = int(isodate[4:6])
		day = int(isodate[6:8])
		hour = int(isodate[9:11])
		minute = int(isodate[12:14])
		second = int(isodate[15:17])
		if len(isodate) > 17:
			fraction = 	float(isodate[17:]) * 1000000
		else:
			fraction = 0
		epoch = datetime.datetime(2001, 1, 1, 0, 0, 0, 0)
		date = datetime.datetime(year, month, day, hour, minute, second, fraction)
		delta = date - epoch
		nano = 864 * 10**11 * delta.days
		nano += 10**9 * delta.seconds
		nano += 10**3 * delta.microseconds
		return nano
	

class ParentRange(BaseRange):
	def __init__(self, value):
		BaseRange.__init__(self, value)
	
	def tuplify(self, ast):
		value_list = []
		kids = ast.get_children()
		for item in kids:
			value_list.append(item.attr)
		return tuple(value_list)
	
	def check(self):
		v = self.value
		assert len(v) == 1
		assert check_match(r'[A-Za-z_][A-Za-z_0-9]+', v[0])
	
	def make_test(self):
		self.test = lambda x: x == self.values[0]

class LevelRange(BaseRange):
	def __init__(self, value):
		BaseRange.__init__(self, value)
	
	def check(self):
		v = self.value
		assert len(v) in (1, 2, 3)
		assert type(v[0]) == int
		assert v[0] >= 0
		if len(v) > 1:
			assert v[1] == '..'
			if len(v) > 2:
				assert type(v[2]) == int
				assert v[2] >= v[0]
	


class BaseList(object):
	def __init__(self, values):
		if type(values) == AST:
			values = self.listify(values)
		for item in values[:]:
			if type(item) in (tuple, AST):
				values.remove(item)
				item = self.process(item)
				values.append(item)
		self.values = values
	
	def listify(self, ast):
		assert ast.type == 'valuelist'
		return ast.get_children()
	
	def __repr__(self):
		return 'BaseList(%s)' % self.values
	

class ParentRangeList(BaseList):
	def __init__(self, values):
		BaseList.__init__(self, values)
	
	def process(self, item):
		return ParentRange(item)
	
	def append(self, item):
		self.values.append(self.process(item))
	

class UintRangeList(BaseList):
	def __init__(self, values):
		BaseList.__init__(self, values)
	
	def process(self, item):
		return UintRange(item)
	

class IntRangeList(BaseList):
	def __init__(self, values):
		BaseList.__init__(self, values)
	
	def process(self, item):
		return IntRange(item)
	

class FloatRangeList(BaseList):
	def __init__(self, values):
		BaseList.__init__(self, values)
	
	def process(self, item):
		return FloatRange(item)
	

class DateRangeList(BaseList):
	def __init__(self, values):
		BaseList.__init__(self, values)
	
	def process(self, item):
		return DateRange(item)
	


class TypeSetup(object):
	def __init__(self):
		self.additional_properties = set()
		self.checker_updates = {}
		self.values = {}
	
	def add_property(self, name):
		self.additional_properties.add(name)
	
	def set_checker(self, name, value):
		self.checker_updates.update({name: value})
	
	def __setattr__(self, name, value):
		if name in ('additional_properties', 'checker_updates', 'values'):
			object.__setattr__(self, name, value)
		else:
			self.values.update({name: value})
	
	def __getattr__(self, name):
		if name in ('additional_properties', 'checker_updates', 'values'):
			return object.__getattr__(self, name)
		else:
			return self.values[name]
	
	def update(self, other):
		for item in other.additional_properties:
			self.add_property(item)
		for key, value in other.checker_updates.items():
			self.set_checker(key, value)
		for key, value in other.values.items():
			self.__setattr__(key, value)
	
	def set_properties(self, properties):
		for kind, value in properties:
			self.__setattr__(kind, value)
	

class IntType(TypeSetup):
	def __init__(self):
		TypeSetup.__init__(self)
		self.add_property('default')
		self.set_checker('default', r'-?\d+|[A-Za-z_][A-Za-z_0-9]+')
		self.set_checker('range', IntRangeList)
		self.name = 'int'
		self.valtype = 'int'
		self.default = None
		self.range = None
		self.size = UintRangeList([(0,'..',8)])
	

class UintType(TypeSetup):
	def __init__(self):
		TypeSetup.__init__(self)
		self.add_property('default')
		self.set_checker('default', r'\d+|[A-Za-z_][A-Za-z_0-9]+')
		self.set_checker('range', UintRangeList)
		self.name = 'uint'
		self.valtype = 'uint'
		self.default = None
		self.range = None
		self.size = UintRangeList([(0,'..',8)])
	

class FloatType(TypeSetup):
	def __init__(self):
		TypeSetup.__init__(self)
		self.add_property('default')
		self.set_checker('default',
			r'-?\d+\.\d+(e(\+|-)\d+)?|[A-Za-z_][A-Za-z_0-9]+')
		self.set_checker('range', FloatRangeList)
		self.name = 'float'
		self.valtype = 'float'
		self.default = None
		self.range = None
		self.size = UintRangeList([(0),(4),(8),(10)])
	

class StringType(TypeSetup):
	def __init__(self):
		TypeSetup.__init__(self)
		self.add_property('default')
		self.set_checker('default', r'"[ -~]*"|[A-Za-z_][A-Za-z_0-9]+')
		self.set_checker('range', UintRangeList)
		self.name = 'string'
		self.valtype = 'string'
		self.default = None
		self.range = None
		self.size = None
	

class DateType(TypeSetup):
	def __init__(self):
		TypeSetup.__init__(self)
		self.add_property('default')
		self.set_checker('default',
			r'\d{8}T\d{2}:\d{2}\d{2}(\.\d+)?|-?\d+|[A-Za-z_][A-Za-z_0-9]+')
		self.set_checker('range', DateRangeList)
		self.name = 'date'
		self.valtype = 'date'
		self.default = None
		self.range = None
		self.size = UintRangeList([8])
	

class BinaryType(TypeSetup):
	def __init__(self):
		TypeSetup.__init__(self)
		self.add_property('default')
		self.set_checker('default',
			r'"[ -~]*"|0x([A-Fa-f0-9]{2})+|[A-Za-z_][A-Za-z_0-9]+')
		self.set_checker('range', UintRangeList)
		self.name = 'binary'
		self.valtype = 'binary'
		self.default = None
		self.range = UintRangeList([(0,'..',255)])
		self.size = None
	

class ContainerType(TypeSetup):
	def __init__(self):
		TypeSetup.__init__(self)
		self.add_property('ordered')
		self.add_property('children')
		self.name = 'container'
		self.valtype = 'container'
		self.range = None
		self.size = None
		self.ordered = True
		self.children = False
	

class DerivedType(TypeSetup):
	def __init__(self, name, basetype):
		TypeSetup.__init__(self)
		self.update(basetype)
		self.name = name
	


class ElementTypeClass(object):
	def __init__(self, name, hexid, basetype):
		self.property_check = {
			'name': r'[A-Za-z_][A-Za-z_0-9]+',
			'valtype': True, #depends on environment, checked elsewhere
			'id': True, # converstion to a hexstring would have failed if it was bad
			'default': None, #depends on type of element
			'value': None, # depends on type of element
			'parent': ParentRangeList,
			'level': LevelRange,
			'card': ['*', '?', '1', '+'],
			'ordered': [True, False],
			'range': None, #rangelist, depends on type of element
			'size': UintRangeList,
			'children': [True, False]
		}
		self.valid_property = self.property_check.keys()
		self.has_property = set(('name', 'valtype', 'range', 'size'))
		self.apply_setup(basetype)
		self.add_property('id')
		self.add_property('parent')
		self.add_property('level')
		self.add_property('card')
		self.add_property('value')
		self.set_checker('value', self.property_check['default'])
		self.name = name
		self.id = hexid
		self.parent = None
		self.level = None
		self.card = '?'
		self.value = None
	
	def apply_setup(self, setup):
		for item in setup.additional_properties:
			self.add_property(item)
		for key, value in setup.checker_updates.items():
			self.set_checker(key, value)
		for key, value in setup.values.items():
			self.__setattr__(key, value)
	
	def __repr__(self):
		return repr(dict([key, self.__dict__[key]] for key in self.has_property))
	
	def add_property(self, kind):
		if kind in self.valid_property:
			self.has_property.add(kind)
		else:
			raise ValueError("Invalid property: %s" % kind)
	
	def special(self, value):
		if value == 'children':
			self.children = True
		else:
			raise SyntaxError("Unknown special element: %%%s;" % value)
	
	def add_parent(self, parent):
		if self.parent:
			self.parent.append(parent)
		else:
			self.parent = ParentRangeList([parent])
	
	def get_properties(self):
		return zip(self.has_property, [self.__dict__[x] for x in self.has_property])
	
	def set_properties(self, properties):
		for kind, value in properties:
			self.__setattr__(kind, value)
	
	def is_container(self):
		if self.valtype == 'container':
			return True
		return False
	
	def set_checker(self, property_name, pattern):
		self.property_check.update({property_name: pattern})
	
	def __setattr__(self, name, value):
		if name in ('property_check', 'valid_property', 'has_property'):
			object.__setattr__(self, name, value)
		elif name in self.has_property:
			check = self.property_check[name]
			if universal_checker(check, value):
				object.__setattr__(self, name, value)
			else:
				raise SyntaxError('Invalid %s: %s' % (name, value))
		else:
			raise SyntaxError("%s has no property %s" % (self.name, name))
	
	def get_value(self):
		if self.value:
			return self.value
		else:
			return self.default
	


class DoctypeBase(object):
	def __init__(self):
		self.types = {
			'int': IntType(),
			'uint': UintType(),
			'float': FloatType(),
			'string': StringType(),
			'date': DateType(),
			'binary': BinaryType(),
			'container': ContainerType()
		}
		self.elements_name = {}
		self.elements_id = {}
		self.header_set = False
		self.add_doctype('EBML')
	
	def __repr__(self):
		return 'DoctypeBase()'
	
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
		scanner = EDTDScanner()
		with open(doctype_file, 'r') as f:
			raw = f.read()
		tokens = scanner.tokenize(raw)
		parser = EDTDParser()
		ast = parser.parse(tokens)
		CleanAST(ast)
		self.build_document(ast)
	
	def build_document(self, node):
		if not node.type == 'DTD':
			raise SyntaxError('Was expecting a DTD node, got %s' % node.type)
		for child in node.get_children():
			if child.type == 'headerblock':
				if self.header_set:
					raise SyntaxError("Only one header block can be declared.")
				else:
					self.build_headers(child)
			elif child.type == 'typesblock':
				self.build_types(child)
			elif child.type == 'elementblock':
				self.build_elements(child)
			else:
				raise SyntaxError("Was expecting a header, type, or elemement block, got %s" % child.type)
	
	def build_headers(self, node):
		if node.type == 'headerblock':
			for child in node.get_children():
				self.build_headers(child)
		elif node.type == 'headerlist':
			kids = node.get_children()
			for item in kids:
				self.build_header(item)
		else:
			raise SyntaxError('Was expecting a headerblock or a headerlist, got %s' % node.type)
	
	def build_header(self, node):
		if not node.type == 'headerdef':
			raise SyntaxError('Was expecting a headerdef node, got %s' % node.type)
		kids = node.get_children()
		if not len(kids) == 2:
			raise SyntaxError
		name = kids[0].attr
		value_node = kids[1]
		values = value_node.get_children()
		if not len(values) == 1:
			raise SyntaxError
		value = values[0].attr
		self.elements_name[name].value = value
	
	def build_types(self, node):
		if node.type == 'typesblock':
			for child in node.get_children():
				self.build_types(child)
		elif node.type == 'typeslist':
			kids = node.get_children()
			for item in kids:
				self.build_type(item)
		else:
			raise SyntaxError('Was expecting a typesblock or a typelist, got %s' % node.type)
	
	def build_type(self, node):
		if not node.type == 'typesdef':
			raise SyntaxError('Was expecting a typesdef node, got %s' % node.type)
		kids = node.get_children()
		name = kids[0].attr
		basetype = self.types[kids[1].attr]
		new_type = DerivedType(name, basetype)
		self.types.update({name: new_type})
		if len(kids) > 2:
			for item in kids[2:]:
				if not item.type == 'propertylist':
					raise SyntaxError('Was expecting a propertylist node, got %s' % item.type)
				properties = self.build_propertylist(item, new_type.valtype)
				new_type.set_properties(properties)
	
	def build_elements(self, node, parent=None):
		if node.type == 'elementblock':
			for child in node.get_children():
				self.build_elements(child)
		elif node.type == 'elementlist':
			kids = node.get_children()
			for item in kids:
				self.build_element(item, parent)
		else:
			raise SyntaxError('Was expecting an elementblock or an elementlist, got %s' % node.type)
	
	def build_element(self, node, parent):
		if not node.type == 'element':
			raise SyntaxError('Was expecting an element node, got %s' % node.type)
		kids = node.get_children()
		if kids[0] == '%':
			self.elements_name[parent].special(kids[1].attr)
		else:
			name = kids[0].attr
			id_string = kids[1].attr
			hexid = id_string.decode('hex')
			type_class = self.types[kids[2].attr]
			element = ElementTypeClass(name, hexid, type_class)
			self.elements_name.update({name: element})
			self.elements_id.update({hexid: element})
			if len(kids) > 3:
				for item in kids[3:]:
					if item.type == 'propertylist':
						properties = self.build_propertylist(item, element.valtype)
						element.set_properties(properties)
					elif item.type == 'elementlist':
						if element.valtype == 'container':
							self.build_elements(item, parent=name)
						else:
							raise SyntaxError("Only container elements can have children elements.")
					else:
						raise SyntaxError("Was expecting a property or element list, got %s" % item.type)
			if parent:
				element.add_parent(parent)
	
	def build_propertylist(self, node, valtype):
		if not node.type == 'propertylist':
			raise SyntaxError('Was expecting a propertylist node, got %s' % node.type)
		properties = []
		for property_node in node.get_children():
			if property_node.type == 'property':
				kids = property_node.get_children()
				name = kids[0].attr
				valuelist = kids[1]
				value_nodes = valuelist.get_children()
				if name == 'range':
					if valtype in ('uint', 'binary', 'string'):
						value = UintRangeList(valuelist)
					elif valtype == 'int':
						value = IntRangeList(valuelist)
					elif valtype == 'float':
						value = FloatRangeList(valuelist)
					elif valtype == 'date':
						value = DateRangeList(valuelist)
					else:
						raise SyntaxError("Types derived from %s do not support ranges" % valtype)
					properties.append(('range', value))
				elif name == 'parent':
					properties.append(('parent', ParentRangeList(valuelist)))
				elif name == 'size':
					properties.append(('size', UintRangeList(valuelist)))
				elif len(value_nodes) == 1:
					value_node = value_nodes[0]
					kids = value_node.get_children()
					if name == 'level':
						value = LevelRange(value_node)
						properties.append(('level', value))
					elif len(kids) == 1:
						value = kids[0]
						if name == 'def':
							properties.append(('default', value.attr))
						elif name == 'ordered':
							if value.attr in ('yes', '1'):
								properties.append(('ordered', True))
							elif value.attr in ('no', '0'):
								properties.append(('ordered', False))
						elif name == 'card':
							properties.append(('card', value.attr))
					else:
						raise SyntaxError("The property %s doesn't accept a range." % name)
				else:
					raise SyntaxError("The property %s doesn't accept a list of values." % name)
		return properties
	
	def get_ids(self):
		return self.elements_id.keys()
	
	def lookup(self, value):
		if value in self.elements_id:
			return self.elements_id[value]
		else:
			return self.elements_name[value]
	

class Doctype(DoctypeBase):
	def __init__(self, doctype):
		DoctypeBase.__init__(self)
		self.doctype_name = doctype
		self.add_doctype(doctype)
	
	def __repr__(self):
		return 'Doctype(%r)' % self.doctype_name
	


class EDTDScannerBase(GenericScanner):
	'Low priority tokens are found in this class'
	def __init__(self):
		GenericScanner.__init__(self)
	
	def  tokenize(self, input):
		self.rv = []
		GenericScanner.tokenize(self, input)
		return self.rv
	
	def t_line_comment(self, s):
		r'//[^\n\r]*(\n|\r)'
		pass
	
	def t_block_comment(self, s):
		r'/\*[^(/*)]*\*/'
		pass
	
	def t_whitespace(self, s):
		r'\s'
		pass
	
	def t_string(self, s):
		r'"[ -~]*"'
		t = Token(type='string', attr=s)
		self.rv.append(t)
	
	def t_binary(self, s):
		r'\b0x([A-Fa-f0-9]{2})+\b'
		t = Token(type='binary', attr=s)
		self.rv.append(t)
	
	def t_alphanumeric(self, s):
		r'\b([A-Fa-f0-9]{2})+\b|-?\b\d+\b|\b[A-Za-z_][A-Za-z_0-9]+\b'
		t = Token(type='alphanumeric', attr=s)
		self.rv.append(t)
	
	def t_date(self, s):
		r'\d{8}T\d{2}:\d{2}\d{2}(\.\d+)?'
		t = Token(type='date', attr=s)
		self.rv.append(t)
	
	def t_bracket(self, s):
		r'{|}|\[|]'
		t = Token(type=s)
		self.rv.append(t)
	
	def t_range(self, s):
		r'\.\.'
		t = Token(type=s)
		self.rv.append(t)
	
	def t_comparison(self, s):
		r'<=|>=|<|>'
		t = Token(type='comparison', attr=s)
		self.rv.append(t)
	
	def t_sep(self, s):
		r':|;|,'
		t = Token(type=s)
		self.rv.append(t)
	
	def t_cardnality(self, s):
		r'\*|\?|\+'
		t = Token(type='cardnality', attr=s)
		self.rv.append(t)
	
	def t_percent(self, s):
		r'%'
		t = Token(type=s)
		self.rv.append(t)
	

class EDTDScanner(EDTDScannerBase):
	'High priority tokens found in this class'
	def __init__(self):
		EDTDScannerBase.__init__(self)
	
	def t_setter(self, s):
		r':='
		t = Token(type=s)
		self.rv.append(t)
	
	def t_float(self, s):
		r'-?\b\d+\.\d+(e(\+|-)\d+)?\b'
		t = Token(type='float', attr=s)
		self.rv.append(t)
	
	def t_reserved(self, s):
		r'\bdefine\b|\bdeclare\b|\bheader\b|\btypes\b|\belements\b'
		t = Token(type=s)
		self.rv.append(t)
	

class EDTDParser(GenericASTBuilder):
	def __init__(self, AST=AST, start='DTD'):
		GenericASTBuilder.__init__(self, AST, start)
	
	def p_DTD(self, args):
		'''
			DTD ::= elementblock DTD
			DTD ::= headerblock DTD
			DTD ::= typesblock DTD
			DTD ::= headerblock
			DTD ::= typesblock
			DTD ::= elementblock
			elementblock ::= define elements { elementlist }
			elementlist ::= element elementlist
			elementlist ::= element
			element ::= alphanumeric := alphanumeric alphanumeric ;
			element ::= alphanumeric := alphanumeric alphanumeric [ propertylist ]
			element ::= alphanumeric := alphanumeric alphanumeric [ propertylist ] ;
			element ::= alphanumeric := alphanumeric alphanumeric [ propertylist ] { elementlist }
			element ::= alphanumeric := alphanumeric alphanumeric { elementlist }
			element ::= % alphanumeric ;
			propertylist ::= property propertylist
			propertylist ::= property
			property ::= alphanumeric : valuelist ;
			valuelist ::= value , valuelist
			valuelist ::= value
			value ::= alphanumeric
			value ::= string
			value ::= cardnality
			value ::= float
			value ::= alphanumeric .. alphanumeric
			value ::= .. alphanumeric
			value ::= alphanumeric ..
			value ::= date .. date
			value ::= .. date
			value ::= date ..
			value ::= comparison float
			value ::= float comparison .. comparison float
			headerblock ::= declare header { headerlist }
			headerlist ::= headerdef headerlist
			headerlist ::= headerdef
			headerdef ::= alphanumeric := value ;
			typesblock ::= define types { typeslist }
			typeslist ::= typesdef typeslist
			typeslist ::= typesdef
			typesdef ::= alphanumeric := alphanumeric [ propertylist ]
			typesdef ::= alphanumeric := alphanumeric [ propertylist ] ;
			typesdef ::= alphanumeric := alphanumeric ;
		'''
	

class CleanAST(GenericASTTraversal):
	def __init__(self, ast):
		GenericASTTraversal.__init__(self, ast)
		self.postorder()
	
	def n_DTD(self, node):
		for child in node.get_children():
			if child.type == 'DTD':
				for item in child.get_children():
					node.add(item)
				node.remove(child)
	
	def n_elementlist(self, node):
		for child in node.get_children():
			if child.type == 'elementlist':
				for item in child.get_children():
					node.add(item)
				node.remove(child)
	
	def n_propertylist(self, node):
		for child in node.get_children():
			if child.type == 'propertylist':
				for item in child.get_children():
					node.add(item)
				node.remove(child)
	
	def n_headerlist(self, node):
		for child in node.get_children():
			if child.type == 'headerlist':
				for item in child.get_children():
					node.add(item)
				node.remove(child)
	
	def n_typeslist(self, node):
		for child in node.get_children():
			if child.type == 'typeslist':
				for item in child.get_children():
					node.add(item)
				node.remove(child)
	
	def n_propertylist(self, node):
		for child in node.get_children():
			if child.type == 'propertylist':
				for item in child.get_children():
					node.add(item)
				node.remove(child)
	
	def n_valuelist(self, node):
		kids = node.get_children()
		for child in kids:
			if child.type == ',':
				node.remove(child)
			elif child.type == 'valuelist':
				self.n_rangelist(child) # process this first to remove commas
				for item in child.get_children():
					node.add(item)
				node.remove(child)
	
	def n_headerblock(self, node):
		kids = node.get_children()
		node.remove(kids[0]) # 'declare'
		node.remove(kids[1]) # 'header'
		node.remove(kids[2]) # '{'
		# node 3 is the headerlist
		node.remove(kids[4]) # '}'
	
	def n_typesblock(self, node):
		kids = node.get_children()
		node.remove(kids[0]) # 'define'
		node.remove(kids[1]) # 'types'
		node.remove(kids[2]) # '{'
		# node 3 is the typeslist
		node.remove(kids[4]) # '}'
	
	def n_elementblock(self, node):
		kids = node.get_children()
		node.remove(kids[0]) # 'define'
		node.remove(kids[1]) # 'elements'
		node.remove(kids[2]) # '{'
		# node 3 is the elementlist
		node.remove(kids[4]) # '}'
	
	def n_headerdef(self, node):
		kids = node.get_children()
		# node 0 is header element name
		node.remove(kids[1]) # ':='
		# node 2 is the value
		node.remove(kids[3]) # ';'
	
	def n_typesdef(self, node):
		kids = node.get_children()
		# node 0 is the name
		node.remove(kids[1]) # ':='
		# node 2 is the base type
		node.remove(kids[3]) # I don't know what it is yet, but I don't want it
		if kids[3].type == ';': # if it was a ';', it ends now.
			pass
		else: # node 3 was a '['
			# node 4 is the propertylist
			node.remove(kids[5]) # ']'
			if len(kids) > 6: # is there more?
				node.remove(kids[6]) # ';'
	
	def n_element(self, node):
		kids = node.get_children()
		if kids[0].type == '%': #check for special case
			# node 0 is the %
			# node 1 is probably 'children', although I haven't checked that yet
			node.remove(kids[2]) # ';'
		else:
			# node 0 is the name
			node.remove(kids[1]) # ':='
			# node 2 is the ID string
			# node 3 is the type
			node.remove(kids[4]) # I don't know what it is yet, but I don't want it
			if kids[4].type == ';': # if it was a ';', it ends now.
				pass
			elif kids[4].type == '[': # if it was '[', there's a propertylist
				# node 5 is the propertylist
				node.remove(kids[6]) # ']'
				if len(kids) > 7: # is there more?
					node.remove(kids[7]) # either ';' or '{'
					if kids[7].type == ';': #ends now
						pass
					else: # it must be '{'
						# node 8 is the elementlist
						node.remove(kids[9]) # '}'
			else: # node 4 was a '{'
				# node 5 is an elementlist
				node.remove(kids[6])
	
	def n_property(self, node):
		kids = node.get_children()
		# node 0 is the property name
		node.remove(kids[1]) # ':'
		# node 2 is the value
		node.remove(kids[3]) # ';'
	


def universal_checker(check, value):
	if value == None:
		return True
	elif type(check) == str:
		return check_match(check, value)
	elif type(check) == list:
		return value in check
	elif type(check) == type:
		return type(value) == check
	elif type(check) == bool:
		return check
	else:
		raise SyntaxError("I don't understand the checker %s" % check)

def check_match(pattern, string):
	if len(string) == re.match(pattern, string).span()[1]:
		return True
	return False
