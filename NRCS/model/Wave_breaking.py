import numpy as np
from NRCS import constants as const
from NRCS import spec
from NRCS import spread
from NRCS.spec.kudryavtsev05 import param
from NRCS.spec.kudryavtsev05 import spec_peak

def Wave_breaking(kr, theta, azimuth, u_10, fetch, spec_name = 'elfouhaily'):
    """
    :param kp:
    :param kr:
    :param theta:
    :param azi:
    :param u_10:
    :param fetch:
    :return:
    """

    nphi = theta.shape[0]

    # Spectral model
    # Omni directional spectrum model name
    specf = spec.models[spec_name]

    # NRCS of plumes
    wb0 = np.exp(-np.tan(theta)**2/const.Swb)/(np.cos(theta)**4*const.Swb)+const.yitawb/const.Swb # Kudryavstev 2003a equation (60)
    knb = min(const.br*kr, const.kwb)

    # tilting transfer function
    dtheta = theta[1]-theta[0]
    Mwb = np.gradient(wb0, dtheta)/wb0

    # distribution function
    phi1 = (np.arange(nphi) * np.pi / nphi).reshape(1, nphi)-np.pi / 2 # in radians azimuth of breaking surface area: -pi/2,pi/2
    nk = 1024
    K = np.linspace(10 * spec_peak(u_10, fetch), knb, nk)
#     K = np.linspace(spec_peak(u_10, fetch), knb, nk)

    if spec_name == 'elfouhaily':
        # Directional spectrum model name
        spreadf = spread.models[spec_name]
        Bkdir = specf(K.reshape(nk, 1), u_10, fetch) * spreadf(K.reshape(nk, 1), phi1, u_10, fetch) * K.reshape(nk, 1)**2
    else:
        Bkdir = specf(K.reshape(nk, 1), u_10, fetch, phi1)

    n, alpha = param(K, u_10)
    lamda = (Bkdir/alpha.reshape(nk, 1))**(n.reshape(nk, 1)+1)/(2*K.reshape(nk, 1)) # distribution of breaking front lengths
    lamda_k = np.trapz(lamda, phi1, axis=1)
    lamda = np.trapz(lamda, K, axis=0)
    lamda_k = np.trapz(lamda_k, K)
    q = const.cq * lamda_k

    if np.shape(azimuth) == ():
        Awb = np.trapz(np.cos(phi1-azimuth)*lamda, phi1, axis=1)/lamda_k
    else:
        nazi = azimuth.shape[0]
        Awb = np.trapz(np.cos(phi1 - azimuth.reshape(nazi, 1)) * lamda, phi1, axis=1) / lamda_k
        Awb = Awb.reshape(nazi, 1)

    WB = wb0.reshape(1, nphi)*(1+Mwb.reshape(1, nphi)*const.theta_wb*Awb)
    return WB, q
