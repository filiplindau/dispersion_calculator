"""
Created on 29 Mar 2017

@author: Filip Lindau
"""

import numpy as np
from scipy.interpolate import interp1d
from xml.etree import cElementTree as ElementTree
import os
import logging
import warnings
root = logging.getLogger()
root.setLevel(logging.DEBUG)
# warnings.filterwarnings('ignore')


class DispersionCalculator(object):
    def __init__(self, t_fwhm=50e-15, l_0=800e-9, t_span=2e-12):
        self.materials_path = "./materials"
        self.c = 299792458.0
        self.l_mat = np.linspace(200e-9, 2000e-9, 1000)
        self.phase_thr = 0.01
        self.t_span = t_span
        self.l_0 = l_0
        self.w_0 = 2 * np.pi * self.c / self.l_0
        self.N = 8192
        self.dt = self.t_span / self.N
        self.t = np.linspace(-self.t_span / 2, self.t_span / 2, self.N)
        self.w = np.fft.fftshift((2*np.pi*np.fft.fftfreq(self.N, d=self.dt)))

        self.E_t = np.array([])
        self.E_w = np.array([])
        self.E_t_out = np.array([])
        self.E_w_out = np.array([])

        self.generate_pulse(t_fwhm, l_0, t_span)

        self.materials = {}
        self.generate_materials_dict()

    def generate_pulse(self, fwhm, l_0, t_span=2e-12, n=None, duration_domain='temporal'):
        self.l_0 = l_0
        self.w_0 = 2 * np.pi * self.c / self.l_0
        self.t_span = t_span
        if n is None:
            n = np.int(self.N)
        self.N = n
        self.dt = self.t_span / n
        self.t = np.linspace(-self.t_span / 2, self.t_span / 2, np.int(n))
        self.w = np.fft.fftshift((2 * np.pi * np.fft.fftfreq(np.int(n), d=self.dt)))
        ph = 0.0
        if duration_domain == 'temporal':
            tau = fwhm / np.sqrt(2 * np.log(2))
        else:
            tau = 0.441 * l_0**2 / (fwhm * self.c)
        # self.E_t = np.exp(-self.t ** 2 / tau ** 2 + ph) * np.exp(1j * self.w_0 * self.t)
        self.E_t = np.exp(-self.t ** 2 / tau ** 2 + ph)
        self.E_w = np.fft.fftshift(np.fft.fft(self.E_t))
        self.E_t_out = self.E_t.copy()
        self.E_w_out = self.E_w.copy()

    def generate_materials_dict(self):
        w_mat = 2 * np.pi * self.c / self.l_mat
        l2_mat = (self.l_mat * 1e6) ** 2

        # n_bk7 = np.sqrt(1 + 1.03961212 * l2_mat / (l2_mat - 0.00600069867) +
        #                 0.231792344 * l2_mat / (l2_mat - 0.0200179144) +
        #                 1.01046945 * l2_mat / (l2_mat - 103.560653))
        #
        # bk7_ip = interp1d(w_mat, n_bk7, bounds_error=False, fill_value=np.nan)
        # self.materials['bk7'] = bk7_ip

        n_air = 1 + 0.05792105 * l2_mat / (238.0185 * l2_mat - 1) + 0.00167917 * l2_mat / (57.362 * l2_mat - 1)
        air_ip = interp1d(w_mat, n_air, bounds_error=False, fill_value=np.nan, kind="quadratic")
        self.materials['air'] = air_ip

        n_fs = np.sqrt(1 + 0.6961663 * l2_mat / (l2_mat - 0.0684043 ** 2) +
                       0.4079426 * l2_mat / (l2_mat - 0.1162414 ** 2) +
                       0.8974794 * l2_mat / (l2_mat - 9.896161 ** 2))
        fs_ip = interp1d(w_mat, n_fs, bounds_error=False, fill_value=np.nan, kind="quadratic")
        self.materials['fs'] = fs_ip

        n_mgf2 = np.sqrt(1 + 0.48755108 * l2_mat / (l2_mat - 0.04338408 ** 2) +
                         0.39875031 * l2_mat / (l2_mat - 0.09461442 ** 2) +
                         2.3120353 * l2_mat / (l2_mat - 23.793604 ** 2))
        mgf2_ip = interp1d(w_mat, n_mgf2, bounds_error=False, fill_value=np.nan, kind="quadratic")
        self.materials['mgf2'] = mgf2_ip

        n_sapphire_o = np.sqrt(1 + 1.4313493 * l2_mat / (l2_mat - 0.0726631 ** 2) +
                               0.65054713 * l2_mat / (l2_mat - 0.1193242 ** 2) +
                               5.3414021 * l2_mat / (l2_mat - 18.028251 ** 2))
        sapphire_o_ip = interp1d(w_mat, n_sapphire_o, bounds_error=False, fill_value=np.nan, kind="quadratic")
        self.materials['sapphire_o'] = sapphire_o_ip

        n_sapphire_e = np.sqrt(1 + 1.5039759 * l2_mat / (l2_mat - 0.0740288 ** 2) +
                               0.55069141 * l2_mat / (l2_mat - 0.1216529 ** 2) +
                               6.5927379 * l2_mat / (l2_mat - 20.072248 ** 2))
        sapphire_e_ip = interp1d(w_mat, n_sapphire_e, bounds_error=False, fill_value=np.nan, kind="quadratic")
        self.materials['sapphire_e'] = sapphire_e_ip

        n_bbo_o = np.sqrt(2.7405 + 0.0184 / (l2_mat - 0.0179) - 0.0155 * l2_mat)
        bbo_o_ip = interp1d(w_mat, n_bbo_o, bounds_error=False, fill_value=np.nan, kind="quadratic")
        self.materials['bbo_o'] = bbo_o_ip

        n_bbo_e = np.sqrt(2.3730 + 0.0128 / (l2_mat - 0.0156) - 0.0044 * l2_mat)
        bbo_e_ip = interp1d(w_mat, n_bbo_e, bounds_error=False, fill_value=np.nan, kind="quadratic")
        self.materials['bbo_e'] = bbo_e_ip

        materials_files = os.listdir(self.materials_path)
        root.info("Found {0:d}".format(materials_files.__len__()))
        for mat_file in materials_files:
            root.info(mat_file)
            self.read_material(''.join((self.materials_path, '/', mat_file)))

    def add_material(self, name, b_coeff, c_coeff):
        l_mat = np.linspace(200e-9, 2000e-9, 5000)
        w_mat = 2 * np.pi * self.c / l_mat
        l2_mat = (l_mat * 1e6) ** 2
        n_tmp = 0.0
        for ind, b in enumerate(b_coeff):
            n_tmp += b*l2_mat / (l2_mat - c_coeff[ind])
        n = np.sqrt(1 + n_tmp)
        n_ip = interp1d(w_mat, n, bounds_error=False, fill_value=np.nan, kind="quadratic")
        self.materials[name] = n_ip

    def read_material(self, filename):
        l_mat = np.linspace(200e-9, 2000e-9, 5000)
        w_mat = 2 * np.pi * self.c / l_mat
        l2_mat = (l_mat * 1e6) ** 2
        n_tmp = 0.0

        e = ElementTree.parse(filename)
        mat = e.getroot()
        name = mat.get('name')
        sm = mat.findall('sellmeier')
        for s in sm:
            at = s.find('A')
            if at is not None:
                a = np.double(at.text)
            else:
                a = 0.0
            bt = s.find('B')
            if bt is not None:
                b = np.double(bt.text)
            else:
                b = 0.0
            ct = s.find('C')
            if ct is not None:
                c = np.double(ct.text)
            else:
                c = 0.0
            n_tmp += a + b*l2_mat / (l2_mat - c)
        n = np.sqrt(1 + n_tmp)
        n_ip = interp1d(w_mat, n, bounds_error=False, fill_value=np.nan)
        self.materials[name] = n_ip

    def propagate_material(self, name, thickness):
        # k_w = self.w * self.materials[name](self.w) / self.c
        try:
            k_w = (self.w + self.w_0) * self.materials[name](self.w + self.w_0) / self.c
        except KeyError:
            return
        H_w = np.exp(-1j * k_w * thickness)
        H_w[np.isnan(H_w)] = 0
        self.E_w_out = H_w * self.E_w_out.copy()
        self.E_t_out = np.fft.ifft(np.fft.fftshift(self.E_w_out))

    def reset_propagation(self):
        self.E_w_out = self.E_w.copy()
        self.E_t_out = self.E_t.copy()

    def get_temporal_intensity(self, norm=True):
        if self.E_t_out.size != 0:
            # Center peak in time
            ind = np.argmax(abs(self.E_t_out))
            shift = (self.E_t_out.shape[0] / 2 - ind).astype(np.int)
            I_t = np.abs(np.roll(self.E_t_out, shift))**2
            if norm is True:
                I_t /= I_t.max()
        else:
            I_t = None
        return I_t

    def get_temporal_phase(self, linear_comp=False):
        eps = self.phase_thr

        if self.E_t_out.size != 0:
            # Center peak in time
            ind = np.argmax(abs(self.E_t_out))
            shift = self.E_t_out.shape[0] / 2 - ind
            E_t = np.roll(self.E_t_out, shift)

            # Unravelling 2*pi phase jumps
            ph0_ind = np.int(E_t.shape[0] / 2)  # Center index
            ph = np.angle(E_t)
            ph_diff = np.diff(ph)
            # We need to sample often enough that the difference in phase is less than 5 rad
            # A larger jump is taken as a 2*pi phase jump
            ph_ind = np.where(np.abs(ph_diff) > 5.0)
            # Loop through the 2*pi phase jumps
            for ind in ph_ind[0]:
                if ph_diff[ind] < 0:
                    ph[ind + 1:] += 2 * np.pi
                else:
                    ph[ind + 1:] -= 2 * np.pi

            # Find relevant portion of the pulse (intensity above a threshold value)
            ph0 = ph[ph0_ind]
            E_t_mag = np.abs(E_t)
            low_ind = np.where(E_t_mag < eps)
            ph[low_ind] = np.nan

            # Here we could go through contiguous regions and make the phase connect at the edges...

            # Linear compensation is we have a frequency shift (remove 1st order phase)
            if linear_comp is True:
                idx = np.isfinite(ph)
                x = np.arange(E_t.shape[0])
                ph_poly = np.polyfit(x[idx], ph[idx], 1)
                ph_out = ph - np.polyval(ph_poly, x)
            else:
                ph_out = ph - ph0
        else:
            ph_out = None
        return ph_out

    def get_spectral_intensity(self, norm=True):
        if self.E_w_out.size != 0:
            # Center peak in time
            ind = np.argmax(abs(self.E_w_out))
            shift = (self.E_w_out.shape[0] / 2 - ind).astype(np.int)
            I_w = np.abs(np.roll(self.E_w_out, shift))**2
            if norm is True:
                I_w /= I_w.max()
        else:
            I_w = None
        return I_w

    def get_spectral_phase(self, linear_comp=True):
        """
        Retrieve the spectral phase of the propagated E-field. The phase is zero at the peak field and NaN
        where the field magnitude is lower than the threshold phase_thr (class variable). Use get_w for the
        corresponding angular frequency vector.

        :param linear_comp: If true, the linear part of the phase (i.e. time shift) if removed
        :return: Spectral phase vector.
        """
        eps = self.phase_thr    # Threshold for intensity where we have signal

        # Check if there is a reconstructed field:
        if self.E_t_out is not None:

            # Center peak in time
            ind = np.argmax(abs(self.E_t_out))
            shift = - ind
            E_t = np.roll(self.E_t_out, shift)
            Ew = np.fft.fftshift(np.fft.fft(E_t))

            # ind = np.argmax(abs(self.E_w_out))
            # shift = (self.E_w_out.shape[0] / 2 - ind).astype(np.int)
            # Ew = np.roll(self.E_w_out, shift)

            # Ew = self.E_w_out
            # Normalize
            Ew /= abs(Ew).max()

            # Unravelling 2*pi phase jumps
            ph0_ind = np.argmax(abs(Ew))
            ph = np.angle(Ew)
            ph_diff = np.diff(ph)
            # We need to sample often enough that the difference in phase is less than 5 rad
            # A larger jump is taken as a 2*pi phase jump
            ph_ind = np.where(np.abs(ph_diff) > 5.0)
            # Loop through the 2*pi phase jumps
            for ind in ph_ind[0]:
                if ph_diff[ind] < 0:
                    ph[ind + 1:] += 2 * np.pi
                else:
                    ph[ind + 1:] -= 2 * np.pi

            # Find relevant portion of the pulse (intensity above a threshold value)
            Ew_mag = np.abs(Ew)
            low_ind = np.where(Ew_mag < eps)
            ph[low_ind] = np.nan

            # Here we could go through contiguous regions and make the phase connect at the edges...

            # Linear compensation is we have a frequency shift (remove 1st order phase)
            if linear_comp is True:
                idx = np.isfinite(ph)
                x = np.arange(Ew.shape[0])
                ph_poly = np.polyfit(x[idx], ph[idx], 1)
                ph_out = ph - np.polyval(ph_poly, x)
            else:
                ph_out = ph
            ph_out -= ph_out[ph0_ind]
        else:
            ph_out = None
        return ph_out

    def get_spectral_phase_expansion(self, orders=4, prefix=1e12):
        """
        Calculate a polynomial fit to the retrieved phase curve as function of angular frequency (spectral phase)
        :param orders: Number of orders to include in the fit
        :param prefix: Factor that the angular frequency is scaled with before the fit (1e12 => Trad)
        :return: Polynomial coefficients, highest order first
        """
        if self.E_t_out is not None:
            # w = self.w
            # w = self.w + self.w_0
            w = self.get_w()
            ph = self.get_spectral_phase()
            ph_ind = np.isfinite(ph)
            ph_good = ph[ph_ind]
            w_good = w[ph_ind] / prefix
            ph_poly = np.polyfit(w_good, ph_good, orders)
        else:
            ph_poly = None
        return ph_poly

    def get_pulse_duration(self, domain='temporal'):
        """
        Calculate pulse parameters such as intensity FWHM.
        :param domain: 'temporal' for time domain parameters,
                     'spectral' for frequency domain parameters
        :return:
        trace_fwhm: full width at half maximum of the intensity trace (E-field squared)
        delta_ph: phase difference (max-min) of the phase trace
        """
        if domain == 'temporal':
            I = self.get_temporal_intensity(True)
            x = self.get_t()
        else:
            I = self.get_spectral_intensity(True)
            x = self.get_w()

        # Calculate FWHM
        x_ind = np.where(np.diff(np.sign(I - 0.5)))[0]
        if x_ind.shape[0] > 1:
            trace_fwhm = x[x_ind[-1]] - x[x_ind[0]]
        else:
            trace_fwhm = np.nan
        return trace_fwhm

    def get_t(self):
        return self.t

    def get_w(self):
        # w = np.fft.fftshift(self.w + self.w_0)
        w = self.w + self.w_0
        return w


if __name__ == "__main__":
    dc = DispersionCalculator(50e-15, 800e-9, 2e-12)
    dc.propagate_material("bk7", 10e-3)
