from NRCS import constants as const
from NRCS import spec
from NRCS import spread
import numpy as np
from stereoid.oceans.bistatic_pol import elfouhaily

def eq_br(k, kr, theta_eq, eq_azi, u_10, fetch, spec_name, polarization):
    """
    all the angles are in radians
    :param k:
    :param kr:
    :param theta:
    :param azimuth:
    :param u_10:
    :param fetch:
    :param spec_name:
    :return:
    """

    nphi = theta_eq.shape[0]
    nk = k.shape[0]
    nazi = eq_azi.shape[0]
    kd = const.d*kr

    # Spectral model
    # Omni directional spectrum model name
    specf = spec.models[spec_name]


    # # Sea surface slope in the direction of incidence angle
    phi_inc = np.linspace(-np.pi, np.pi, nazi*2)# in radians wave direction relative to the incidence plane
    if spec_name == 'elfouhaily':
        # Directional spectrum model name
        spreadf = spread.models[spec_name]
        Skdir_ni = specf(k.reshape(nk, 1), u_10, fetch) * spreadf(k.reshape(nk, 1), phi_inc, u_10, fetch)/k.reshape(nk, 1) # equation 45
    else:
        Skdir_ni = specf(k.reshape(nk, 1), u_10, fetch, phi_inc) / k.reshape(nk, 1) ** 4
    ni = np.trapz(k.reshape(nk, 1)**3*np.cos(phi_inc)**2*Skdir_ni, phi_inc, axis=1)
    ni2 = np.trapz(ni[k >= kd], k[k >= kd])

    nn = 89 * 2 * np.pi / 180
    ni = (np.arange(nk) * nn / nk).reshape(1, nk) - nn / 2
    ni = ni.reshape(nk, 1)
    ni = np.tan(ni)
    P = np.exp(-0.5 * (ni - np.mean(ni)) ** 2 / ni2) / np.sqrt(2 * np.pi * ni2)
    #  the range of the sea surface slope
    angle_index = np.logical_and(-3 * 180 * np.arctan(np.sqrt(ni2)) / np.pi < np.arctan(ni) * 180 / np.pi, np.arctan(ni) * 180 / np.pi < 3 * 180 * np.arctan(np.sqrt(ni2)) / np.pi)
    P = P[angle_index]
    ni = ni[angle_index]

    nnk = ni.shape[0]
    ni = ni.reshape(nnk, 1)

    # local incidence angle
    theta_l = np.abs(theta_eq - np.arctan(ni).reshape(nnk, 1))

    # geometric scattering coefficients [Plant 1997] equation 5,6
    eps_sin = np.sqrt(const.epsilon_sw-np.sin(theta_l)**2)

    if polarization == 'VV':
        G = np.cos(theta_l) ** 2 * (const.epsilon_sw - 1) * (
                    const.epsilon_sw * (1 + np.sin(theta_l) ** 2) - np.sin(theta_l) ** 2) / (
                        const.epsilon_sw * np.cos(theta_l) + eps_sin) ** 2
        G = np.abs(G) ** 2
    else:
        G = np.cos(theta_l) ** 2 * (const.epsilon_sw - 1) / (np.cos(theta_l) + eps_sin) ** 2
        G = np.abs(G) ** 2

    Br = np.zeros([nazi, nphi])

    for num in np.arange(nazi):

        kbr = 2*kr*np.sin(theta_l)*np.cos(eq_azi[num])

    # 3-D Sk computed from kudryavtsev05
        if spec_name == 'kudryavtsev05':
            Skk = np.zeros([nnk, nphi, nazi])
        # spec_Skk = specf(np.sort(kbr[0, :]).reshape(nphi, 1), u_10, fetch, azimuth) / np.sort(kbr[0, :]).reshape(nphi, 1) ** 4
            for nn in np.arange(nnk):
                spec_Skk = specf(kbr[nn, :].reshape(nphi, 1), u_10, fetch, eq_azi) / kbr[nn, :].reshape(nphi, 1) ** 4
                Skk[nn, :, :] = spec_Skk
            inc = np.where(eq_azi >= 0)[0]
            incc = np.linspace(1, inc[0], inc[0])
            inc = np.hstack((inc, incc))
            Skk_pi = Skk[:, :, inc.astype(int)]
            Skb = Skk[:, :, num]  # equation 45
            Skb_pi = Skk_pi[:, :, num]
        else:
            Sk = specf(kbr, u_10, fetch)
            spreadf = spread.models[spec_name]
            Skb = Sk * spreadf(kbr, eq_azi[num], u_10, fetch) / kbr  # equation 45
            Skb_pi = Sk * spreadf(kbr, eq_azi[num] + np.pi, u_10, fetch) / kbr  # equation 45
        Skb_r = (Skb+Skb_pi) / 2 # Kudryavtsev 2003a equation 2

    # pure Bragg scattering NRCS
        br0 = 16 * np.pi * kr ** 4 * G * Skb_r

    # Bragg scattering composite model
        BR = br0 * P.reshape(nnk, 1)

    # integral over kbr >= kd
        intebr = []

        for i in np.arange(nphi):
            a = np.tan(theta_eq[i]-const.d / (2 * np.cos(eq_azi[num])))
            b = np.tan(theta_eq[i]+const.d / (2 * np.cos(eq_azi[num])))
            inte = BR[:, i].reshape(nnk, 1)
            vv = np.trapz(inte[ni <= a], ni[ni <= a]) + np.trapz(inte[ni >= b], ni[ni >= b])
            intebr.append(vv)
        intebr = np.asarray(intebr)
        Br[num, :] = intebr
    return Br

def Br_bi(k, kr, theta_i, theta_s, theta_eq, eq_azi, u_10, fetch, spec_name, polarization):
    """
    :param k:
    :param kr:
    :param theta_i:
    :param eq_azi:
    :param u_10:
    :param fetch:
    :param spec_name:
    :param polarization:
    :return:
    """
    # polarization of incident plane
    if polarization == 'VV':
        poli = 90
    else:
        poli = 0
    bist_ang_az = 2 * eq_azi
    # polarization for the mono-static equivalent
    (rot_ang_1, rot_ang_2, rot_ang_tot, Ps1, Ps2, Ps_tot) = elfouhaily(poli, eq_azi, theta_i, eq_azi, theta_i)
    Ps_tot_eq_norm = np.linalg.norm(Ps_tot, axis=-1)
    (rot_ang_1, rot_ang_2, rot_ang_tot, Ps1, Ps2, Ps_tot) = elfouhaily(poli, 0, theta_i, bist_ang_az, theta_s)
    Ps_tot_bi_norm = np.linalg.norm(Ps_tot, axis=-1)
    #  transfer function
    M = Ps_tot_bi_norm ** 2 / Ps_tot_eq_norm ** 2

    Br = eq_br(k, kr, theta_eq, eq_azi, u_10, fetch, spec_name, polarization)
    return M * Br