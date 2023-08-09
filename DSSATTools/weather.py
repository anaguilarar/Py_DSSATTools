# TODO: There are different ET methods, so this should be included here, I mean,
#  the minimum data requirement must deppend on the ET method

'''
This module hosts the `Weather` class. It also contains the
`list_station_parameters` and `list_weather_variables` which return a list of the
parameters that define the weather station where the data was collected, and the
weather variables that can be included in the dataset. A `Weather` instance is
initialized by passing five mandatory parameters: a pandas dataframe including
the weather data, a dict mapping each dataframe column to one of the DSSAT
weather varaibles, latitude, longitude, and elevation.

The next example illustrates how to define a Weather instance from syntetic data:

    >>> DATES = pd.date_range('2000-01-01', '2010-12-31'); N=len(DATES)
    >>> df = pd.DataFrame(
            {
            'tn': np.random.gamma(10, 1, N),
            'rad': np.random.gamma(10, 1.5, N),
            'prec': np.round(np.random.gamma(.4, 10, N), 1),
            'rh': 100 * np.random.beta(1.5, 1.15, N),
            },
            index=DATES,
        )
    >>> df['TMAX'] = df.tn + np.random.gamma(5., .5, N)
    >>> weather = Weather(
            df, 
            {"tn": "TMIN", "rad": "SRAD", "prec": "RAIN", 
            "rh": "RHUM", "TMAX": "TMAX"},
            4.54, -75.1, 1800
        )

The parameters of the weather station are defined as attributes of the `Weather`
class. Those parameters can be listed by calling the `list_station_parameters`.
In the next example the reference height for windspeed measurements is defined
for the weather instance created in the previous example:

    >>> weather.WNDHT = 2

'''
import os
import pandas as pd
from pandas import DataFrame
from pandas import NA, isna
from DSSATTools.base.formater import weather_data, weather_data_header, weather_station

PARS_DESC = {
    # Station parameters
    'INSI': 'Institute and site code',
    'LAT': 'Latitude, degrees (decimals)',
    'LONG': 'Longitude, degrees (decimals)',
    'ELEV': 'Elevation, m',
    'TAV': 'Temperature average for whole year [long-term], C',
    'AMP': 'Temperature amplitude (range), monthly averages [long-term], C',
    'REFHT': 'Reference height for weather measurements, m',
    'WNDHT': 'Reference height for windspeed measurements, m',
    # Data parameters
    'DATE': 'Date, year + days from Jan. 1',
    'SRAD': 'Daily solar radiation, MJ m-2 day-1',
    'TMAX': 'Daily temperature maximum, C',
    'TMIN': 'Daily temperature minimum, C',
    'RAIN': 'Daily rainfall (incl. snow), mm day-1',
    'DEWP': 'Daily dewpoint temperature average, C',
    'WIND': 'Daily wind speed (km d-1)',
    'PAR': 'Daily photosynthetic radiation, moles m-2 day-1',
    'EVAP': 'Daily pan evaporation (mm d-1)',
    'RHUM': 'Relative humidity average, %'
}
PARS_STATION = ['INSI', 'LAT', 'LONG', 'ELEV', 'TAV', 'AMP', 'REFHT', 'WNDHT']
PARS_DATA = [i for i in PARS_DESC.keys() if i not in PARS_STATION]
MANDATORY_DATA = ['TMIN', 'TMAX', 'RAIN', 'SRAD']

def list_station_parameters():
    '''
    Print a list of the weather station parameters
    '''
    for key, value in PARS_DESC.items():
        if key in PARS_STATION:
            print(key + ': ' + value)

def list_weather_variables():
    '''
    Print a list of the weather data parameters
    '''
    for key, value in PARS_DESC.items():
        if key in PARS_DATA:
            print(key + ': ' + value)


class Weather():
    def __init__(self, df:DataFrame, pars:dict, lat:float, lon:float, elev:float):
        '''
        Initialize a Weather instance. This instance contains the weather data,
        as well as the parameters that define the weather station that the data
        represents,nsuch as the latitude, longitude and elevation.

        Arguments
        ----------
        df: DataFrame
            pandas DataFrame with the weather data. The index of the dataframe
            must be datetime. A simple quality control check is performed for
            data. 
        pars: dict
            A dictionary mapping the data columns to the Weather variables
            required by DSSAT. Use `weather.list_weather_variables` function to
            have a detailed description of the DSSAT weather variables.
        lat, lon, elev: float
            Latitude, longitude and elevation of the weather station
        '''
        self.description = "Weather station"
        self.INSI = 'WSTA'
        self.LAT = lat
        self.LON = lon
        self.ELEV = elev 
        self.TAV = 17 
        self.AMP = 10 
        self.REFHT = 2
        self.WNDHT = 10
        data = df.copy()

        for key, value in pars.items():
            assert value in PARS_DATA, \
                f'{value} is not a valid variable name'
            if (value in PARS_DATA) and (key not in PARS_DATA):
                data[value] = data[key]
                data.drop(columns=[key], inplace=True)

        assert all(map(lambda x: x in data.columns, MANDATORY_DATA)), \
            f'Data must contain at least {", ".join(MANDATORY_DATA)} variables'

        # A really quick QC check
        TEMP_QC = all(data.TMIN <= data.TMAX)
        assert TEMP_QC, 'TMAX < TMIN at some point in the series'
        if 'RHUM' in data.columns:
            RHUM_QC = all((data.RHUM >= 0) & (data.RHUM <= 100))
            assert RHUM_QC, '0 <= RHUM <= 100 must be accomplished'
        RAIN_QC = all(data.RAIN >= 0)
        assert RAIN_QC, '0 <= RAIN must be accomplished'
        if 'SRAD' in data.columns:
            SRAD_QC = all(data.SRAD >= 0)
            assert SRAD_QC, '0 <= SRAD must be accomplished'

        # Check date column
        DATE_COL = False
        for col in data.columns:
            if pd.api.types.is_datetime64_any_dtype(data[col]):
                DATE_COL = col
        if pd.api.types.is_datetime64_any_dtype(data.index):
            DATE_COL = True
        assert DATE_COL, 'At least one of the data columns must be a date'

        if isinstance(DATE_COL, str):
            data.set_index(DATE_COL, inplace=True)
        
        self.INSI = self.INSI[:4].upper()

        assert isinstance(data, DataFrame), \
            'wthdata must be a DataFrame instance'
        self.data = data

    def write(self, folder:str='', **kwargs):
        '''
        Writes the weather files in the provided folder. The name is defined by the dates and the Institute code (INSI).

        Arguments
        ----------
        folder: str
            Path to the folder the files will be saved.
            
        '''
        if not os.path.exists(folder):
            os.mkdir(folder)
        man = kwargs.get('management', False)
        if man:
            from datetime import datetime
            sim_start = datetime(man.sim_start.year, man.sim_start.month, man.sim_start.day)
            self.data = self.data.loc[self.data.index >= sim_start]
        for year in self.data.index.year.unique():
            df = self.data.loc[self.data.index.year == year]
            # month = df.index[0].strftime('%m')
            month = '01'
            filename = f'{self.INSI}{str(year)[2:]}{month}.WTH'
            outstr = f'*WEATHER DATA : {self.description}\n\n'
            outstr += '@ INSI      LAT     LONG  ELEV   TAV   AMP REFHT WNDHT\n'
            outstr += weather_station([
                self.INSI, self.LAT, self.LON, self.ELEV,
                self.TAV, self.AMP, self.REFHT, self.WNDHT
            ])
            outstr += weather_data_header(self.data.columns)
            
            for day, fields in df.iterrows():
                day = day.strftime('%y%j')
                outstr += weather_data([day]+list(fields))
            
            with open(os.path.join(folder, filename), 'w') as f:
                f.write(outstr)

    def __repr__(self):
        repr_str = f"Weather data at {self.LON:.3f}°, {self.LAT:.3f}°\n"
        repr_str += f"  Date start: {self.data.index.min().strftime('%Y-%m-%d')}\n"
        repr_str += f"  Date end: {self.data.index.max().strftime('%Y-%m-%d')}\n"
        repr_str += "Average values:\n" + self.data.mean().__repr__()
        return repr_str
        
