import pytest
import numpy
from nbodykit.lab import UniformCatalog, LogNormalCatalog
from nbodykit.cosmology import LinearPower
from nbodykit.transform import CartesianToSky

class BenchmarkingSample(object):
    """
    An object to generate catalog source objects for benchmarking for
    various sample configuration.

    Specific samples can be selected via the command-line using the ``-m``
    marker selector.

    Specific attributes, e.g., ``N``, ``BoxSize``, can be set explicitly
    in benchmarking functions, and the data generated by :func:`data`
    will reflect the changes.

    Examples
    --------
    To run the boss samples, use:

    >>> python run-tests.py benchmarks --no-build --bench -m boss
    """
    samples   = ['test', 'boss_like', 'desi_like']
    test      = {'BoxSize' : 100.,  'Nmesh':64,   'N':1e3}
    boss_like = {'BoxSize' : 2500., 'Nmesh':1024, 'N':1e6}
    desi_like = {'BoxSize' : 5000., 'Nmesh':1024, 'N':1e7}

    def __init__(self, name):
        assert name in self.samples, 'valid names are: %s' % str(self.samples)
        self.name = name

    @property
    def Nmesh(self):
        return getattr(self, '_Nmesh', getattr(self, self.name)['Nmesh'])

    @Nmesh.setter
    def Nmesh(self, val):
        self._Nmesh = val

    @property
    def BoxSize(self):
        boxsize = getattr(self, '_BoxSize', getattr(self, self.name)['BoxSize'])
        return numpy.ones(3) * boxsize

    @BoxSize.setter
    def BoxSize(self, val):
        self._BoxSize = val

    @property
    def N(self):
        return getattr(self, '_N', getattr(self, self.name)['N'])

    @N.setter
    def N(self, val):
        self._N = val

    @property
    def cosmo(self):
        from nbodykit.cosmology import Planck15
        return Planck15

    @property
    def redshift(self):
        return 0.

    def data(self, seed=None):
        """
        Return a LogNormalCatalog using the specific configuration of this
        sample. The catalog also includes (RA, DEC, Z) coordinates in
        addition to Position.
        """
        redshift = 0.
        nbar = self.N/self.BoxSize.prod()

        # lognormal catalog
        Plin = LinearPower(self.cosmo, redshift=self.redshift, transfer='EisensteinHu')
        cat = LogNormalCatalog(Plin=Plin, nbar=nbar, BoxSize=self.BoxSize, Nmesh=512, seed=seed)

        # add sky coordinates too
        cat['RA'], cat['DEC'], cat['Z'] = CartesianToSky(cat['Position'], self.cosmo, observer=0.5*self.BoxSize)

        # and n(z)
        cat['NZ'] = nbar

        return cat

    def randoms(self, alpha, seed=None):
        """
        Return a UniformCatalog using the specific configuration of this
        sample, accounting for the additional up-sampling factor ``alpha``.

        The overall ``N`` used here is ``alpha * self.N``.
        """
        nbar = alpha * self.N/self.BoxSize.prod()
        cat = UniformCatalog(nbar=nbar, BoxSize=self.BoxSize, seed=seed)

        # add sky coordinates too
        cat['RA'], cat['DEC'], cat['Z'] = CartesianToSky(cat['Position'], self.cosmo, observer=0.5*self.BoxSize)

        # and n(z)
        cat['NZ'] = nbar/alpha

        return cat

@pytest.fixture(params=BenchmarkingSample.samples, scope='session')
def sample(request):
    """
    Define the BenchmarkingSample as a session-wide pytest fixture.
    """
    return BenchmarkingSample(request.param)

def pytest_collection_modifyitems(items):
    """
    Automatically apply a ``pytest.mark`` decorator for each sample
    in the benchmarking samples.
    """
    for item in items:
        for name in BenchmarkingSample.samples:
            postfix = item.name.split(item.originalname)[-1] # this looks like [boss_like-10000]
            if name in postfix:
                item.add_marker(getattr(pytest.mark, name))
