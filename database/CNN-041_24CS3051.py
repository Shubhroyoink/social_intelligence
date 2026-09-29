import numpy as np

I=np.array([
    [4,4,8,9,8,3,0],
    [6,4,9,0,6,3,5],
    [3,0,7,0,2,7,5],
    [5,4,3,8,5,8,4],
    [0,5,7,6,1,6,6],
    [0,0,6,0,9,9,2],
    [8,2,4,1,2,7,2]
])

K=np.array([
    [-1,0,1],
    [-2,0,2],
    [-1,0,1]
])

def conv2d(image, kernel,stride=1, padding=1):
    image=np.pad(image,((padding,padding),(padding,padding)))
    
    H,W =image.shape
    kH,kW= kernel.shape
    
    out_H= (H-kH)//stride +1
    out_W= (W-kW)//stride+1
    
    output=np.zeroes((out_H,out_W))
    
    