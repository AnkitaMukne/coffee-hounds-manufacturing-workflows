import cv2
import numpy as np
#import matplotlib.pyplot as plt 

cam = cv2.VideoCapture(0)

# Capture one frame
ret, frame = cam.read()
r=0
g=0

if ret:
    cv2.imshow("Captured", frame)         
    cv2.imwrite("captured_image.png", frame) 
    hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) 

    #red_lower = np.array([100, 50, 100], np.uint8) 
    #red_upper = np.array([180, 255, 255], np.uint8) 
    #red_mask = cv2.inRange(hsvFrame, red_lower, red_upper) 

    red_lower1 = np.array([0, 50, 100], np.uint8) 
    red_upper1 = np.array([10, 255, 255], np.uint8) 
    red_lower2 = np.array([170, 50, 100], np.uint8) 
    red_upper2 = np.array([180, 255, 255], np.uint8) 
    red_mask1 = cv2.inRange(hsvFrame, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsvFrame, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2) 

	# Set range for green color and 
	# define mask 
    green_lower = np.array([25, 100, 100], np.uint8) 
    green_upper = np.array([102, 255, 255], np.uint8) 
    green_mask = cv2.inRange(hsvFrame, green_lower, green_upper) 

    kernel = np.ones((5, 5), "uint8") 
	
	# For red color 
    red_mask = cv2.dilate(red_mask, kernel) 
    res_red = cv2.bitwise_and(frame, frame, 
							mask = red_mask) 
	
	# For green color 
    green_mask = cv2.dilate(green_mask, kernel) 
    res_green = cv2.bitwise_and(frame, frame, 
								mask = green_mask) 
    
    # Creating contour to track red color
    contours, hierarchy = cv2.findContours(red_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for pic, contour in enumerate(contours):
        area_r = cv2.contourArea(contour)
        if (area_r > 300):
            x, y, w, h = cv2.boundingRect(contour)
            frame = cv2.rectangle(frame, (x, y),
                                       (x + w, y + h),
                                       (0, 0, 255), 2)

            cv2.putText(frame, "Red Colour", (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (0, 0, 255))
            r=r+area_r
            print("Red colour detected at coordinates ")

    # Creating contour to track green color
    contours, hierarchy = cv2.findContours(green_mask,
                                           cv2.RETR_TREE,
                                           cv2.CHAIN_APPROX_SIMPLE)

    for pic, contour in enumerate(contours):
        area_g = cv2.contourArea(contour)
        if (area_g > 300):
            x, y, w, h = cv2.boundingRect(contour)
            frame = cv2.rectangle(frame, (x, y),
                                       (x + w, y + h),
                                       (0, 255, 0), 2)

            cv2.putText(frame, "Green Colour", (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (0, 255, 0))
            g=g+area_g
            print("Green colour detected at coordinates ")
    
    if(r>g):
        print("Red colour detected")
    elif(g>r):
        print("Green colour detected")
    else:
        print("No colour detected")
    cv2.imshow("Color Detection", frame)
    cv2.waitKey(0)                      
    cv2.destroyAllWindows()       
    
else:
    print("Failed to capture image.")

cam.release()