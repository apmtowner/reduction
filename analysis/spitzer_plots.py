import requests
import re
import numpy as np
from astropy import table
import io
import time
from astropy import units as u
import radio_beam
import regions
from astropy.io import fits
from astropy.visualization import simple_norm
from astropy import stats, convolution, wcs, coordinates
from spectral_cube import SpectralCube
import pylab as pl
import spectral_cube

from spectralindex import prefixes

import warnings
warnings.filterwarnings('ignore', category=spectral_cube.utils.StokesWarning)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=pl.matplotlib.cbook.MatplotlibDeprecationWarning)
np.seterr('ignore')




glimpses=g_subsets=['glimpsei_0_6','glimpseii_0_6','glimpse3d_0_6','glimpse360_0_6','glimpse_cygx_0_6','glimpse_deepglimpse_0_6','glimpse_smog_0_6','glimpse_velacar_0_6']



def get_spitzer_data(crd, size):
    for spitzertbl in glimpses:
        url = f"https://irsa.ipac.caltech.edu/IBE?table=spitzer.{spitzertbl}&POS={crd.ra.deg},{crd.dec.deg}&ct=csv&mcen&where=fname+like+'%.fits'"
        response = requests.get(url)
        response.raise_for_status()
        tbl = table.Table.read(io.BytesIO(response.content), format='ascii.csv')

        files = {}

        if len(tbl) >= 4:

            fnames = tbl['fname']
            for fname in fnames:
                irsa_url = f"https://irsa.ipac.caltech.edu/ibe/data/spitzer/{spitzertbl}/{fname}?center={crd.ra.deg},{crd.dec.deg}&size={size.to(u.arcmin).value}arcmin"

                key = re.search("I[1-4]", fname).group()

                fh = fits.open(irsa_url)
                files[key] = fh

            return files

def show_fov_on_spitzer(finaliter_prefix_b3, finaliter_prefix_b6, fieldid, spitzerpath='spitzer_datapath', contour_level={'B3':[0.01], 'B6':[0.01]}):
    image_b3 = SpectralCube.read(f'{finaliter_prefix_b3}.image.tt0.fits', use_dask=False, format='fits')
    image_b6 = SpectralCube.read(f'{finaliter_prefix_b6}.image.tt0.fits', use_dask=False, format='fits')

    spitzfn = f'{spitzerpath}/{fieldid}_spitzer_images.fits'
    spitz = fits.open(spitzfn)[0]

    ww = wcs.WCS(spitz.header)

    fig = pl.figure(1, figsize=(10,10))
    fig.clf()
    ax = fig.add_subplot(projection=ww.celestial)

    ax.imshow(simple_norm(spitz.data, stretch='log', min_percent=5, max_percent=99.99)(spitz.data.T.swapaxes(0,1)))

    lims = ax.axis()

    ax.contour(image_b3.mask.include()[0], transform=ax.get_transform(image_b3.wcs.celestial), levels=[0.5], colors=['orange'])
    ax.contour(image_b6.mask.include()[0], transform=ax.get_transform(image_b6.wcs.celestial), levels=[0.5], colors=['cyan'])
    ax.contour(image_b3[0].value,  transform=ax.get_transform(image_b3.wcs.celestial), levels=contour_level['B3'], colors=['wheat'], linewidths=[0.5])
    ax.contour(image_b6[0].value,  transform=ax.get_transform(image_b6.wcs.celestial), levels=contour_level['B6'], colors=['lightblue'], linewidths=[0.5])


    ax.axis(lims)
    ax.set_xlabel('Galactic Longitude')
    ax.set_ylabel('Galactic Latitude')

    #pl.figure(2).gca().imshow(image_b6.mask.include()[0])
    return fig


contour_levels = {
    'G328': {'B3': [0.001], 'B6':[0.003]},
    'G333': {'B3': [0.005], 'B6':[0.01]},
    'G12': {'B3': [0.005], 'B6':[0.01]},
    'W51IRS2': {'B3': [0.005], 'B6':[0.01]},
    'W51-E': {'B3': [0.005], 'B6':[0.01]},
    'W43MM2': {'B3': [0.005], 'B6':[0.01]},
    'W43MM3': {'B3': [0.005], 'B6':[0.01]},
    'G008': {'B3': [0.005], 'B6':[0.01]},
    'G327': {'B3': [0.005], 'B6':[0.01]},
    'G10': {'B3': [0.005], 'B6':[0.01]},
    'G337': {'B3': [0.005], 'B6':[0.01]},
    'G338': {'B3': [0.005], 'B6':[0.01]},
    'G351': {'B3': [0.005], 'B6':[0.01]},
    'G353': {'B3': [0.005], 'B6':[0.01]},
}


if __name__ == "__main__":
    import os
    try:
        os.chdir('/orange/adamginsburg/ALMA_IMF/2017.1.01355.L/RestructuredImagingResults')
    except FileNotFoundError:
        os.chdir('/home/adam/Dropbox_UFL/ALMA-IMF/December2020Release/')

    if not os.path.exists('spitzer_datapath'):
        os.mkdir('spitzer_datapath')
    if not os.path.exists('spitzer_datapath/fov_plots'):
        os.mkdir('spitzer_datapath/fov_plots')
    if not os.path.exists('spitzer_datapath/fov_contour_plots'):
        os.mkdir('spitzer_datapath/fov_contour_plots')

    for fieldid, pfxs in prefixes.items():

        print(fieldid)
        spitzer_cubename = f'spitzer_datapath/{fieldid}_spitzer_images.fits'
        if not os.path.exists(spitzer_cubename):
            cube = SpectralCube.read(pfxs['finaliter_prefix_b3']+".image.tt0.fits", format='fits', use_dask=False).minimal_subcube()

            size = np.abs(np.max(cube.shape[1:] * cube.wcs.pixel_scale_matrix.diagonal()[:2])*u.deg)*1.5

            center = coordinates.SkyCoord(*cube[0].world[int(cube.shape[1]/2), int(cube.shape[2]/2)][::-1],
                                          frame=wcs.utils.wcs_to_celestial_frame(cube.wcs))

            spitzer_data = get_spitzer_data(center, size)


            spitzer_cube = np.array([spitzer_data['I4'][0].data, spitzer_data['I2'][0].data, spitzer_data['I1'][0].data, ])
            fits.PrimaryHDU(data=spitzer_cube, header=spitzer_data['I1'][0].header).writeto(spitzer_cubename, overwrite=True)

        fig = show_fov_on_spitzer(**pfxs, fieldid=fieldid, spitzerpath='spitzer_datapath', contour_level={'B3':[100], 'B6': [100]})
        fig.savefig(f'spitzer_datapath/fov_plots/{fieldid}_field_of_view_plot.png', bbox_inches='tight')
        fig = show_fov_on_spitzer(**pfxs, fieldid=fieldid, spitzerpath='spitzer_datapath', contour_level=contour_levels[fieldid])
        fig.savefig(f'spitzer_datapath/fov_contour_plots/{fieldid}_field_of_view_contour_plot.png', bbox_inches='tight', dpi=300)

