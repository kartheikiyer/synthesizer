import numpy as np

from scipy.stats import linregress
from scipy import integrate

import unyt
from unyt import c, h, nJy, erg, s, Hz, pc, angstrom, eV, unyt_array

from .units import Quantity
from .igm import Inoue14
from . import exceptions



class Sed:

    """
    A class representing a spectral energy distribution (SED).

    Attributes
    ----------
    lam : ndarray
        the wavelength grid in Angstroms
    nu : ndarray
        frequency in Hz
    lnu: ndarray
        the spectral luminosity density


    Methods
    -------
    return_beta:
        Calculate beta using two wavelength points
    return_beta_spec:
        Calculate beta using linear regression to the spectra over a
        wavelength range
    """

    # for details see units.py
    lam = Quantity()  # Angstrom
    nu = Quantity()  # Hz
    lnu = Quantity()  # erg/s/Hz
    fnu = Quantity()  # nJy

    def __init__(self, lam, lnu=None, description=False):
        """Initialise an empty spectral energy distribution object"""

        self.description = description

        self.lam = lam  # \AA

        if lnu is None:
            self.lnu = np.zeros(self.lam.shape)  # luminosity erg/s/Hz
        else:
            self.lnu = lnu

        self.nu = (c / (self.lam)).to("Hz").value  # Hz

        self.redshift = 0
        self.obslam = None
        self.nuz = None
        self.fnu = None
        self.broadband_luminosities = None
        self.broadband_fluxes = None

    def __add__(self, second_sed):
        if not np.array_equal(self._lam, second_sed._lam):
            exceptions.InconsistentAddition("Wavelength grids must be identical")

        else:
            if self._lnu.ndim != second_sed._lnu.ndim:
                exceptions.InconsistentAddition("SEDs must have same dimensions")

            elif self._lnu.ndim == 1:
                # if single Seds simply add together and return.
                return Sed(self._lam, lnu=self._lnu + second_sed._lnu)

            elif self._lnu.ndim == 2:
                # if array of Seds concatenate them. This is only relevant for particles.
                return Sed(self._lam, np.concatenate((self._lnu, second_sed._lnu)))

            else:
                exceptions.InconsistentAddition("Sed.lnu must have ndim 1 or 2")

    def __str__(self):
        """
        Overloads the __str__ operator. A summary can be achieved by
        print(sed) where sed is an instance of sed.
        """

        # Set up string for printing
        pstr = ""

        # Add the content of the summary to the string to be printed
        pstr += "-" * 10 + "\n"
        pstr += "SUMMARY OF SED \n"
        pstr += f"Number of wavelength points: {len(self._lam)} \n"
        # pstr += f"Bolometric luminosity: {self.get_bolometric_luminosity()}"
        pstr += "-" * 10

        return pstr

    @property
    def _spec_dims(self):
        return np.ndim(self.lnu)

    def get_bolometric_luminosity(self):
        """
        Calculate the bolometric luminosity of the SED.
        """

        return np.trapz(self.lnu[::-1], x=self.nu[::-1])


    def get_index(index_window, blue_window, red_window, loc):
        """
        Calculate the bounds of absorption, blue continuum, and red continuum windows.

        Args:
            index_window (list): List of index window bounds.
            blue_window (list): List of blue shifted window bounds.
            red_window (list): List of red shifted window bounds.
            loc (int): Location index to select the appropriate bounds.

        Returns:
            tuple: A tuple containing the following integer values:
                - absorption_start (int): Start of the absorption window.
                - absorption_end (int): End of the absorption window.
                - blue_start (int): Start of the blue continuum window.
                - blue_end (int): End of the blue continuum window.
                - red_start (int): Start of the red continuum window.
                - red_end (int): End of the red continuum window.
        """
        indices = np.array([index_window[loc], index_window[loc+1], blue_window[loc], blue_window[loc+1], red_window[loc], red_window[loc+1]])
        
        absorption_start, absorption_end, blue_start, blue_end, red_start, red_end = indices
        
        return absorption_start, absorption_end, blue_start, blue_end, red_start, red_end


    def return_beta(self, wv=[1500.0, 2500.0]):
        """Return the UV continuum slope (\beta) based on measurements
        at two wavelength."""

        if self._spec_dims == 2:
            f0 = np.array([np.interp(wv[0], self.lam, _lnu) for _lnu in self.lnu])
            f1 = np.array([np.interp(wv[1], self.lam, _lnu) for _lnu in self.lnu])

        else:
            f0 = np.interp(wv[0], self._lam, self._lnu)
            f1 = np.interp(wv[1], self._lam, self._lnu)

        return np.log10(f0 / f1) / np.log10(wv[0] / wv[1]) - 2.0

    def return_beta_spec(self, wv=[1250.0, 3000.0]):
        """
        Return the UV continuum slope (\beta) based on linear
        regression to the spectra over a wavelength range.
        """

        s = (self.lam > wv[0]) & (self.lam < wv[1])

        if self._spec_dims == 2:
            slope = np.array(
                [
                    linregress(np.log10(self.lam[s]), np.log10(_lnu[..., s]))[0]
                    for _lnu in self.lnu
                ]
            )
        else:
            dummy = linregress(np.log10(self.lam[s]), np.log10(self.lnu[..., s]))
            slope = dummy[0]

        return slope - 2.0

    def get_balmer_break(self):
        """Return the Balmer break strength"""

        T = (self.lam > 3400) & (self.lam < 3600)
        T = T.astype(float)
        b = integrate.trapezoid(self.lnu * T / self.nu, self.nu) / integrate.trapezoid(
            T / self.nu, self.nu
        )  # numerator

        T = (self.lam > 4150) & (self.lam < 4250)
        T = T.astype(float)
        r = integrate.trapezoid(self.lnu * T / self.nu, self.nu) / integrate.trapezoid(
            T / self.nu, self.nu
        )  # numerator

        return np.log10(r / b)

        """ measure the balmer break strength """

    def get_broadband_luminosities(self, filters):
        """
        Calculate broadband luminosities using a FilterCollection object

        arguments
        fc: a FilterCollection object
        """

        self.broadband_luminosities = {}

        for f in filters:
            # Apply the filter transmission curve and store the resulting
            # luminosity
            bb_lum = f.apply_filter(self._lnu, nu=self._nu) * erg / s / Hz
            self.broadband_luminosities[f.filter_code] = bb_lum

        return self.broadband_luminosities

    def get_fnu0(self):
        """
        Calculate a dummy observed frame spectral energy distribution.
        Useful when you want rest-frame quantities.

        Uses a standard distance of 10 pc
        """

        # Get the observed wavelength and frequency arrays
        self.obslam = self._lam
        self.nuz = self._nu

        # Compute the flux SED and apply unit conversions to get to nJy
        self.fnu = self._lnu / (4 * np.pi * (10 * pc).to("cm").value)
        self._fnu *= 1e23  # convert to Jy
        self._fnu *= 1e9  # convert to nJy

    def get_fnu(self, cosmo, z, igm=None):
        """
        Calculate the observed frame spectral energy distribution in nJy

        """

        # Define default igm if none has been given
        if igm is None:
            igm = Inoue14()

        # Store the redshift for later use
        self.redshift = z

        # Get the observed wavelength and frequency arrays
        self.obslam = self._lam * (1.0 + z)
        self.nuz = self._nu / (1.0 + z)

        # Compute the luminosity distance
        luminosity_distance = cosmo.luminosity_distance(z).to("cm").value

        # Finally, compute the flux SED and apply unit conversions to get
        # to nJy
        self.fnu = self._lnu * (1.0 + z) / (4 * np.pi * luminosity_distance**2)
        self._fnu *= 1e23  # convert to Jy
        self._fnu *= 1e9  # convert to nJy

        # If we are applying an IGM model apply it
        if igm:
            self._fnu *= igm.T(z, self.obslam)

    def get_broadband_fluxes(self, fc, verbose=True):  # broad band flux/nJy
        """
        Calculate broadband luminosities using a FilterCollection object

        arguments
        fc: a FilterCollection object
        """

        if (self.obslam is None) | (self.fnu is None):
            return ValueError(
                (
                    "Fluxes not calculated, run `get_fnu` or "
                    "`get_fnu0` for observer frame or rest-frame "
                    "fluxes, respectively"
                )
            )

        self.broadband_fluxes = {}

        # loop over filters in filter collection
        for f in fc:
            # Check whether the filter transmission curve wavelength grid
            # and the spectral grid are the same array
            if not np.array_equal(f.lam, self.lam):
                if verbose:
                    print(
                        (
                            "WARNING: filter wavelength grid is not "
                            "the same as the SED wavelength grid."
                        )
                    )

            # Calculate and store the broadband flux in this filter
            bb_flux = f.apply_filter(self._fnu, nu=self.nuz) * nJy
            self.broadband_fluxes[f.filter_code] = bb_flux

        return self.broadband_fluxes

    def colour(self, f1, f2, verbose=False):
        """
        Calculate broadband colours using the broad_band fluxes
        """

        if not bool(self.broadband_fluxes):
            raise ValueError(
                (
                    "Broadband fluxes not yet calculated, "
                    "run `get_broadband_fluxes` with a "
                    "FilterCollection"
                )
            )

        return 2.5 * np.log10(self.broadband_fluxes[f2] / self.broadband_fluxes[f1])

    def calculate_ew(self, index):
        """
        Calculate the equivalent width of an absorption feature.

        Parameters:
            index (list): List of wavelength indices, containing:
                - absorption_start (int): Start index of the absorption feature.
                - absorption_end (int): End index of the absorption feature.
                - blue_start (int): Start index of the blue continuum.
                - blue_end (int): End index of the blue continuum.
                - red_start (int): Start index of the red continuum.
                - red_end (int): End index of the red continuum.

        Returns:
            float: Equivalent width in angstroms (Å).

        Notes:
            - This method calculates the equivalent width (EW) of an absorption feature in a spectrum.
            - The flux units are converted from nJy to Lnu.
            - The method defines the wavelength ranges of the absorption feature and two sets of continuum.
            - The average continuum level is computed based on the specified wavelength ranges.
            - The EW is calculated by integrating the flux difference between the absorption feature and continuum.

        Example:
            To calculate the EW, provide a list of wavelength indices:
            >>> index = [1370, 1400, 1360, 1380, 1436, 1447]
            >>> ew_value = your_instance.calculate_ew(index)
            >>> print(ew_value)
            42.15 Å
        """
        
        flux = self._lnu * (self._lam**2)

        absorption_start = index[0]
        absorption_end = index[1]

        blue_start = index[2]
        blue_end = index[3]

        red_start = index[4]
        red_end = index[5]

        continuum_indices = np.where(
            (self._lam >= absorption_start) & (self._lam <= absorption_end)
        )[0]

        blue_indices = np.where((self._lam >= blue_start) & (self._lam <= blue_end))[0]
        red_indices = np.where((self._lam >= red_start) & (self._lam <= red_end))[0]

        blue_mean = np.mean(flux[blue_indices])
        red_mean = np.mean(flux[red_indices])

        avg_blue = 0.5 * (blue_start + blue_end)
        avg_red = 0.5 * (red_start + red_end)

        line = np.polyfit([avg_blue, avg_red], [blue_mean, red_mean], 1)

        continuum = (line[0] * self._lam) + line[1]

        ew = np.trapz(
            (continuum[continuum_indices] - flux[continuum_indices])
            / continuum[continuum_indices],
            self._lam[continuum_indices],
        )

        return ew

    # def return_log10Q(self):
    #     """
    #     measure the ionising photon luminosity
    #     :return:
    #     """
    #
    #     llam = self.lnu * c.value / (self.lam**2*1E-10)  # erg s^-1 \AA^-1
    #     # s^-1 \AA^-1
    #     nlam = (llam*self.lam*1E-10) / (h.to('erg/Hz').value * c.value)
    #     s = ((self.lam >= 0) & (self.lam < 912)).nonzero()[0]
    #     Q = simps(nlam[s], self.lam[s])
    #
    #     return np.log10(Q)


# def calculate_Q_deprecated(lam, lnu):
#     """ calculate the ionising photon luminosity
#
#     arguments:
#     lam -- wavelength / \\AA
#     lnu -- spectral luminosity density/erg/s/Hz
#     """
#
#     # --- check lam is increasing and if not reverse
#     if lam[1] < lam[0]:
#         lam = lam[::-1]
#
#     lam_m = lam * 1E-10  # m
#     lnu *= 1E-7  # convert to W s^-1 Hz^-1
#     llam = lnu * c.value / (lam * lam_m)  # convert to l_lam (W s^-1 \AA^-1)
#     nlam = (llam * lam_m) / (h.value * c.value)  # s^-1 \AA^-1
#
#     def f(l): return np.interp(l, lam, nlam)
#     Q = integrate.quad(f, 0, 912.0)[0]
#
#     return Q


def calculate_Q(lam, lnu, ionisation_energy=13.6 * eV, limit=100):
    """
    An improved function to calculate the ionising production rate.

    Parameters
    ----------
    lam : float array
        wavelength grid
    lnu: float array
        luminosity grid (erg/s/Hz)
    ionisation_energy: unyt_array
        ionisation energy
    limit: float or int, optional
        An upper bound on the number of subintervals
        used in the integration adaptive algorithm.


    Returns
    ----------
    float
        ionising photon luminosity (s^-1)

    """

    if not isinstance(lam, unyt_array):
        lam = lam * angstrom

    if not isinstance(lnu, unyt_array):
        lnu = lnu * erg / s / Hz

    # convert lnu to llam
    llam = lnu * c / lam**2

    # convert llam to lum [THIS SEEMS REDUNDANT]
    lum = llam * lam

    # caculate ionisation wavelength
    ionisation_wavelength = h * c / ionisation_energy

    x = lam.to("Angstrom").value
    y = lum.to("erg/s").value / (h.to("erg/Hz").value * c.to("Angstrom/s").value)

    def f(x_):
        return np.interp(x_, x, y)

    return integrate.quad(
        f, 0, ionisation_wavelength.to("Angstrom").value, limit=limit
    )[0]


def rebin(l, f, n):  # rebin SED [currently destroys original]
    n_len = int(np.floor(len(l) / n))
    _l = l[: n_len * n]
    _f = f[: n_len * n]
    nl = np.mean(_l.reshape(n_len, n), axis=1)
    nf = np.sum(_f.reshape(n_len, n), axis=1) / n

    return nl, nf
