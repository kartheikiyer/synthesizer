import sys
import h5py
import numpy as np

from astropy.cosmology import FlatLambdaCDM

from .particle.galaxy import Galaxy


def _load_CAMELS(
    lens,
    imasses,
    ages,
    metals,
    s_oxygen,
    s_hydrogen,
    coods,
    masses,
    g_coods,
    g_masses,
    g_metallicities,
    g_hsml,
    star_forming,
    dtm=0.3
):
    """
    Load CAMELS galaxies into a galaxy object

    Arbitrary back end for different CAMELS simulation suites

    Args:
        lens (array):
            subhalo particle length array
        imasses (array):
            initial masses particle array
        ages (array):
            particle ages array
        metals (array):
            particle summed metallicities array
        s_oxygen (array):
            particle oxygen abundance array
        s_hydrogen (array):
            particle hydrogen abundance array
        coods (array):
            particle coordinates array, comoving
        masses (array):
            current mass particle array
        g_coods (array):
            gas particle coordinates array, comoving
        g_masses (array):
            gas particle masses array
        g_metallicities (array):
            gas particle overall metallicities array
        g_hsml (array):
            gas particle smoothing lengths array, comoving
        star_forming (array):
            boolean array flagging star forming gas particles
        dtm (float):
            dust-to-metals ratio to apply to all particles

    Returns:
        galaxies (object):
            `ParticleGalaxy` object containing specified
            stars and gas objects
    """

    begin, end = get_len(lens[:, 4])
    galaxies = [None] * len(begin)
    for i, (b, e) in enumerate(zip(begin, end)):
        galaxies[i] = Galaxy()

        galaxies[i].load_stars(
            imasses[b:e],
            ages[b:e],
            metals[b:e],
            s_oxygen=s_oxygen[b:e],
            s_hydrogen=s_hydrogen[b:e],
            coordinates=coods[b:e, :],
            current_masses=masses[b:e],
        )

    begin, end = get_len(lens[:, 0])
    for i, (b, e) in enumerate(zip(begin, end)):
        galaxies[i].load_gas(
            coordinates=g_coods[b:e],
            masses=g_masses[b:e],
            metals=g_metallicities[b:e],
            star_forming=star_forming[b:e],
            smoothing_lengths=g_hsml[b:e],
            dust_to_metal_ratio=dtm,
        )

    return galaxies


def load_CAMELS_IllustrisTNG(
    _dir=".",
    snap_name="snap_033.hdf5",
    fof_name="fof_subhalo_tab_033.hdf5",
    fof_dir=None,
    verbose=False,
    dtm=0.3,
):
    """
    Load CAMELS-IllustrisTNG galaxies

    Args:
        dir (string):
            data location
        snap_name (string):
            snapshot filename
        fof_name (string):
            subfind / FOF filename
        fof_dir (string):
            optional argument specifying lcoation of fof file
            if different to snapshot
        verbose (bool):
            verbosity flag
        dtm (float):
            dust-to-metals ratio to apply to all gas particles

    Returns:
        galaxies (object):
            `ParticleGalaxy` object containing star and gas particle
    """

    with h5py.File(f"{_dir}/{snap_name}", "r") as hf:
        form_time = hf["PartType4/GFM_StellarFormationTime"][:]
        coods = hf["PartType4/Coordinates"][:]
        masses = hf["PartType4/Masses"][:]
        imasses = hf["PartType4/GFM_InitialMass"][:]
        _metals = hf["PartType4/GFM_Metals"][:]
        metallicity = hf["PartType4/GFM_Metallicity"][:]

        g_sfr = hf["PartType0/StarFormationRate"][:]
        g_masses = hf["PartType0/Masses"][:]
        g_metals = hf["PartType0/GFM_Metallicity"][:]
        g_coods = hf["PartType0/Coordinates"][:]
        g_hsml = hf["PartType0/SubfindHsml"][:]

        scale_factor = hf["Header"].attrs["Time"]
        Om0 = hf["Header"].attrs["Omega0"]
        h = hf["Header"].attrs["HubbleParam"]

    if fof_dir:
        _dir = fof_dir  # replace if symlinks for fof files are broken
    with h5py.File(f"{_dir}/{fof_name}", "r") as hf:
        lens = hf["Subhalo/SubhaloLenType"][:]

    """
    remove wind particles
    """
    mask = form_time <= 0.0  # mask for wind particles

    if verbose:
        print("Wind particles:", np.sum(mask))

    # change len indexes
    for m in np.where(mask)[0]:
        # create array of end indexes
        cum_lens = np.append(0, np.cumsum(lens[:, 4]))

        # which halo does this wind particle belong to?
        which_halo = np.where(m < cum_lens)[0]

        # check we're not at the end of the array
        if len(which_halo) > 0:
            # reduce the length of *this* halo
            lens[which_halo[0] - 1, 4] -= 1

    # filter particle arrays
    imasses = imasses[~mask]
    form_time = form_time[~mask]
    coods = coods[~mask]
    metallicity = metallicity[~mask]
    masses = masses[~mask]
    _metals = _metals[~mask]

    masses = (masses * 1e10) / h
    g_masses = (g_masses * 1e10) / h
    imasses = (imasses * 1e10) / h

    star_forming = g_sfr > 0.0

    s_oxygen = _metals[:, 4]
    s_hydrogen = 1.0 - np.sum(_metals[:, 1:], axis=1)

    # convert formation times to ages
    cosmo = FlatLambdaCDM(H0=h * 100, Om0=Om0)
    universe_age = cosmo.age(1.0 / scale_factor - 1)
    _ages = cosmo.age(1.0 / form_time - 1)
    ages = (universe_age - _ages).value * 1e9  # yr

    return _load_CAMELS(
        lens=lens,
        imasses=imasses,
        ages=ages,
        metals=metallicity,
        s_oxygen=s_oxygen,
        s_hydrogen=s_hydrogen,
        coods=coods,
        masses=masses,
        g_coods=g_coods,
        g_masses=g_masses,
        g_metallicities=g_metals,
        g_hsml=g_hsml,
        star_forming=star_forming,
        dtm=dtm,
    )


def load_CAMELS_Astrid(
    _dir=".",
    snap_name="snap_090.hdf5",
    fof_name="fof_subhalo_tab_090.hdf5",
    fof_dir=None,
    dtm=0.3
):
    """
    Load CAMELS-Astrid galaxies

    Args:
        dir (string):
            data location
        snap_name (string):
            snapshot filename
        fof_name (string):
            subfind / FOF filename
        fof_dir (string):
            optional argument specifying lcoation of fof file
            if different to snapshot
        dtm (float):
            dust to metals ratio for all gas particles

    Returns:
        galaxies (object):
            `ParticleGalaxy` object containing star and gas particle
    """

    with h5py.File(f"{_dir}/{snap_name}", "r") as hf:
        form_time = hf["PartType4/GFM_StellarFormationTime"][:]
        coods = hf["PartType4/Coordinates"][:]
        masses = hf["PartType4/Masses"][:]
        imasses = np.ones(len(masses)) * 0.00155  # TODO: update with correct scaling
        _metals = hf["PartType4/GFM_Metals"][:]
        metallicity = hf["PartType4/GFM_Metallicity"][:]

        g_sfr = hf["PartType0/StarFormationRate"][:]
        g_masses = hf["PartType0/Masses"][:]
        g_metals = hf["PartType0/GFM_Metallicity"][:]
        g_coods = hf["PartType0/Coordinates"][:]
        g_hsml = hf["PartType0/SmoothingLength"][:]

        scale_factor = hf["Header"].attrs["Time"][0]
        Om0 = hf["Header"].attrs["Omega0"][0]
        h = hf["Header"].attrs["HubbleParam"][0]

    masses = (masses * 1e10) / h
    g_masses = (g_masses * 1e10) / h
    imasses = (imasses * 1e10) / h

    star_forming = g_sfr > 0.0

    s_oxygen = _metals[:, 4]
    s_hydrogen = 1 - np.sum(_metals[:, 1:], axis=1)

    # convert formation times to ages
    cosmo = FlatLambdaCDM(H0=h * 100, Om0=Om0)
    universe_age = cosmo.age(1.0 / scale_factor - 1)
    _ages = cosmo.age(1.0 / form_time - 1)
    ages = (universe_age - _ages).value * 1e9  # yr

    if fof_dir:
        _dir = fof_dir  # replace if symlinks for fof files are broken
    with h5py.File(f"{_dir}/{fof_name}", "r") as hf:
        lens = hf["Subhalo/SubhaloLenType"][:]

    return _load_CAMELS(
        lens=lens,
        imasses=imasses,
        ages=ages,
        metals=metallicity,
        s_oxygen=s_oxygen,
        s_hydrogen=s_hydrogen,
        coods=coods,
        masses=masses,
        g_coods=g_coods,
        g_masses=g_masses,
        g_metallicities=g_metals,
        g_hsml=g_hsml,
        star_forming=star_forming,
        dtm=dtm
    )


def load_CAMELS_SIMBA(
    _dir=".",
    snap_name="snap_033.hdf5",
    fof_name="fof_subhalo_tab_033.hdf5",
    fof_dir=None,
    dtm=0.3
):
    """
    Load CAMELS-SIMBA galaxies

    Args:
        dir (string):
            data location
        snap_name (string):
            snapshot filename
        fof_name (string):
            subfind / FOF filename
        fof_dir (string):
            optional argument specifying lcoation of fof file
            if different to snapshot
        dtm (float):
            dust to metals ratio for all gas particles

    Returns:
        galaxies (object):
            `ParticleGalaxy` object containing star and gas particle
    """

    with h5py.File(f"{_dir}/{snap_name}", "r") as hf:
        form_time = hf["PartType4/StellarFormationTime"][:]
        coods = hf["PartType4/Coordinates"][:]
        masses = hf["PartType4/Masses"][:]
        imasses = np.ones(len(masses)) * 0.00155  # * hf['Header'].attrs['MassTable'][1]
        _metals = hf["PartType4/Metallicity"][:]

        g_sfr = hf["PartType0/StarFormationRate"][:]
        g_masses = hf["PartType0/Masses"][:]
        g_metals = hf["PartType0/Metallicity"][:][:, 0]
        g_coods = hf["PartType0/Coordinates"][:]
        g_hsml = hf["PartType0/SmoothingLength"][:]

        scale_factor = hf["Header"].attrs["Time"]
        Om0 = hf["Header"].attrs["Omega0"]
        h = hf["Header"].attrs["HubbleParam"]

    masses = (masses * 1e10) / h
    g_masses = (g_masses * 1e10) / h
    imasses = (imasses * 1e10) / h

    star_forming = g_sfr > 0.0

    s_oxygen = _metals[:, 4]
    s_hydrogen = 1 - np.sum(_metals[:, 1:], axis=1)
    metallicity = _metals[:, 0]

    # convert formation times to ages
    cosmo = FlatLambdaCDM(H0=h * 100, Om0=Om0)
    universe_age = cosmo.age(1.0 / scale_factor - 1)
    _ages = cosmo.age(1.0 / form_time - 1)
    ages = (universe_age - _ages).value * 1e9  # yr

    if fof_dir:
        _dir = fof_dir  # replace if symlinks for fof files are broken
    with h5py.File(f"{_dir}/{fof_name}", "r") as hf:
        lens = hf["Subhalo/SubhaloLenType"][:]

    return _load_CAMELS(
        lens=lens,
        imasses=imasses,
        ages=ages,
        metals=metallicity,
        s_oxygen=s_oxygen,
        s_hydrogen=s_hydrogen,
        coods=coods,
        masses=masses,
        g_coods=g_coods,
        g_masses=g_masses,
        g_metallicities=g_metals,
        g_hsml=g_hsml,
        star_forming=star_forming,
        dtm=dtm,
    )

def load_FLARES(f, region, tag):
    """
    Load FLARES galaxies from a FLARES master file

    Args:
        f (string):
            master file location
        region (string):
            FLARES region to load
        tag (string):
            snapshot tag to load

    Returns:
        galaxies (object):
            `ParticleGalaxy` object containing stars
    """

    with h5py.File(f, "r") as hf:
        lens = hf[f"{region}/{tag}/Galaxy/S_Length"][:]
        ages = hf[f"{region}/{tag}/Particle/S_Age"][:]  # Gyr
        coods = hf[f"{region}/{tag}/Particle/S_Coordinates"][:].T
        mass = hf[f"{region}/{tag}/Particle/S_Mass"][:]  # 1e10 Msol
        imass = hf[f"{region}/{tag}/Particle/S_MassInitial"][:]  # 1e10 Msol
        # metals = hf[f'{region}/{tag}/Particle/S_Z'][:]
        metals = hf[f"{region}/{tag}/Particle/S_Z_smooth"][:]
        s_oxygen = hf[f"{region}/{tag}/Particle/S_Abundance_Oxygen"][:]
        s_hydrogen = hf[f"{region}/{tag}/Particle/S_Abundance_Hydrogen"][:]
        # ids = hf[f'{region}/{tag}/Particle/S_ID'][:]
        # index = hf[f'{region}/{tag}/Particle/S_Index'][:]
        # hf[f'{pre}/S_Vel']

    ages = ages * 1e9  # yr
    mass = mass * 1e10  # Msol
    imass = imass * 1e10  # Msol

    begin, end = get_len(lens)

    galaxies = [None] * len(begin)
    for i, (b, e) in enumerate(zip(begin, end)):
        galaxies[i] = Galaxy()
        galaxies[i].load_stars(
            mass[b:e],
            ages[b:e],
            metals[b:e],
            s_oxygen=s_oxygen[b:e],
            s_hydrogen=s_hydrogen[b:e],
            coordinates=coods[b:e, :],
        )

    return galaxies


def get_len(Length):
    """
    Find the beginning and ending indices from a length array

    Args:
        Length (array):
            array of number of particles

    Returns:
        begin (array):
            beginning indices
        end (array):
            ending indices
    """

    begin = np.zeros(len(Length), dtype=np.int64)
    end = np.zeros(len(Length), dtype=np.int64)
    begin[1:] = np.cumsum(Length)[:-1]
    end = np.cumsum(Length)
    return begin, end


def main():
    # e.g.
    # '/cosma7/data/dp004/dc-love2/codes/flares/data/FLARES_30_sp_info.hdf5'
    _f = sys.argv[1]
    tag = sys.argv[2]  # '/010_z005p000/'
    load_FLARES(_f, tag)
    return None


if __name__ == "__main__":
    main()
