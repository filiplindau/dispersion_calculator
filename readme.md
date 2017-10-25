## Calculation of linear dispersion through transparent materials


### Synopsis
Calculation of linear dispersion of short laser pulses through transparent materials.
The materials are specified with their Sellmeier coefficients and stored in a dictionary.
At creation an internal set of materials is generated (air, fused silica (fs), bbo, sapphire, MgF2) and a materials directory (./materials)
    is scanned for XML files for additional materials.
    The XML files contain a sellmeier element and a list of tags A, B, and C with the coefficients.

A GUI is included that uses pyqtgraph for plotting.

The propagation is done in the frequency domain through spectral filtering. FFT is used to
transform between time and frequency domains.

### Code Example
Create a 50 fs gaussian pulse centered at 800 nm. Propagate it through 10 mm of BK7
glass. Plot the resulting pulse, now 70 fs long.
```
dc = DispersionCalculator(50e-15, 800e-9, 20e-12)
dc.propagate_material("bk7", 10e-3)
t = dc.get_t()
I_t = dc.get_temporal_intensity(True)
mpl.plot(t, I_t)
```

To get pulse characteristics:
```
dc.get_pulse_duration('temporal')
7.000437527345388e-14
dc.get_spectral_phase_expansion(orders=4, prefix=1e12)
array([ -1.87785647e-11,   1.76835023e-07,  -3.87455963e-04,
        -1.35853758e-01,  -1.10705156e+01])
```
Meaning -3.87e-4 ps^2 second order phase, 1.77e-7 ps^3 third order phase,
and -0.14 ps delay.

### GUI
The GUI has a list of materials to propagate in a table. Materials can be added using the combobox
and the add button. The table can be editing be typing with a cell selected. Both material type and
thickness can be changed. A material can be deleted from the propagation by pressing delete with a
cell selected.

The pulse can be specified either as an initial pulse duration or an initial spectral width.

### Installation
The gui depends on `PyQt4` and `pyqtgraph`. The dispersion calculation depends on
`scipy.interpolate` and `numpy`