
import sys
import numpy as np
import scipy.integrate as sp

import ekf

## vicon2xhatInitial(yk) - returns initial state and covariance estimate based on a single initial vicon measurement
#   @param yk [x,y,z,b0,b1,b2,b3] vicon measurement of position and attitude (quaternion)
def vicon2xhatInitial(yk):
    # xhat: [(x,y,z)_inertial (v1,v2,v3)_body, quat_body]
    xhat = np.zeros(10)
    # initialize position to vicon
    xhat[0:3] = yk[0:3].copy()
    # initialize attitude to vicon
    xhat[6:10] = yk[3:7].copy()
    # velocity is already zero
    var_x = 0.001*0.001#meters^2
    var_vel = 0.1*0.1
    var_quat = 0.01*0.01
    # covariance estimate
    Pk = np.diag([var_x, var_x, var_x, var_vel, var_vel, var_vel, var_quat, var_quat, var_quat, var_quat])
    Pk = Pk + 1e-12*np.ones((10,10))
    return (xhat,Pk)

## stateDerivative(x,t,u) - returns the derivative of the filter state at a given time, for particular control values
#
#   @param x state given by ( position(inertial), velocity(body frame), quaternion )
#   @param t current time
#   @param u "control" given by (accelerometer measurement, gyro measurement, gravity constant)
def stateDerivative(x,t,u):
    f = np.zeros((2,))
    f[0] = x[1]
    f[1] = -2.0*(1.5/1.0)*(x[0]*x[0]-1.0)*x[1]-(1.2/1.0)*x[0]
    return f

def stateDerivativeEKF(x,t,u):
    f = np.zeros((2,))
    f[0] = x[1]
    f[1] = -2.0*(1.0/1.0)*(x[0]*x[0]-1.0)*x[1]-(1.0/1.0)*x[0]
    return f

## stateGradient(x,t,u) - returns the gradient of the derivative of the filter state w.r.t. the filter state
#
#   @param x state given by ( position(inertial), velocity(body frame), quaternion )
#   @param t current time
#   @param u "control" given by (accelerometer measurement, gyro measurement, gravity constant)
def stateGradient(x,t,u):
    Fk = np.zeros((2,2))
    Fk = np.array([ [0.0,1.0],[-4.0*x[0]*x[1]-1.0,-2.0*(x[0]*x[0]-1.0)] ])
    return Fk

## stateProcessInfluence(x,t,u) - returns the process noise matrix on the derivative of the filter state
#
#   @param x state given by ( position(inertial), velocity(body frame), quaternion )
#   @param t current time
#   @param u "control" given by (accelerometer measurement, gyro measurement, gravity constant)
def stateProcessInfluence(x,t,u):
    # numerically validated for one case
    Gk = np.array([ [0.0],[1.0] ])
    return Gk

## viconFunction(x,t) - returns the expectation of a vicon measurement, given the state and time
#
#   @param x state given by ( position(inertial), velocity(body frame), quaternion )
#   @param t current time
def measFunction(x,t):
    yexp = np.array([ x[0] ])
    return yexp

## viconGradient(x,t) - returns the gradient of the expectation given the state and time
#
#   @param x state given by ( position(inertial), velocity(body frame), quaternion )
#   @param t current time
def measGradient(x,t):
    Hk = np.array([ [1.0,0.0] ])
    return Hk

def initFunction(yinit):
    return (np.array([ yinit[0],0.0 ]),np.identity(2)*1000.0+1e-6*np.ones((2,2)))

def simMeasurementFunction(xk,t):
    ymeas = np.array([ xk[0]+ np.random.normal(0.0,0.01) ])
    return ymeas

def main(argin='./'):
    # output file
    FOUT = open('python_ekf_test.csv','w')
    FOUT.write('t,x1,x2,ymeas,x1hat,x2hat,P11,P22\n');

    # initialize EKF
    #Qkin = np.array([[0.2]])
    Qkin = np.array([[20.0]])
    EKF = ekf.ekf(2,1,stateDerivativeEKF,stateGradient,stateProcessInfluence,Qk = Qkin)

    Rkin = np.array([ [0.0001] ])

    dt = 0.01
    tfin = 10.0
    nSteps = int(tfin/dt)
    tsim = 0.0

    xk = np.array([1.0,0.0])
    yk = measFunction(xk,tsim)
    EKF.init(yk,initFunction,tsim)

    print(nSteps)

    for k in range(nSteps):
        # propagte
        EKF.propagate(dt)

        # simulate
        y = sp.odeint(stateDerivative,xk,np.array([tsim,tsim+dt]),args=([],) )
        xk = y[-1,:].copy()

        # update time
        tsim = tsim + dt
        # measurement
        ymeas = simMeasurementFunction(xk,tsim)
        # update EKF
        EKF.update(tsim,ymeas,measFunction,measGradient,Rkin)
        # log to file
        FOUT.write('%f,%f,%f,%f,%f,%f,%f,%f\n' % (tsim,xk[0],xk[1],ymeas[0],EKF.xhat[0],EKF.xhat[1],EKF.Pk[0,0],EKF.Pk[1,1]) )

    FOUT.close()
    return

if __name__ == '__main__':
    main()
