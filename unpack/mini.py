# -*- coding:utf-8 -*-
import util.rawutil as rawutil
from util.filesystem import *
from util.utils import ClsFunc, byterepr
from unpack._formats import get_ext

MINI_TABLE_STRUCT = '2sH /1[I] I 128a'


class extractmini (ClsFunc, rawutil.TypeReader):
	def main(self, filename, data, verbose, endian, opts={}):
		self.byteorder = endian
		self.verbose = verbose
		self.outdir = make_outdir(filename)
		offsets = self.read_table(data)
		files = self.extract_files(offsets, data)
		self.write_files(files)
	
	def read_table(self, data):
		tbl = self.unpack_from(MINI_TABLE_STRUCT, data, 0)
		magic = tbl[0]
		print('File magic: %s' % byterepr(magic))
		self.filecount = tbl[1]
		offsets = [el[0] for el in tbl[2]]
		offsets.append(tbl[3])
		if self.verbose:
			print('File count: %d' % self.filecount)
		return offsets
	
	def extract_files(self, offsets, data):
		files = []
		for i in range(0, self.filecount):  #the last is total file length
			data.seek(offsets[i])
			length = offsets[i + 1] - offsets[i]
			files.append(data.read(length))
		return files
	
	def write_files(self, files):
		for i, filedata in enumerate(files):
			ext = get_ext(filedata)
			name = path(self.outdir, '%d%s' % (i, ext))
			bwrite(filedata, name)
