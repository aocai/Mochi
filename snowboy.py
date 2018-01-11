import sys
#sys.path.append('/home/pi/snowboy_source/snowboy/examples/Python3')
import snowboydecoder
import zmq

end = False

def snowboy_notify(socket):
    print('sending detected')
    socket.send_string('detected')
    msg = socket.recv_string()
    print(msg)
    
    if msg == 'end':
        global end
        end = True
    
def interrupt_callback():
    global end
    return end

def snowboyDetect():
    context = zmq.Context.instance()
    socket = context.socket(zmq.REQ)
    socket.connect('tcp://127.0.0.1:5556')
    
    #model = '/home/pi/snowboy/Hey_Mochi.pmdl'
    model = './resources/Hey_Mochi.pmdl'
    detector = snowboydecoder.HotwordDetector(model, sensitivity=0.5)
    
    print('Listening...')
    detector.start(detected_callback=lambda: snowboy_notify(socket),
                   interrupt_check=interrupt_callback,
                   sleep_time=0.03)
    
    detector.terminate()
    
if __name__ == '__main__':
    snowboyDetect()