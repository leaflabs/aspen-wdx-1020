#!/usr/bin/env python2

import numpy as np
import h5py
import cPickle

from scipy import signal

import twisted.internet.protocol as tip
import twisted.internet.reactor as tir

MICROVOLTS_PER_COUNT = np.float16(0.195)

def chanMap_linearToWillow(channels_linear, probeMap_dict):
    willowChans = []
    for linChan in channels_linear:
        shank = linChan // 204
        row = linChan % 102
        col = linChan & 0x1
        willowChans.append(probeMap_dict[shank, row, col]) 
    return willowChans

class AspenProtocol(tip.Protocol):

    def __init__(self):
        lowcut = 300.
        highcut = 9500.
        fs = 3e4
        order = 5
        self.b, self.a = signal.butter(order, [lowcut*2./fs, highcut*2./fs], btype='band')

    def dataReceived(self, payload):
        print 'payload = ', payload
        msg = payload.split(',')
        if msg[0] == 'nsamples':
            nsamples = (FILE['channel_data'].shape[0] / 1024)
            nsamples_payload = np.array(nsamples, dtype=np.uint64).tostring()
            self.transport.write(nsamples_payload)
        elif msg[0] == 'dataSlab':
            dataCoords = msg[1:]
            tir.callInThread(self.handleDataRequest, dataCoords)
        elif msg[0] == 'activity':
            tir.callInThread(self.handleActivityRequest)
        else:
            print 'unexpected keyword:', msg[0]

    def handleDataRequest(self, dataCoords):
        # send channel list
        chan = int(dataCoords[0])
        time = int(dataCoords[1])
        filt = (dataCoords[2] == 'True')
        channels_linear = range(chan, chan+12)
        channels_willow = np.array(chanMap_linearToWillow(channels_linear, probeMap_dict),
                                dtype=np.uint16)
        self.transport.write(channels_willow.tostring())

        # IO, filt, send dataslab
        data = np.array(FILE['channel_data'][(1024 * time):(1024 * (time + 60000))],
                        dtype=np.uint16).reshape((-1, 1024)).transpose()
        dataSlab = (np.array(data[channels_willow,:], dtype=np.float16)-np.float16(2**15))*MICROVOLTS_PER_COUNT
        if filt:
            dataSlab = np.array(signal.lfilter(self.b, self.a, dataSlab), dtype=np.float16)
        print '\nSending:', dataSlab.dtype, dataSlab.shape, dataSlab[0,:10], '\n'
        self.transport.write(dataSlab.tostring())

    def handleActivityRequest(self):
        pass # TODO

class AspenFactory(tip.ServerFactory):

    def buildProtocol(self, addr):
        return AspenProtocol()

if __name__ == '__main__':
    import sys
    if len(sys.argv)>1:
        FILE = h5py.File(sys.argv[1])
    else:
        print 'Usage: ./server.py <path/to/datafile.h5>'
        sys.exit(1)
    probeMap_dict = cPickle.load(open('probeMap_1020_level2_20160402.p', 'rb'))
    port = 8000
    tir.listenTCP(port, AspenFactory())
    tir.run()
