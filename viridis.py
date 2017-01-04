import numpy as np

COLORTABLE = np.loadtxt('viridis.txt', dtype=np.uint8)

def viridis(val):
    """
    takes a value between 0 and 1, returns an ndarray containing [R,G,B]
    no interpolation, just round to nearest uint8 for now
    """
    idx = int(np.clip(val,0,1)*255)
    return COLORTABLE[idx]
