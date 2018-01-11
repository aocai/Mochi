import cv2
import time
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
import zmq

context = zmq.Context.instance()
socket = context.socket(zmq.REQ)
socket.connect('tcp://127.0.0.1:5557')

def PiGestureDetect():
    camera = PiCamera()
    camera.resolution = (640,480)
    camera.framerate = 15
    camera.vflip = True

    rawCapture = PiRGBArray(camera,size=(640,480))

    fgbg = cv2.createBackgroundSubtractorMOG2(varThreshold=80,detectShadows=False)

    while camera.analog_gain <= 1:
        time.sleep(0.1)
    camera.shutter_speed = camera.exposure_speed
    camera.exposure_mode = 'off'
    g = camera.awb_gains
    camera.awb_mode = 'off'
    camera.awb_gains = g

    camera.capture(rawCapture,format="bgr")
    img_background = rawCapture.array
    rawCapture.truncate(0)
    
    for frame in camera.capture_continuous(rawCapture,format="bgr",use_video_port=True):
        image = frame.array
        
        #Color segmentation:
        #gray_image = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        #blur = cv2.GaussianBlur(gray_image,(5,5),0)
        #ret,thresh = cv2.threshold(blur,70,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
        
        #hsv_image = cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
        #thresh = cv2.inRange(hsv_image, (0,0.28*255,0), (25,0.68*255,255))
        
        fgmask = fgbg.apply(image,learningRate=0.001)
        fgmask = cv2.medianBlur(fgmask, 7)
        
        thresh,contours,hierarchy = cv2.findContours(fgmask,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        drawing = np.zeros(image.shape,np.uint8)
        max_area = 0 
        ci = -1
    
        for i in range(len(contours)):
            cnt = contours[i]
            area = cv2.contourArea(cnt)
            if (area > max_area):
                max_area = area
                ci = i
    
        if contours and ci >= 0:
            cnt = contours[ci]
            hull = cv2.convexHull(cnt)
            moments = cv2.moments(cnt)
            if moments['m00'] != 0:
                cx = int(moments['m10']/moments['m00'])
                cy = int(moments['m01']/moments['m00'])
            centr = (cx,cy)
            cv2.circle(image,centr,5,[0,0,255],2)
            
            #cv2.drawContours(drawing,[cnt],0,(0,255,0),2)
            #cv2.drawContours(drawing,[hull],0,(0,0,255),2)
        
            cnt = cv2.approxPolyDP(cnt,0.01*cv2.arcLength(cnt,True),True)
            hull = cv2.convexHull(cnt,returnPoints=False)
        
            defects = cv2.convexityDefects(cnt,hull)
            if defects is not None:
                for j in range(defects.shape[0]):
                    s,e,f,d = defects[j,0]
                    start = tuple(cnt[s][0])
                    end = tuple(cnt[e][0])
                    far = tuple(cnt[f][0])
                    
                    cv2.line(image,start,end,[0,255,0],2)
                    cv2.circle(image,far,5,[0,0,255],-1)

                if j >= 4 and cv2.contourArea(cnt) > 30000:
                    socket.send_string("detected")
                    msg = socket.recv_string()
                    print(msg)
                    print(j)
        
        #cv2.imshow("Thresh",thresh)
        #cv2.imshow("Output",drawing)
        cv2.imshow("Input",image)
        
        key = cv2.waitKey(1) & 0xFF
        
        rawCapture.truncate(0)
        if key == ord('q'):
            break

if __name__ == '__main__':
    PiGestureDetect()