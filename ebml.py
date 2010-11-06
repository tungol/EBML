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
    def __init__(self, doctype=None, filename=None, offset=None, **kwargs):
        self.doctype = doctype
        self.filename = filename
        self.hexid_offset = offset
        self.dummy = False
        if filename == offset == None:
            self.dummy = True
            self.hexid = kwargs['hexid']
            if self.hexid == 'document': # special case for document psudo-element
                self.valtype = 'document'
                self.name = 'document'
                self.hexid_offset = 0
    
    def __repr__(self):
        return "Reference(%r, %r, %r)" % (self.doctype, self.filename, 
            self.hexid_offset)
    
    def __str__(self):
        return "<%s bytes at offset %s in file %s>" % (self.total_length, 
                self.hexid_offset, self.filename)
    
    def __getattr__(self, key):
        if key == 'name':
            self.name = self.doctype.lookup(self.hexid).name
            return self.name
        if key == 'payload_length':
            if self.dummy:
                return 0
            return self.get_payload_length()
        if key == 'hexid_length':
            if self.dummy:
                return 0
            return len(self.hexid.bytes) 
        elif key == 'end':
            self.end = self.total_length + self.hexid_offset
            return self.end
        elif key == 'size_offset':
            self.size_offset = self.hexid_offset + self.hexid_length
            return self.size_offset
        elif key == 'size_length':
            if self.dummy:
                return 0
            return self.get_size_length()
        elif key == 'payload_offset':
            self.payload_offset = self.size_offset + self.size_length
            return self.payload_offset
        elif key == 'total_length':
            self.total_length = self.hexid_length + self.size_length + self.payload_length
            return self.total_length
        elif key == 'valtype':
            self.valtype = self.doctype.lookup(self.hexid).valtype
            return self.valtype
        elif key == 'payload':
            return self.get_payload()
        elif key == 'hexid':
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
                if bitstring.Bits(bytes=hexid) in self.doctype.get_ids():
                    break
        self.hexid_length = len(hexid)
        self.hexid = bitstring.Bits(bytes=hexid)
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
        bits = bitstring.Bits(filename=self.filename, offset=self.size_offset*8,
            length=self.size_length*8)
        for pos, bit in enumerate(bits):
            if bit == 1:
                index = pos
                break
        bits = bits[index + 1:]
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
    
    def encode_payload(self, payload=None):
        if payload == None:
            payload = self.payload
        if self.valtype == 'uint':
            if payload == 0 and self.payload_length == 0:
                return bitstring.Bits()
            minlength = int(math.ceil(math.log(payload+1, 2)/8))
            if minlength < self.payload_length:
                return bitstring.Bits(uint=payload, 
                    length=self.payload_length*8)
            else:
                return bitstring.Bits(uint=payload, length=minlength*8)
        elif self.valtype == 'int':
            if payload == 0 and self.payload_length == 0:
                return bitstring.Bits()
            elif payload < 0:
                minlength = int(math.ceil(math.log(math.fabs(payload), 2)/8) + 1)
            else:
                minlength = int(math.ceil(math.log(payload+1, 2)/8) + 1)
            if minlength < self.payload_length:
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
    
    def encode_payload_length(self, payload_length):
        minlength = int(math.ceil(math.log(payload_length+1, 2)))
        length = int(math.ceil(minlength / 7))
        bytelength = max((length, self.size_length))
        padding_amount = (((bytelength * 8) - minlength) - bytelength)
        tmp_str = ('0' * (bytelength-1)) + '1' + ('0' * padding_amount)
        number = bitstring.Bits(uint=payload_length, length=minlength)
        width = bitstring.Bits(bin=tmp_str)
        return width + number
    
    def write(self, new_payload, new_offset=0, commit=True, filename=None):
        return_tuple = self.process_payload(new_payload, new_offset)
        processed_payload = return_tuple[0]
        encoded_payload_length = return_tuple[1]
        length_delta = return_tuple[2]
        end_offset = new_offset + self.total_length + length_delta
        if commit:
            if encoded_payload_length != bitstring.Bits(): # check for removal
                self.write_to_file(processed_payload, encoded_payload_length, 
                    new_offset, filename)
            self.total_length += length_delta
            return ('okay', end_offset, self.total_length)
        return ('pending', end_offset, self.total_length + length_delta)
    
    def process_payload(self, input_payload, new_offset):
        if self.name == 'Void':
            return self.process_void(input_payload, new_offset)
        else:
            return self.process_normal(input_payload, new_offset)
    
    def process_void(self, input_payload, new_offset):
        if self.dummy:
            return self.process_normal(input_payload, new_offset)
        remove_self = False
        offset_delta = new_offset - self.hexid_offset
        if self.total_length - 2 >= offset_delta:
            length_delta = -offset_delta # shrink by the offset_delta
        elif self.total_length - 1 == offset_delta:
            length_delta = -(self.total_length - 2) # can't have a void of length 1
        else: # void is equal to or smaller than shift
            remove_self = True # dissapear entirely
            length_delta = -self.total_length
        if not remove_self:
            total_length = self.total_length + length_delta
            size_length = int(math.ceil(math.log(total_length+1, 2)))
            size_length_delta = self.size_length - size_length
            payload_length_delta = length_delta - size_length_delta
            payload_length = self.payload_length + payload_length_delta
            encoded_payload_length = self.encode_payload_length(payload_length)
            output_payload = bitstring.Bits(bytes=('\x00' * payload_length))
        else:
            output_payload = bitstring.Bits()
            encoded_payload_length = bitstring.Bits()
        return (output_payload, encoded_payload_length, length_delta)
    
    def process_normal(self, input_payload, new_offset):
        if self.valtype in ('container', 'document'):
            output_payload = input_payload
            size_length = self.size_length
            while True:
                child_results = []
                shift = new_offset + self.hexid_length + size_length
                for child in input_payload:
                    result = child.write(shift, False)
                    child_results.append(result)
                    shift = result[1]
                payload_length = sum([result[2] for result in child_results])
                minlength = int(math.ceil(math.log(payload_length+1, 2)))
                length = int(math.ceil(minlength / 7))
                bytelength = max((length, self.size_length))
                if bytelength == size_length:
                    break
                else:
                    size_length = bytelength
        else:
            output_payload = self.encode_payload(input_payload)
            payload_length = len(output_payload.bytes)
        encoded_payload_length = self.encode_payload_length(payload_length)
        payload_length_delta = payload_length - self.payload_length
        size_length_delta = len(encoded_payload_length.bytes) - self.size_length
        length_delta = payload_length_delta + size_length_delta
        if self.dummy:
            length_delta += len(self.hexid)
        return (output_payload, encoded_payload_length, length_delta)
    
    def write_to_file(self, payload, payload_length, offset, filename):
        if self.valtype == 'document':
            shift = offset
            for child in payload:
                result = child.write(shift, True, filename)
                shift = result[1]
        elif self.valtype == 'container':
            try:
                with open(filename, 'r+b') as file:
                    file.seek(offset)
                    file.write(self.hexid.bytes)
                    file.write(payload_length.bytes)
            except IOError:
                with open(filename, 'w+b') as file:
                    file.seek(offset)
                    file.write(self.hexid.bytes)
                    file.write(payload_length.bytes)
            shift = offset + self.hexid_length + len(payload_length.bytes)
            for child in payload:
                result = child.write(shift, True, filename)
                shift = result[1]
        else:
            with open(filename, 'r+b') as file:
                file.seek(offset)
                file.write(self.hexid.bytes)
                file.write(payload_length.bytes)
                file.write(payload.bytes)
        if self.valtype != 'container':
            self.dummy = False
    

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
        #if self.has_reference():
        #    return 'Element(%r, %r)' % (self.doctype, self.reference)
        #else:
        #    return 'Element(%r, %r, %r)' % (self.doctype, self.hexid, self.payload)
        return self.__str__()
    
    def __str__(self):
        if 'payload' in dir(self):
            return '<%s element, %r>' % (self.name, self.payload)
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
        elif key == 'dummy_reference':
            self.dummy_reference = Reference(self.doctype, hexid=self.hexid)
            return self.dummy_reference
        elif key == 'reference':
            return self.dummy_reference
        elif key == 'total_length':
            return self.reference.total_length
        elif key == 'end':
            return self.reference.end
        else:
            raise AttributeError
    
    def __iter__(self):
        if self.valtype == 'container':
            return iter(self.payload)
    
    def has_write_pending(self, new_offset=None, new_filename=None):
        if self.has_reference():
            if new_filename != None:
                if new_filename != self.reference.filename:
                    return True
            if new_offset != None:
                if new_offset != self.reference.hexid_offset:
                    return True
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
    
    def write(self, new_offset=0, commit=True, filename=None):
        if self.has_write_pending(new_offset, filename):
            if not self.has_reference():
                reference = Reference(self.doctype, hexid=self.hexid)
            else:
                reference = self.reference
            result = reference.write(self.payload, new_offset, commit, filename)
            if result[0] == 'okay':
                # if a write occured on a dummy reference, it's now a real
                # reference and we need to be sure to save it.
                self.reference = reference
        else:
            result = ('unneeded', self.end, self.total_length)
        return result
    

class EBML(Element):
    def __init__(self, filename, doctype=None):
        self.filename = filename
        if doctype:
            self.doctype == dtd.Doctype(doctype)
        else:
            self.doctype = dtd.DoctypeBase()
            self.find_document_type()
        self.build_document()
        self.hexid = 'document'
        
    
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
        self.payload = ContainerPayload()
        offset = 0
        end = os.stat(self.filename).st_size
        while True:
            if offset == end:
                break
            elif offset > end:
                raise EOFError('Went too far, file is damaged.')
            reference = Reference(self.doctype, self.filename, offset)
            element = Element(self.doctype, reference)
            self.payload.append(element, keep_reference=True)
            offset = reference.end
    
    def write(self, filename):
        Element.write(self, filename=filename)
    


if __name__ == '__main__':
    a = EBML('test.mkv')
    a.payload[0].payload[1].payload = 2
    a.write('writetest.mkv')
    b = EBML('writetest.mkv')
#    EBML('test2.mkv')
#    EBML('test3.mkv')
