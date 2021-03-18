import socket
import sys
import threading

import bpy

HOST = "localhost"
PORT = 8081
BUFFER_SIZE = 1024
PATH_MAX = 4096


class BlenderHIPSConnectThread(threading.Thread):
    args = []
    running = False
    serversocket = None

    def __init__(self):

        threading.Thread.__init__(self)

    def start(self):
        # Start the thread.
        print('Starting HIPS to Blender connect thread')
        self.running = True
        self.daemon = True
        threading.Thread.start(self)

    def stop(self):
        # Stop the thread.
        print('Stopping HIPS to Blender connect thread')
        self.running = False
        self.serversocket.settimeout(0.1)
        self.serversocket.close()
        del self.serversocket
        print('Done stopping HIPS to Blender connect thread')

    def run(self):
        # Setup the network socket.
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.bind((HOST, PORT))
        self.serversocket.listen(1)
        print(f"Blender listening on {HOST}:{PORT}")

        # Receive new data from the client.
        while self.running:
            try:
                connection, address = self.serversocket.accept()
                buf = connection.recv(PATH_MAX)

                myargs = buf.split(b'\x00')
                myargs.pop()
                self.args = []
                for i, element in enumerate(myargs):
                    self.args.append(element.decode('UTF-8'))
            except socket.timeout:
                pass


class BlenderHIPSConnection(bpy.types.Operator):
    bl_idname = 'hips.connect'
    bl_label = 'Connect to HIPS'

    thread = None
    timer = None
    is_disposed = False

    def modal(self, context, event):
        # print(event.type)
        if self.is_disposed:
            self.thread.stop()
            context.window_manager.event_timer_remove(self.timer)
            return {'CANCELLED'}

        # Update the object with the received data.
        if event.type == 'TIMER':
            if len(self.thread.args) > 0:
                print("Executing:", self.thread.args[0])
                try:
                    sys.argv = self.thread.args
                    execfile(self.thread.args[0])
                    self.thread.args = []
                except:
                    import traceback
                    traceback.print_exc()

        return {'PASS_THROUGH'}

    def dispose(self):
        self.is_disposed = True

    def execute(self, context):
        self.thread = BlenderHIPSConnectThread()
        self.thread.start()
        self.timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def execfile(filepath):
    global_namespace = {
        "__file__": filepath,
        "__name__": "__main__",
    }
    with open(filepath, 'rb') as file:
        exec(compile(file.read(), filepath, 'exec'), global_namespace)


def register():
    bpy.utils.register_class(BlenderHIPSConnection)


if __name__ == "__main__":
    register()
    bpy.ops.hips.connect()
