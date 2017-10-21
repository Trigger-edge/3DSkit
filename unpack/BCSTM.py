# -*- coding:utf-8 -*-
from util import error
import util.rawutil as rawutil
from util.fileops import *
from util.funcops import ClsFunc
from util.wavy import WAV

rawutil.register_sub('S', '(2H2I)')  #sized refs
rawutil.register_sub('R', '(2HI)')  #references
rawutil.register_sub('T', 'I/p1[2HI]')  #ref table

BCSTM_HEADER_STRUCT = '4s2H 2I2H SSS'
BCSTM_INFO_STRUCT = '4sI RRR (4B11IR) TT $'
BCSTM_TRACK_INFO_STRUCT = '2BHR I/p1[B]'
BCSTM_DSPADPCM_INFO_STRUCT = '(16H) (2B2H) (2B2H) H'
BCSTM_IMAADPCM_INFO_STRUCT = '(H2B) (H2B)'

PCM8 = 0
PCM16 = 1
DSPADPCM = 2
IMAADPCM = 3


class SizedRef (object):
	def __init__(self, data):
		self.id = data[0]
		self.offset = data[2] if data[2] != 0xffffffff else None
		self.size = data[3]
	
	def getdata(self, data):
		return data[self.offset: self.offset + self.size]


class Reference (object):
	def __init__(self, data):
		self.id = data[0]
		self.offset = self.offset = data[2] if data[2] != 0xffffffff else None
	
	def __add__(self, obj):
		self.offset += obj
		return self


class TrackInfo (object):
	def __init__(self, data):
		self.volume = data[0]
		self.pan = data[1]
		self.channelindex = data[5]


class DSPADPCMContext (object):
	def __init__(self, data):
		self.predictor = data[0] >> 4
		self.scale = data[0] & 0x0f
		self.previous_sample = data[2]
		self.second_previous_sample = data[3]


class DSPADPCMInfo (object):
	def __init__(self, data):
		self.param = data[0]
		self.context = DSPADPCMContext(data[2])
		self.loopcontext = DSPADPCMContext(data[3])


class IMAADPCMContext (object):
	def __init__(self, data):
		self.data = data[0]
		self.table_index = data[1]


class IMAADPCMInfo (object):
	def __init__(self, data):
		self.context = IMAADPCMContext(data[0])
		self.loopcontext = IMAADPCMContext(data[1])


class extractBCSTM (ClsFunc, rawutil.TypeReader):
	def main(self, filename, data, opts={}):
		outname = make_outfile(filename, 'wav')
		self.read_header(data)
		self.readINFO()
	
	def read_header(self, data):
		bom = rawutil.unpack_from('>H', data, 4)[0]
		self.byteorder = '<' if bom == 0xfffe else '>'
		hdata = self.unpack_from(BCSTM_HEADER_STRUCT, data)
		magic = hdata[0]
		if magic != b'CSTM':
			error('Invalid magic %s' % magic)
		bom = hdata[1]
		headerlen = hdata[2]
		self.version = hdata[3]
		filesize = hdata[4]
		blockcount = hdata[5]  #Should be 3
		padding = hdata[6]
		inforef = SizedRef(hdata[7])
		seekref = SizedRef(hdata[8])
		dataref = SizedRef(hdata[9])
		self.info = inforef.getdata(data)
		self.seek = seekref.getdata(data)
		self.data = dataref.getdata(data)
	
	def readINFO(self):
		data = self.unpack(BCSTM_INFO_STRUCT, self.info)
		info = self.info
		streaminforef = Reference(data[2])
		trackinforef = Reference(data[3]) + streaminforef.offset
		channelinforef = Reference(data[4]) + streaminforef.offset
		streaminfo = data[5]
		self.read_streaminfo(streaminfo)
		trackinforeftable = [Reference(el) + trackinforef.offset + 4 for el in data[7]]
		channelinforeftable = [Reference(el) + channelinforef.offset + 4 for el in data[9]]
		self.trackinfo = []
		for ref in trackinforeftable:
			offset = ref.offset
			if offset is not None:
				self.trackinfo.append(TrackInfo(self.unpack_from(BCSTM_TRACK_INFO_STRUCT, self.info, offset)))
		self.channelinfo = []
		for ref in channelinforeftable:
			offset = ref.offset
			if offset is not None:
				adpcminforef = Reference(self.unpack_from('R', self.info, offset)[0])
				if self.codec == DSPADPCM:
					adpcminfo = DSPADPCMInfo(self.unpack_from(BCSTM_DSPADPCM_INFO_STRUCT, self.info, adpcminforef.offset + offset))
					self.channelinfo.append(adpcminfo)
				elif self.codec == IMAADPCM:
					adpcminfo = IMAADPCMInfo(self.unpack_from(BCSTM_IMAADPCM_INFO_STRUCT, self.info, adpcminforef.offset + offset))
					self.channelinfo.append(adpcminfo)
				else:
					self.channelinfo.append(None)
	
	def read_streaminfo(self, data):
		self.codec = data[0]
		self.islooping = bool(data[1])
		self.channel_count = data[2]
		self.sample_rate = data[4]
		self.loop_start = data[5]
		self.loop_end = data[6]
		self.sampleblock_count = data[7]
		self.sampleblock_size = data[8]
		self.sampleblock_samplecount = data[9]
		self.last_sampleblock_size = data[10]
		self.last_sampleblock_samplecount = data[11]
		self.last_sampleblock_paddedsize = data[12]
		self.seek_datasize = data[13]
		self.seek_interval_samplecount = data[14]
