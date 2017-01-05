#!/usr/bin/env python2

import numpy as np
import h5py
import cPickle

from scipy import signal as dsp
import multiprocessing as mp

from time import time as WALLCLOCK

import signal

import twisted.internet.protocol as tip
import twisted.internet.reactor as tir

#### globals

MICROVOLTS_PER_COUNT = np.float16(0.195)

lowcut = 300.
highcut = 9500.
fs = 3e4
order = 5
FILTERB, FILTERA = dsp.butter(order, [lowcut*2./fs, highcut*2./fs], btype='band')

#### helper functions

def filterSlab(slab):
    """
    NOTE: this upcasts to np.float64
    """
    return dsp.lfilter(FILTERB, FILTERA, slab, axis=1)

def calculateActivity(slab, wpipe):
    nchan = slab.shape[0]
    slab = (np.array(slab, dtype='float')-2**15)*MICROVOLTS_PER_COUNT
    filteredSlab = filterSlab(slab)
    threshold = (-4.5*np.median(np.abs(filteredSlab), axis=1)/0.6745) # from J.P. Kinney
    activity = np.zeros(nchan)
    for i in range(nchan):
        activity[i] = np.sum((filteredSlab[i,:] < threshold[i]))
    wpipe.send(activity)

class PipedProcess(mp.Process):
    def __init__(self, rpipe, **kwargs):
        mp.Process.__init__(self, **kwargs)
        self.rpipe = rpipe

def chanMap_linearToWillow(channels_linear, probeMap_dict):
    willowChans = []
    for linChan in channels_linear:
        shank = linChan // 204
        row = linChan % 102
        col = linChan & 0x1
        willowChans.append(probeMap_dict[shank, row, col]) 
    return willowChans

def MPGenerator(dataSlab, nproc):
    nchan = dataSlab.shape[0]
    nchanPerProc = nchan // nproc
    splitter = np.arange(1,nproc) * nchanPerProc
    for subSlab in np.split(dataSlab, splitter):
        yield subSlab

#### main twisted code

CACHE_RAW = None
CACHE_TIME = None

class AspenProtocol(tip.Protocol):

    def __init__(self):

        self.activity = np.zeros(1020, dtype=np.float16)

        self.chans1020_linear = np.arange(1020, dtype=int)
        self.chans1020_willow = np.array(chanMap_linearToWillow(self.chans1020_linear, probeMap_dict),
                                dtype=np.uint16)

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
            #self.handleDataRequest(dataCoords)
        elif msg[0] == 'activity':
            time = int(msg[1])
            tir.callInThread(self.handleActivityRequest, time)
            #self.handleActivityRequest(time)
        else:
            print 'unexpected keyword:', msg[0]

    def handleDataRequest(self, dataCoords):
        global CACHE_RAW, CACHE_TIME
        # send channel list
        chan = int(dataCoords[0])
        time = int(dataCoords[1])
        filt = (dataCoords[2] == 'True')
        channels_linear = range(chan, chan+12)
        channels_willow = np.array(chanMap_linearToWillow(channels_linear, probeMap_dict),
                                dtype=np.uint16)
        self.transport.write(channels_willow.tostring())

        # IO (first, attempt to retrieve raw data from cache)
        if time == CACHE_TIME:
            print 'cache hit!'
            data = CACHE_RAW
        else:
            print 'cache miss! ', time, CACHE_TIME
            data = np.array(FILE['channel_data'][(1024 * time):(1024 * (time + 60000))],
                            dtype=np.uint16).reshape((-1, 1024)).transpose()

        # slab selection and conversion
        dataSlab = (np.array(data[channels_willow,:], dtype=np.float16)-np.float16(2**15))*MICROVOLTS_PER_COUNT

        # filtering
        if filt:
            dataSlab = np.array(filterSlab(dataSlab), dtype=np.float16)
        self.transport.write(dataSlab.tostring())

        # save to cache
        CACHE_RAW = data
        CACHE_TIME = time

    def handleActivityRequest(self, time):
        # IO (first, attempt to retrieve raw data from cache)
        if time == CACHE_TIME:
            print 'cache hit!'
            data = CACHE_RAW
        else:
            print 'cache miss! ', time, CACHE_TIME
            data = np.array(FILE['channel_data'][(1024 * time):(1024 * (time + 60000))],
                            dtype=np.uint16).reshape((-1, 1024)).transpose()

        dataSlab = data[self.chans1020_willow,:] # re-ordering

        # (multi) processing
        procs = []
        for subSlab in MPGenerator(dataSlab, NCPU):
            rpipe, wpipe = mp.Pipe()
            procs.append(PipedProcess(rpipe, target=calculateActivity,
                            args=(subSlab, wpipe)))
        for pp in procs: pp.start()
        cursor = 0
        for i, pp in enumerate(procs):
            pp.join()
            activitySlice = pp.rpipe.recv()
            nchan_slice = activitySlice.shape[0]
            self.activity[cursor:(cursor+nchan_slice)] = activitySlice
            cursor += nchan_slice
        self.transport.write(self.activity.tostring())

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
    NCPU = mp.cpu_count()
    PORT = 8000
    print '\nNCPU = %d' % NCPU
    print 'Serving on Port %d\n' % PORT
    tir.listenTCP(PORT, AspenFactory())
    tir.run()
