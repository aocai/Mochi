import shlex, subprocess, io, os, sys, time
from subprocess import Popen, PIPE
#sys.path.append('../snowboy_source/snowboy/examples/Python3')
import snowboydecoder
import zmq
import pexpect

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
    
#workdir = "/home/pi/voice-recognizer-raspi/env/lib/python3.5/site-packages/googlesamples/assistant/grpc"
workdir = "/home/pi/Mochi"
mps_youtube = None
end = False
context = zmq.Context.instance()
assist_socket = context.socket(zmq.REQ)
assist_socket.connect('tcp://127.0.0.1:5555')
snowboy_socket = context.socket(zmq.REP)
snowboy_socket.bind('tcp://127.0.0.1:5556')
gesture_socket = context.socket(zmq.REP)
gesture_socket.bind('tcp://127.0.0.1:5557')

def transcribe_audio(client, speech_file):
    print("reading audio file..")
    with io.open(speech_file, 'rb') as audio_file:
        content = audio_file.read()
    
    print("configuring audio")
    audio = types.RecognitionAudio(content=content)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code='en-US')
    
    final_result = ""
    print("recognizing audio...")
    response = client.recognize(config, audio)
    print("processing result...")
    for result in response.results:
        print('Transcript: {}'.format(result.alternatives[0].transcript))
        final_result = result.alternatives[0].transcript
    
    print("transcription done")
    return final_result

def process_request(request):
    if "stop" in request:
        if "YouTube" in request:
            global mps_youtube
            mps_youtube.expect(">")
            mps_youtube.sendline("q")

        else:
            global end
            end = True
    elif "YouTube" in request:
        substr_index = min(request.index('YouTube') + 8, len(request))
        global mps_youtube
        mps_youtube.expect(">")
        mps_youtube.sendline("/"+request[substr_index:])
        mps_youtube.expect(">")
        mps_youtube.sendline("1")
    else:
        assist_socket.send_string('start')
        msg = assist_socket.recv_string()
        print(msg)
        
def record_audio():
    print("recording...")
    record = subprocess.call(['arecord', '-fS16_LE', '-r16000', '-d5', 'in.wav'], cwd=workdir)
    print("recording done")

def gestureDetect():
    print("gestureDetect started")

def main():
    client = speech.SpeechClient()
    p_snowboy = subprocess.Popen(['python', 'snowboy.py'])
    p_gesture = subprocess.Popen(['python', 'gesture_detect.py'])
    global mps_youtube
    mps_youtube = pexpect.spawn("mpsyt")
    
    global snowboy_socket
    poller = zmq.Poller()
    poller.register(snowboy_socket, zmq.POLLIN)
    poller.register(gesture_socket, zmq.POLLIN)
    
    global end
    while end is False:
        socks = dict(poller.poll())
        if snowboy_socket in socks and socks[snowboy_socket] == zmq.POLLIN:
            print("receiving message...")
            msg = snowboy_socket.recv_string()
            print(msg)
            if msg == 'detected':
                print('detected by voice')
                snowboydecoder.play_audio_file()
                record_audio()
                transcript = transcribe_audio(client, os.path.join(workdir,'in.wav'))
                process_request(transcript)
            if end is True:
                snowboy_socket.send_string('end')
                p_snowboy.wait()
            else:
                snowboy_socket.send_string('continue')
        if gesture_socket in socks and socks[gesture_socket] == zmq.POLLIN:
            msg = gesture_socket.recv_string()
            print(msg)
            if msg == 'detected':
                print('detected by gesture')
                snowboydecoder.play_audio_file()
                record_audio()
                transcript = transcribe_audio(client, os.path.join(workdir,'in.wav'))
                process_request(transcript)
            gesture_socket.send_string('continue')
    
    p_snowboy.kill()
    p_gesture.kill()
    if mps_youtube.isalive():
        mps_youtube.terminate()
	
if __name__ == '__main__':
    main()