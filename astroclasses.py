""" Contains structural classes ie binary, star, planet etc which mimic the xml structure with objects
"""
import numpy as np

import quantities as pq

import equations as eq
import astroquantities as aq
import assumptions as assum
import flags


class baseObject(object):

    def __init__(self, params=None):

        self.children = []
        self.parent = None # TODO should be read only (use add method)
        self.classType = 'BaseObject'
        self.flags = flags.Flag()

        self.params = {}
        if params is not None:
            self._updateParams(params)  # TODO value validator?

    def _addChild(self, child):

        self.children.append(child)

    def _updateParams(self, params):
        """ This method updates parameters allowing for any validation / unit additions in the near future
        """

        self.params.update(params)

    @property
    def name(self):
        try:
            return self.params['name']
        except KeyError:
            try:
                return self.parent.name
            except AttributeError:
                return 'Un-named ' + self.classType
        except AttributeError:
            return 'Un-named ' + self.classType

    def __repr__(self):
        return '{}({!r})'.format(self.classType, self.name)

    def getParam(self, paramKey):
        """ Fetches a parameter from the params dictionary. If it's not there it will return NaN. This allows the use
        of list comprehensions over the entire planet set without KeyErrors.

        NaN was used as unlike False and None, NaN < 1 and NaN > 1 are both False
        """

        try:
            return self.params[paramKey]
        except KeyError:
            return np.NaN


class System(baseObject):

    def __init__(self, *args, **kwargs):
        baseObject.__init__(self, *args, **kwargs)
        self.classType = 'System'

    @property
    def ra(self):
        return self.getParam('rightascension')

    @property
    def dec(self):
        return self.getParam('declination')

    @property
    def d(self):
        return self.getParam('distance')

    @property
    def stars(self):
        return self.children


class StarAndPlanetCommon(baseObject):

    def __init__(self, *args, **kwargs):
        baseObject.__init__(self, *args, **kwargs)
        self.classType = 'StarAndPlanetCommon'

    @property
    def age(self):
        return self.getParam('age')

    @property  # allows stars and planets to access system values by propagating up
    def ra(self):
        return self.parent.ra

    @property
    def dec(self):
        return self.parent.dec

    @property
    def d(self):
        return self.parent.d

    @property
    def R(self):
        return self.getParam('radius')

    @property
    def T(self):
        """ Looks for the planet temperature in the catalogue, if absent it calculates it using meanPlanetTemp()

        :return: planet temperature
        """
        paramTemp = self.getParam('temperature')

        if not paramTemp is np.nan:
            return paramTemp
        else:
            self.flags.addFlag('Calculated Temperature')
            return self.calcTemperature()

    @property
    def M(self):
        return self.getParam('mass')

    def calcTemperature(self):
        raise NotImplementedError('Only implemented for Stars and Planet child classes')

    @property
    def system(self):
        return self.parent

    def calcSurfaceGravity(self):

        return eq.surfaceGravity(self.M, self.R)

    def calcLogg(self):

        return eq.logg(self.M, self.R)

    def calcDensity(self):

        if self.M is np.nan or self.R is np.nan:
            return np.nan
        else:
            return eq.density(self.M, self.R)


class Binary(StarAndPlanetCommon):

    def __init__(self, *args, **kwargs):
        StarAndPlanetCommon.__init__(self, *args, **kwargs)
        self.classType = 'Binary'

    @property
    def stars(self):
        return self.children


class Star(StarAndPlanetCommon):

    def __init__(self, *args, **kwargs):
        StarAndPlanetCommon.__init__(self, *args, **kwargs)
        self.classType = 'Star'

    def calcLuminosity(self):

        return eq.starLuminosity(self.R, self.T)

    def calcTemperature(self):
        """ uses equations.starTemperature to estimate temperature based on main sequence relationship
        """
        return eq.starTemperature(self.M)

    @property
    def Z(self):
        return self.getParam('metallicity')

    @property
    def Z(self):
        return self.getParam('metallicity')

    @property
    def magB(self):
        return self.getParam('magB')

    @property
    def magH(self):
        return self.getParam('magH')

    @property
    def magI(self):
        return self.getParam('magI')

    @property
    def magJ(self):
        return self.getParam('magJ')

    @property
    def magK(self):
        return self.getParam('magK')

    @property
    def magV(self):
        return self.getParam('magV')

    @property
    def spectralType(self):
        return self.getParam('spectraltype')

    @property
    def planets(self):
        return self.children


class Planet(StarAndPlanetCommon):

    def __init__(self, *args, **kwargs):
        StarAndPlanetCommon.__init__(self, *args, **kwargs)
        self.classType = 'Planet'

    def isTransiting(self):
        """ Checks the discovery method to see if the planet transits
        """

        if self.params['discoverymethod'] == 'transit':
            return True  # is this all or will it miss RV detected planets that transit?
        else:
            return False

    def calcTransitDuration(self):
        """ Estimation of the primary transit time assuming a circular orbit (see :py:func:`equations.transitDuration`)
        """
        try:
            return eq.transitDuration(self.P, self.parent.R, self.R, self.a, self.i)
        except ValueError:
            return np.nan

    def calcScaleHeight(self):
        raise NotImplementedError
        # return eq.scaleHeight(self.T, , self.g)  # TODO mu based on assumptions

    def calcTransitDepth(self):
        return eq.transitDepth(self.star.R, self.R)

    def type(self):
        return assum.planetType(self.T, self.M, self.R)

    def massType(self):
        return assum.planetMassType(self.M)

    def radiusType(self):
        return assum.planetRadiusType(self.R)

    def tempType(self):
        return assum.planetTempType(self.T)

    def mu(self):  # TODO make getter look in params first calc if not
        if self.M is not np.nan:
            return assum.planetMu(self.massType())
        elif self.R is not np.nan:
            return assum.planetMu(self.radiusType())
        else:
            return np.nan

    def albedo(self):
        if self.getParam('temperature') is not np.nan:
            planetClass = self.tempType()
        elif self.M is not np.nan:
            planetClass = self.massType()
        elif self.R is not np.nan:
            planetClass = self.radiusType()

        return assum.planetAlbedo(planetClass)

    def calcTemperature(self):
        """ Calculates the temperature using which uses equations.meanPlanetTemp, albedo assumption and potentially
        equations.starTemperature.

        issues
        - you cant get the albedo assumption without temp but you need it to calculate the temp.
        """
        try:
            return eq.meanPlanetTemp(self.albedo(), self.star.T, self.star.R, self.a)
        except ValueError:  # ie missing value (.a) returning nan
            return np.nan

    def estimateMass(self):

        density = assum.planetDensity(self.radiusType())

        return eq.estimateMass(self.R, density)

    def calcSMA(self):
        """ Calculates the semi-major axis based on star mass and period
        """

        return eq.calcSemiMajorAxis(self.P, self.star.M)

    @property
    def discoveryMethod(self):
        return self.getParam('discoverymethod')

    @property
    def discoveryYear(self):
        return self.getParam('discoveryyear')

    @property
    def e(self):
        return self.getParam('eccentricity')

    @property
    def lastUpdate(self):
        return self.getParam('lastupdate')

    @property
    def i(self):
        return self.getParam('inclination')

    @property
    def P(self):
        return self.getParam('period')

    @property
    def a(self):

        sma = self.getParam('semimajoraxis')
        if sma is np.nan:
            sma = self.calcSMA()
            self.flags.addFlag('Calculated SMA')

        return sma

    @property
    def transittime(self):
        return self.getParam('transittime')

    @property
    def star(self):
        return self.parent


class Parameters(object):  # TODO would this subclassing dict be more preferable?
    """ A class to hold parameter dictionaries, the input can be validated, units added and handling of multi valued
    fields. In future this may be better as a child of dict.
    """

    def __init__(self):

        self.params = {
            'altnames': [],
            'list': [],
        }

        self._defaultUnits = {
            'age': aq.Gyear,
            'distance': pq.pc, # TODO more specific unit handling here or in classes?
            'magB': 1,
            'magH': 1,
            'magI': 1,
            'magJ': 1,
            'magK': 1,
            'magV': 1,
            'temperature': pq.K,
        }

        self.rejectTags = ('system', 'binary', 'star', 'planet', 'moon')  # These are handled in their own classes

    def addParam(self, key, value, attrib=None):
        """ Checks the key dosnt already exist, adds alternate names to a seperate list

        Future
            - format input and add units
            - logging
        """

        if key in self.rejectTags:
            return False  # TODO Replace with exception

        if key in self.params:

            if key == 'name':
                self.params['altnames'].append(value)
            elif key == 'list':
                self.params['list'].append(value)
            else:
                try:
                    name = self.params['name']
                except KeyError:
                    name = 'Unnamed'
                print 'rejected duplicate {}: {} in {}'.format(key, value, name)  # TODO: log rejected value
                return False  # TODO Replace with exception

        else:  # If the key dosnt already exist and isn't rejected

            # Some tags have no value but a upperlimit in the attributes
            if value is None and attrib is not None:
                try:
                    value = attrib['upperlimit']
                except KeyError:
                    try:
                        value = attrib['lowerlimit']
                    except KeyError:
                        return False

            if key in self._defaultUnits:
                try:
                    value = float(value) * self._defaultUnits[key]
                except:
                    print 'caught an error with {} - {}'.format(key, value)
            self.params[key] = value


class BinaryParameters(Parameters):

    def __init__(self):

        Parameters.__init__(self)

        self._defaultUnits.update({
         # TODO add binary parameters
        })


class StarParameters(Parameters):

    def __init__(self):

        Parameters.__init__(self)

        self._defaultUnits.update({
            'mass': aq.M_s,
            'metallicity': 1,
            'radius': aq.R_s,
        })


class PlanetParameters(Parameters):

    def __init__(self):

        Parameters.__init__(self)

        self._defaultUnits.update({
            'discoveryyear': 1,
            'mass': aq.M_j,
            'radius': aq.R_j,
            'inclination': pq.deg,
            'eccentricity': 1,
            'period': pq.day,
            'semimajoraxis': pq.au,
            'transittime': pq.d
        })

_ExamplePlanetCount = 1  # Used by example.py - put here to enable global