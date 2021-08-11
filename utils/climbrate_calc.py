import numpy as np, matplotlib.pyplot as plt
# assumed sample rate of 1 minute

maxclimb = 3000
desc_const = -2000
tr = 5

def cr_calc(alt_coord, climbrate, T: int, z0: float, zf: float, X: float, debug: bool = False):
    if debug:
        alt_coord = np.zeros((100 * T))
        climbrate = np.zeros((100 * T))

    # calc t0, tf, c in native units (minutes, ft/min)
    t0 = np.roots([-22.5, 2700, 16500 - X + z0])
    c = (maxclimb - (50) * t0)
    t0 = [t0[i] for i in range(len(t0)) if c[i] > 0][0]
    c = [x for x in c if x > 0][0]
    tf = (c / 500)

    # create sampled vars
    tru_tr, tru_t0, tru_tf, tru_c, tru_max = tr, t0, tf, c, maxclimb
    tr_smp, t0_smp, tf_smp, c_smp, maxclimb_smp = int(tr * T), int(t0 * T), int(tf * T), c / T, maxclimb / T

    # Compute Theoretical (no rounding), clipped (theoretical with sampling limitation), and clipped-approx (clipped + adjusted C-point)
    theor = 7500 + (tru_t0 * ((tru_c + 3000) / 2)) + tru_tf * (tru_c / 2) + z0
    clipped = 7500 + (t0_smp * ((c_smp + (3000 / T)) / 2)) + tf_smp * (c_smp / 2) + z0
    c_appx = np.linspace(c_smp - 10 / T, c_smp + 10 / T, 500)
    clipped_appx = 7500 + (t0_smp * ((c_appx + (3000 / T)) / 2)) + tf_smp * (c_appx / 2) + z0
    idx_closest = np.argmin(np.abs(clipped_appx - X))
    closest_appx = clipped_appx[idx_closest]
    closest_c = c_appx[idx_closest]

    # Interpret climbrates
    climbrate[:tr_smp] = np.linspace(0, maxclimb_smp, tr_smp)
    climbrate[tr_smp:tr_smp + t0_smp] = np.linspace(maxclimb_smp, closest_c, t0_smp)
    climbrate[tr_smp + t0_smp:tr_smp + t0_smp + tf_smp] = np.linspace(closest_c, 0, tf_smp)

    # Descent Phase is much Simpler
    td = 10; td_smp = td * T
    tru_t1 = (X - zf - 15000.) / abs(desc_const)
    t1_smp = int(tru_t1 * T)

    land_theor = X - 15000. - (tru_t1 * abs(desc_const))
    land_clipped = X - 15000. - (t1_smp * abs(desc_const) / T)
    climbrate[-(tr_smp + t1_smp + td_smp):-(t1_smp + td_smp)] = np.linspace(0, desc_const / T, tr_smp)
    climbrate[-(t1_smp + td_smp):-(td_smp)] = desc_const / T
    climbrate[-td_smp:] = np.linspace(desc_const / T, 0, td_smp)

    # Validations
    alt_coord = [z0 + np.sum(climbrate[:i]) for i in range(len(climbrate))]

    if not debug: return {'cr': climbrate, 'alt': alt_coord}
    else: return {'cr': climbrate, 'alt': alt_coord,
                  'X_calcs': {'theor': theor, 'rounded': clipped, 'appx': closest_appx},
                  'zf_calcs': {'theor': land_theor, 'rounded': land_clipped}
                  }


def main():
    Xs = np.arange(28000.,40000.,1000.)
    z0s  = [216, 80, 1026, 672, 125, 21, 433, 5431, 97, 20]
    zfs = z0s
    T = 60

    X_err, zf_err = [],[]
    for z0 in z0s:
        for zf in zfs:
            for X in Xs:
                dict_calc = cr_calc(alt_coord=None, climbrate=None, T=60,z0=z0,zf=zf,X=X,debug=True)
                if X == Xs[0] and zf == zfs[0] and z0 == z0s[0]:
                    print('\nASCENT\nTarget:{}\tAct:{}\nTheor:{}\tRounded:{}\tAppx:{}'.format(X, max(dict_calc['alt']),
                          dict_calc['X_calcs']['theor'],dict_calc['X_calcs']['rounded'],dict_calc['X_calcs']['appx']))
                    print('\n\nDESCENT\nTarget:{}\tAct:{}\tTheor:{}:\tClipped:{}'.format(zf, dict_calc['alt'][-1],
                        dict_calc['zf_calcs']['theor'],dict_calc['zf_calcs']['rounded']))
                    crfig, crax = plt.subplots(1,1)
                    crax.plot(T*dict_calc['cr'][::T])
                    crax.set_xlabel('Time (Minutes'); crax.set_ylabel('Climb Rate (ft/min)')
                    crfig.suptitle('Sample FP Climb Rate\nX:{}   z0:{}   zf:{}'.format(X,z0,zf))
                    crfig.savefig('Sample FP CR.png',dpi=300)
                    plt.close(crfig); crfig.clf(); crax.cla()

                    altfig, altax = plt.subplots(1,1)
                    altax.plot(dict_calc['alt'][::T])
                    altax.set_xlabel('Time (Minutes'); altax.set_ylabel('Altitude (fT)')
                    altfig.suptitle('Sample FP Altitude\nX:{}   z0:{}   zf:{}'.format(X, z0, zf))
                    altfig.savefig('Sample FP Altitude.png', dpi=300)
                    plt.close(altfig); altfig.clf(); altax.cla()

                X_err.append(max(dict_calc['alt'])-X)
                zf_err.append(dict_calc['alt'][-1]-zf)

    Xfig, Xax = plt.subplots(1,1)
    #Xax.hist(X_err, bins=int(len(X_err)/10))
    Xax.hist(X_err, bins=100)
    Xfig.suptitle('Cruising Altitude Err\n T = {} smp/min'.format(T))
    Xax.set_xlabel('err (ft)'); Xax.set_ylabel('Count')
    Xfig.savefig('Cruising Altitude Errors.png',dpi=300)

    zffig, zfax = plt.subplots(1,1)
    # zfax.hist(zf_err, bins=int(len(zf_err/10)))
    zfax.hist(zf_err, bins=100)
    zffig.suptitle('Landing Elevation Err\n T = {} smp/min'.format(T))
    zfax.set_xlabel('err (ft)'); zfax.set_ylabel('Count')
    zffig.savefig('Landing Elevation Errors.png', dpi=300)

if __name__ == '__main__': main()