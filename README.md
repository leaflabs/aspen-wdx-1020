# aspen-wdx-1020
Aspen-powered Willow Data eXplorer for 1020-channel datasets

![screenshot_aspenwdx](https://static1.squarespace.com/static/5786c0a51b631ba257b3055a/t/586eab2be58c623df69a19ce/1483648619018/screenshot_aspenwdx.png?format=2500w)

www.leaflabs.com/willow

www.leaflabs.com/aspen

## Overview

Aspen is an effort to integrate scalable solutions for the Analysis, Storage, and Processing of
large scientific datasets. Among other things, this enables researchers to explore their data
remotely using a thin client interface to a large database with compute-on-storage capabilities.

aspen-wdx-1020 is a demonstration of this idea, applied specifically to 1020-channel Willow datasets.

## Setup

1. Install dependencies. Both server and client require python and numpy. If you're just running
the client, you'll also need:

    ```bash
    $ sudo apt-get install python-qt4 python-pyqtgraph
    ```

and to run the server:

    $ sudo apt-get install python-scipy python-twisted
    $ sudo pip install h5py

2. Start the server:

    ```bash
    $ ./server.py bigData.h5
    ```

(NOTE: this application works only with Willow-formatted HDF5 files)

3. Open the client:

    ```bash
    $ ./client.py
    ```

If the server is running on another machine, give its address as first argument. For example:

    $ ./client.py 10.0.1.19


## Usage

In the top-left of the client window, you'll see the 1020-channel probe map. A small translucent rectangle
shows which channels are currently selected. Click and drag this window around to select a dataslab.

In the top-right, you'll find the time scrubber, representing the entire duration of the datafile.
Click and drag to navigate in time.

On the bottom, you'll find the view port, showing voltage traces from the 12 channels selected on the
probe map. 2 seconds are shown by default; units are are microvolts vs. seconds. You can zoom
horizontally using the mousewheel, zoom vertically using ctrl-shift-mousewheel, and click and drag
to pan.

Click F1 for help, including more keyboard shortcuts.

