#!/usr/local/bin/python

import argparse

def pos_to_offset(data, line, column):
	line -= 1
	column -= 1

	offset = 0

	for i in range(len(data)):
		if i == line:
			offset += column
			break

		offset += len(data[i])

	return offset

def offset_to_pos(data, offset):
	# to handle the last offset
	data[-1] += ' '

	cur_offset = 0
	line = 0
	column = 0
	for i in range(len(data)):
		line_len = len(data[i])
		if cur_offset + line_len > offset:
			line = i + 1
			column = offset - cur_offset + 1
			break

		cur_offset += line_len

	return line, column



def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("filename",  help="input filename")
	parser.add_argument("-p", help="convert position(line:column) to offset")
	parser.add_argument("-o", help="convert offset to position")
	parser.add_argument("-v", help="verbose", action="store_true")
	args = parser.parse_args()

	if not args.filename:
		print 'filename is required'
		exit(-1)

	if not args.p and not args.o:
		print 'select position or offset'
		exit(-1)

	filename = args.filename
	f = open(filename, 'r')
	#f = codecs.open(filename, encoding='utf-8')
	data = f.readlines()

	data = [line.decode('utf-8') for line in data]

	if args.p:
		line, column = args.p.split(':')
		offset = pos_to_offset(data, int(line), int(column))
		print offset

	elif args.o:
		offset = int(args.o)
		line, column = offset_to_pos(data, offset)
		print str(line) + ":" + str(column)

	f.close()

	if args.v:
		print 'offset =', offset
		print 'line =', line, ',column =' , column


if __name__ == "__main__":
	main()
