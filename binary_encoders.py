def encode_binary(rawstring):
	hexstring = rawstring.decode('hex')
	return hexstring

def decode_binary(hexstring):
	return hexstring.encode('hex')

def isodate_to_nanoseconds(rawstring):
	year = int(rawstring[:4])
	month = int(rawstring[4:6])
	day = int(rawstring[6:8])
	hour = int(rawstring[9:11])
	minute = int(rawstring[12:14])
	second = int(rawstring[15:17])
	if len(rawstring) > 17:
		fraction = 	float(rawstring[17:]) * 1000000
	else:
		fraction = 0
	epoch = datetime.datetime(2001, 1, 1, 0, 0, 0, 0)
	date = datetime.datetime(year, month, day, hour, minute, second, fraction)
	delta = date - epoch
	nano = 864 * 10**11 * delta.days
	nano += 10**9 * delta.seconds
	nano += 10**3 * delta.microseconds
	return nano

def decode_uint(hexstring):
	bytes = [ord(byte) for byte in hexstring]
	bytes.reverse()
	value = 0
	for place, byte in enumerate(bytes):
		value += byte * 16**(2 * place)
	return value

def decode_ieee_float(hexstring):
	print "floats aren't working yet, but going on anyway."
	return hexstring

def decode_date(hexstring):
	nanoseconds = decode_twos_complement(hexstring)
	return nanoseconds

def decode_twos_complement(hexstring):
	
	return hexstring

def get_bits(hexstring):
	allbits = []
	for byte in hexstring:
		b = bin(ord(byte))
		bits = [x for x in b[2:]]
		while len(bits) < 8:
			bits.insert(0, '0')
		allbits += bits
	return allbits
