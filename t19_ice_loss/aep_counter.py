"""

"""

import datetime
import numpy as np
import scipy.stats as ss
import configparser
import sys

class TimingError(Exception):
    def __init__(self, starttime, stoptime, index):
        self.index = index
        self.start = starttime
        self.stop = stoptime
        self.dateformat = "%Y-%m-%d %H:%M:%S"


class AEPcounter:
    """
    set of functions to calculate AEP losses from structured data
    """
    def __init__(self):
        """
        Initialize all relevant variables to some values. These need to be set
        based on the structure of the actual data

        wind_bins and direction_bins contain the CENTERS of bins

        """
        self.id = '' # data id used to id the data
        self.ts_index = 0  # column of TIMESTAMP in source data
        self.ws_index = 1  # column of WIND SPEED in source data
        self.wd_index = 2  # column of WIND DIRECTION index in source data
        self.temp_index = 3  # column of TEMPERATURE in source data
        self.pow_index = 4  # column of POWER in source data
        self.state_index = [5]  # column of TURBINE STATE INFORMATION
        self.normal_state = [0]  # normal/default value of state variable
        self.wind_bins = np.arange(0, 20, 1)  # wind speed binning
        self.direction_bins = np.arange(0, 360, 360)  # wind direction binning
        self.rated_power = 1.0  # rated power of the turbine (1.0 if power given as relative to rated power)
        self.icing_time = 3 # icing length in samples for now
        self.stop_time = 6 # time filter for stops in number of samples
        self.pc_low_limit = 10 # lower limit for power curve checks
        self.pc_high_limit = 90 # lower limit for power curve checks
        self.stop_level = 0.005 # level used to define stops
        self.state_filter_type = 1 # type 1 inclusive 2 exclusive
        self.power_level_filter_limit = 0.01 # limit for self.power_level_filter
        self.reference_temperature_limit = 3
        self.icing_temperature_limit = 3
        self.pc_binsize = 36 # bin size filter for power curve
        self.pc_dist_filter = True # filter out obviously wrong values from power curves.
        self.site_elevation = 0.0
        self.fault_dict = {} # used in case fault codes need to be replaced very non-elegant solution, but...
        self.result_dir = '.'
        self.starttimestamp = datetime.datetime.min
        self.stoptimestamp = datetime.datetime.max
        self.stopcodes = [] # status codes for icing related stops
        self.stop_filter_type = 0 # 0 for power level based 1 for status code based where stop if true 2 for stop if false
        self.status_stop_index = None
        self.heated_site = False
        self.ice_detection = False
        self.ice_alarm_index = 0
        self.ice_alarm_value = 0
        self.heating_status_index = 0
        self.heating_status_value = 0
        self.heating_status_type = 0
        self.heating_power_index = 0
        self.replace_faults = False
        self.fault_columns = []
        # TODO:
        # fix icing and stoptime to be actual minutes instead of sample count

    def get_fallback_value(self, section, config_var):
        """
        Helper function used when reading .ini files. Sets non-mandatory values to common fallback settings
        :param section, where config_var is defined
        :param config_var:
        :return: fallback value
        """
        # so far all config var names are unique, no need to split this by section yet, do it anyway
        if section == 'Source file':
            sf_fallbacks = {'delimiter': ',',
                            'quotechar': 'NONE',
                            'datetime format': '%Y-%m-%d %H:%M:%S',
                            'datetime extra char': '0',
                            'replace fault codes': 'False'}
            return sf_fallbacks[config_var]
        elif section == 'Output':
            o_fallbacks = {'result directory': '.',
                           'summary': 'True',
                           'plot': 'True',
                           'alarm time series': 'True',
                           'filtered raw data': 'True',
                           'icing events': 'False','power curve': 'True'}
            return o_fallbacks[config_var]
        elif section == 'Data Structure':
            # these are all mandatory, except this one, it needs a fallback to maintain compatibility with old inifiles
            # need to define this anyway
            ds_fallbacks = {"status code stop value": '0',
                            "status index": '-1'}
            return ds_fallbacks[config_var]
        elif section == 'Icing':
            # icing is not mandatory anyway
            i_fallbacks = {}
            return None
        elif section == 'Binning':
            b_fallbacks = {'minimum wind speed': '0',
                           'maximum wind speed': '20',
                           'wind speed bin size': '1',
                           'wind direction bin size': '360'}
            return b_fallbacks[config_var]
        elif section == 'Filtering':
            f_fallbacks = {'power drop limit': '10',
                           'overproduction limit': '90',
                           'power level filter': '0.01',
                           'temperature filter': '1',
                           'reference temperature': '3',
                           'icing time': '3',
                           'stop filter type': '0',
                           'stop limit multiplier': '0.005',
                           'stop time filter': '6',
                           'statefilter type': '1',
                           'min bin size': '36',
                           'distance filter': 'True',
                           'start time': 'None',
                           'stop time': 'None'}
            return f_fallbacks[config_var]
        else:
            print('section "{0}" does not exist in config file'.format(section))
            sys.exit(1)


    def set_data_options_from_file(self,filename):
        """
        read in configuration settings from a config file
        """
        config = configparser.ConfigParser()
        config.read(filename)
        try:
            self.ts_index = int(config.get('Data Structure','timestamp index'))
            self.ws_index = int(config.get('Data Structure','wind speed index'))
            self.wd_index  = int(config.get('Data Structure','wind direction index'))
            self.temp_index = int(config.get('Data Structure','temperature index'))
            self.pow_index = int(config.get('Data Structure','power index'))
            self.rated_power = float(config.get('Data Structure','rated power'))
            state_index_raw = config.get('Data Structure','state index')
            self.state_index = [int(column_index) for column_index in state_index_raw.split(',')]
            self.site_elevation = float(config.get('Data Structure','site elevation'))
            stop_codes_raw = config.get('Data Structure', 'status code stop value', fallback=self.get_fallback_value('Data Structure', 'status code stop value'))
            normal_state_raw = config.get('Data Structure','normal state')
            # normal state can be given as text or as a list of codes, all cases need to be sorted
            self.replace_faults = config.getboolean('Source file','replace fault codes')
            if self.replace_faults: # fault codes as text
                fault_codes = [self.replace_faultcode(codestring) for codestring in normal_state_raw.split(',')]
                stop_code_values = [self.replace_faultcode(stop_code_string) for stop_code_string in stop_codes_raw.split(',')]
            else:
                fault_codes = [int(code) for code in normal_state_raw.split(',')]
                stop_code_values = [int(stop_code) for stop_code in stop_codes_raw.split(',')]
            self.normal_state = fault_codes
            self.stopcodes = stop_code_values
            self.id = config.get('Source file','id')
            self.result_dir = config.get('Output', 'result directory', fallback=self.get_fallback_value('Output','result directory'))
            status_stops_raw = config.get('Data Structure', 'status index', fallback=self.get_fallback_value('Data Structure', 'status index'))
            self.status_stop_index = [int(code) for code in status_stops_raw.split(',')]
            fault_column_string = config.get('Source file','fault columns')
            self.fault_columns = [int(column_index) for column_index in fault_column_string.split(',')]
        except configparser.NoOptionError as missing_value:
            print("missing config option in {0}: {1}".format(filename, missing_value))
            sys.exit(1)
        except configparser.NoSectionError as missing_section:
            print("missing config section in {0}: {1}".format(filename, missing_section))
            sys.exit(1)
        except ValueError as wrong_value:
            print("Wrong type of value in {0}: {1}".format(filename, wrong_value))
            sys.exit(1)

    def replace_faultcode(self, code):
        """
        Replace textual fault_code with a value from fault_dict. If the wanted faultcode is not in fault_dict,
        add it as a new maximum value into it and then return the new replacement value.

        :param code:
        :return the replacement fault code:
        """

        if code in self.fault_dict:
            return self.fault_dict[code]
        else:
            self.fault_dict[code] = max(self.fault_dict.values()) + 1
            return self.fault_dict[code]

    def set_binning_options_from_file(self, filename):
        """
        set bin division based on a config file
        """
        config = configparser.ConfigParser()
        config.read(filename)
        if config.has_section('Binning'):
            try:
                min_windbin = float(config.get('Binning', 'minimum wind speed', fallback=self.get_fallback_value('Binning', 'minimum wind speed')))
                max_windbin = float(config.get('Binning', 'maximum wind speed', fallback=self.get_fallback_value('Binning', 'maximum wind speed')))
                windbin_width = float(config.get('Binning', 'wind speed bin size', fallback=self.get_fallback_value('Binning', 'wind speed bin size')))
                directionbin_width = float(config.get('Binning', 'wind direction bin size', fallback=self.get_fallback_value('Binning', 'wind direction bin size')))
                self.wind_bins = np.arange(min_windbin, max_windbin, windbin_width)
                self.direction_bins = np.arange(0,360,directionbin_width)
            except configparser.NoOptionError as missing_value:
                print("missing config option in {0}: {1}".format(filename, missing_value))
                sys.exit(1)
            except ValueError as wrong_value:
                print("Wrong type of value in {0}: {1}".format(filename, wrong_value))
                sys.exit(1)
        else:
            print("No binning options set, using defaults")

    def set_filtering_options_from_file(self, filename):
        """
        set filtering options based on a config file
        """
        config = configparser.ConfigParser()
        config.read(filename)
        if config.has_section('Filtering'):
            try:
                self.pc_low_limit = int(config.get('Filtering', 'power drop limit', fallback=self.get_fallback_value('Filtering', 'power drop limit')))
                self.pc_high_limit = int(config.get('Filtering', 'overproduction limit', fallback=self.get_fallback_value('Filtering', 'overproduction limit')))
                self.icing_time = int(config.get('Filtering', 'icing time', fallback=self.get_fallback_value('Filtering', 'icing time')))
                self.stop_level = float(config.get('Filtering', 'stop limit multiplier', fallback=self.get_fallback_value('Filtering',  'stop limit multiplier')))
                self.stop_time = int(config.get('Filtering', 'stop time filter', fallback=self.get_fallback_value('Filtering',  'stop time filter')))
                self.state_filter_type = int(config.get('Filtering', 'statefilter type', fallback=self.get_fallback_value('Filtering',  'statefilter type')))
                self.pc_binsize = int(config.get('Filtering', 'min bin size', fallback=self.get_fallback_value('Filtering',  'min bin size')))
                self.pc_dist_filter = config.getboolean('Filtering', 'distance filter', fallback=self.get_fallback_value('Filtering',  'distance filter'))
                self.power_level_filter_limit = float(config.get('Filtering', 'power level filter', fallback=self.get_fallback_value('Filtering',  'power level filter')))
                self.icing_temperature_limit = float(config.get('Filtering', 'temperature filter', fallback=self.get_fallback_value('Filtering',  'temperature filter')))
                self.reference_temperature_limit = float(config.get('Filtering', 'reference temperature', fallback=self.get_fallback_value('Filtering',  'reference temperature')))
                self.stop_filter_type = int(config.get('Filtering', 'stop filter type', fallback=self.get_fallback_value('Filtering',  'stop filter type')))
                dt_format = config.get('Source file', 'datetime format', raw=True, fallback=self.get_fallback_value('Source file', 'datetime format'))
                starttime_str = config.get('Filtering', 'Start time', fallback=self.get_fallback_value('Filtering', 'start time'))
                if starttime_str.upper() != 'NONE':
                    self.starttimestamp = datetime.datetime.strptime(starttime_str, dt_format)
                stoptime_str = config.get('Filtering', 'Stop time', fallback=self.get_fallback_value('Filtering', 'stop time'))
                if stoptime_str.upper() != 'NONE':
                    self.stoptimestamp = datetime.datetime.strptime(stoptime_str, dt_format)

            except configparser.NoOptionError as missing_value:
                print("missing config option in {0}: {1}".format(filename, missing_value))
                sys.exit(1)
            except ValueError as wrong_value:
                print("Wrong type of value in {0}: {1}".format(filename, wrong_value))
                sys.exit(1)

    def set_ips_options_from_file(self, filename):
        """
        set config options for a heated site, first check if "Icing" section even exists, then set the options
        # if ice detection is set to false or IPS is set to false, don't try to read their options
        """
        config = configparser.ConfigParser()
        config.read(filename)
        if config.has_section('Icing'):
            try:
                self.heated_site = config.getboolean("Icing","heating")
                self.ice_detection = config.getboolean("Icing","ice detection")
                self.ice_alarm_index = int(config.get("Icing","icing alarm index"))
                if self.replace_faults and (self.ice_alarm_index in self.fault_columns):
                    ice_alarm_raw = config.get("Icing", "icing alarm code")
                    self.ice_alarm_value = self.replace_faultcode(ice_alarm_raw)
                else:
                    self.ice_alarm_value = int(config.get("Icing", "icing alarm code"))
                heating_index_raw = config.get("Icing","ips status index")
                heating_value_raw = config.get("Icing","ips status code")
                self.heating_status_index = [int(code) for code in heating_index_raw.split(',')]
                if self.replace_faults and any({*self.heating_status_index} & {*self.fault_columns}): # status codes as text
                    self.heating_status_value = [self.replace_faultcode(codestring) for codestring in heating_value_raw.split(',')]
                else:
                    self.heating_status_value = [int(code) for code in heating_value_raw.split(',')]

                self.heating_status_type = int(config.get("Icing","ips status type"))
                self.heating_power_index = int(config.get("Icing","ips power consumption index"))
            except configparser.NoOptionError as missing_value:
                print("missing config option in {0}: {1}".format(filename, missing_value))
                sys.exit(1)
            except configparser.NoSectionError as missing_section:
                print("missing config section in {0}: {1}".format(filename, missing_section))
                sys.exit(1)
            except ValueError as wrong_value:
                print("Wrong type of value in {0}: {1}".format(filename, wrong_value))
                sys.exit(1)
        else:
            print("no [Icing] section in {0}, ignoring IPS options".format(filename))

    def state_filter_data(self, data):
        """
        remove all data where the state variable is something else than normal_state
        correct state variable values depend on turbine type
        if exclude set to true, remove all lines where state==normal_state
        exclude is set in a class variable

        if state_filter_type == 3 filter removes data below a certain threshold
        threshold is set in normal_state
        state filter type 3 is used in case there is no explicit turbine state and the
        filtering has to be done using output power or such


        :param data: data to be filtered
        :return: filtered data with the filterd liens removed
        """

        if self.state_filter_type == 2:
            exclude = True
        else:
            exclude = False

        #if exclude:
            #return data[data[:, self.state_index] != self.normal_state, :]
            #return np.array([line for line in data if line[self.state_index] not in self.normal_state])
        #else:
            #return data[data[:, self.state_index] == self.normal_state, :]
            #return np.array([line for line in data if line[self.state_index] in self.normal_state])
        #TODO:
            # fix this mess, remove exclude from where it iss and have all filter type switches in the same place
        filtered_data = []
        for line in data:
            # state_vals = [line[i] for i in self.state_index]
            # state_val_check = all([j in self.normal_state for j in state_vals]) # if all in state_vals are in normal state evaluates as True
            state_val_check_vars = []
            for normal_state_index,value_index in enumerate(self.state_index):
                if self.state_filter_type == 3:
                    state_val_check_vars.append(line[value_index] >= self.normal_state[normal_state_index])
                elif self.state_filter_type == 4:
                    state_val_check_vars.append(line[value_index] <= self.normal_state[normal_state_index])
                else:
                    state_val_check_vars.append(line[value_index] == self.normal_state[normal_state_index])
            state_val_check = all(state_val_check_vars)
            if exclude:
                if not state_val_check:
                    filtered_data.append(line)
            else:
                if state_val_check:
                    filtered_data.append(line)
        return np.array(filtered_data)

    def temperature_filter_data(self, data):
        """
        remove all data points with temperature below set threshold

        :param data: input data
        :return: data set containing only the data in previously specified range
        """
        # suppress the runtimewarning caused by nans in data
        # the result is what we want: nans case the comparison to evaluate as false
        with np.errstate(invalid = 'ignore'):
            return data[data[:, self.temp_index] >= self.reference_temperature_limit, :]

    def power_level_filter(self, data):
        """
        remove all data points where power is below the wanted limit level

        limit is defined as percentage of rated power

        :param data: unfiltered input data
        :param limit_level: filtering level as fraction of rated
        :return: data with the unwanted timestamps removed
        """
        # suppress the runtimewarning caused by nans in data
        # the result is what we want: nans case the comparison to evaluate as false
        with np.errstate(invalid = 'ignore'):
            return data[data[:, self.pow_index] >= (self.power_level_filter_limit * self.rated_power), :]

    def wind_speed_filter(self,data,limit_level):
        """
        remove all data points with wind speed below a preset level

        :param data: original data
        :param limit_level: filtering level
        :return: filtered data
        """
        # suppress the runtimewarning caused by nans in data
        # the result is what we want: nans case the comparison to evaluate as false
        with np.errstate(invalid = 'ignore'):
            return data[data[:, self.ws_index] >= limit_level, :]

    def time_filter_data(self, data):
        """

        :param data: the data to be filtered
        :param start: start time as datetime.datetime
        :param stop: stop time as datetime.datetime
        :return: filtered dataset
        """
        return data[np.logical_and(data[:, self.ts_index] >= self.starttimestamp, data[:, self.ts_index] < self.stoptimestamp), :]


    def expand_array(self, arr, n):
        """
        add n columns to the right-hand side of a numpy ndarray
        used for bin indices when binning data

        :param arr: original array
        :param n: number column to be added
        :return: appended array
        """
        for i in range(n):
            arr = np.c_[arr, np.zeros(np.shape(arr)[0])]
        return arr

    def bin_measurement(self, data, bin_centers, comp_column, bin_index_column, direction=False):
        """
        puts a measurement into an appropriate bin

        :param data: contains a single line of measurements
        :param bin_centers: a numpy.ndarray containing centerpoints of the bin division
        :param comp_column: column index of the variable used for binning e.g.
                            wind speed index when searching for the appropriate wind speed bin

        :param bin_index_column: column index where bin indexes are stored
        :return: parameter data with the bin index appended

        """
        if direction:
            value = data[comp_column]
            x = np.cos(np.radians(value))
            y = np.sin(np.radians(value))
            bin_x = np.cos(np.radians(bin_centers))
            bin_y = np.sin(np.radians(bin_centers))
            bin_index = np.sqrt((x-bin_x)**2+(y-bin_y)**2).argmin()
            data[bin_index_column] = bin_index
        else:
            data[bin_index_column] = abs(float(data[comp_column])-bin_centers).argmin()
        return data

    def wind_dir_mean(self,a):
        """
        calculates the mean of wind direction measurements contained in array data

        :param a: array of wind direction measurements in degrees
        :return: mean of the array
        """
        y = []
        x = []
        for item in a:
            if not np.isnan(item):
                y.append(np.sin(np.radians(item)))
                x.append(np.cos(np.radians(item)))

        if np.size(y) == 0 or np.size(x) == 0:
            return np.nan
        else:
            my = np.nanmean(y)
            mx = np.nanmean(x)
            angle = np.degrees(np.arctan2(my,mx))

            #wd_mean = np.remainder(360.0 + np.degrees(np.arctan2(my,mx)),360.0)
            wd_mean = (angle +360) % 360
            #print((mx,my,wd_mean))
            return wd_mean

    def put_data_into_bins(self, data, bins, comp_column,direction=False):
        """
        Bins into externally defined set of bins. Adds a column to the data matrix containing a bin index.
        After this contents of any bin can be found using features of a numpy.ndarray

        Example:
            we need contents of bin number 7. This is returned by
                    data[data[:,-1]==7,:]


        :param data: original data that needs to be separated in to bins. A numpy.ndarray
        :param bins: center points of the bins
        :param comp_column: column in the data containing the value used for binning
                            (wind speed index when binning by wind speed)

        :return: expanded array, contains the original data and one additional
                 column that contains a bin index for each line

        """
        binned_data = []
        exp_data = self.expand_array(data, 1)
        for line in exp_data:
            if direction:
                binned_data.append(self.bin_measurement(line, bins, comp_column, -1,True))
            else:
                binned_data.append(self.bin_measurement(line, bins, comp_column, -1))
        return np.array(binned_data)

    def fetch_bin_contents_2d(self, data, bin_index1, bin_number1, bin_index2, bin_number2):
        """
        returns the contents of a particular bin in case that data is binned according to two different variables
        for example wind speed and direction

        :param data: binned data wind bin indexes
        :param bin_index1: column where the first bin index is found
        :param bin_number1: requested bin on the first bin index
        :param bin_index2:  column where the second bin index is found
        :param bin_number2: requested bin on the second bin index
        :return: slice of the data containing the contents of the wanted bin
        """
        return data[np.logical_and(data[:, bin_index1] == bin_number1, data[:, bin_index2] == bin_number2), :]

    def nan_helper(self, y):
        """
        Helper to handle indices and logical indices of NaNs.

        | Input:
        |    - y, 1d numpy array with possible NaNs
        | Output:
        |    - nans, logical indices of NaNs
        |    - index, a function, with signature indices= index(logical_indices),
        |      to convert logical indices of NaNs to 'equivalent' indices
        | Example:
        |     # linear interpolation of NaNs
        |     nans, x= nan_helper(y)
        |     y[nans]= np.interp(x(nans), x(~nans), y[~nans])

        :param y: input array
        :return: converted array
        """

        return np.isnan(y), lambda z: z.nonzero()[0]

    def interpolate_over_nans(self, pc):
        """
        helper function to interpolate over possible nan values in power curves caused by empty bins
        during binning
        input is a single power curve i.e. 2d matrix of wind speed versus power

        :param pc: power curve matrix as returned by self.count_power_curves
        :return: interpolated power curves
        """
        nans, x = self.nan_helper(pc)
        pc[nans] = np.interp(x(nans), x(~nans), pc[~nans])
        return pc

    def distance_to_neighbours(self, pc, speed_bin, direction_bin, variable_index):
        """
        helper function used in power curve post-processing:
        calculates the mean distance of point at index in different curves stored in data
        Operates only on one bin at a time.
        requires power curves divided according to wind speed and direction

        :param pc: original dataset containing the power curves as defined by count_power_curves function
        :param speed_bin: index of active wind speed bin
        :param direction_bin: index of active wind direction bin
        :param variable_index: processed variable. usually power
        :return: mean distance to all other power curves in the particular bin
        """
        (x, y, z) = np.shape(pc)
        # reduce the dimension
        targets = pc[speed_bin, :, variable_index]
        distances = []
        neighbours = np.ones(y).astype('bool')
        neighbours[direction_bin] = False
        distances.append(np.abs(targets[neighbours]-targets[direction_bin]))
        if len(distances) == 0:
            return 0.0
        else:
            return np.nanmean(np.array(distances))

    def distance_filter(self, pc, target_value):
        """
        calculate distances between different power curves,
        if value is dramatically different replace with mean of all others
        goes through all curves bin by bin
        can be useful to automatically weed out outliers in the data

        :param pc: prefilterd power curves
        :param target_value: index of the value used for filtering e.g. power
        :return: fltered power curve matrix

        """
        (x, y, z) = np.shape(pc)
        value_filter = 2.5
        for speed_bin in range(x):
            mean_distances = np.zeros(y)
            for direction_bin in range(y):
                mean_distances[direction_bin] = self.distance_to_neighbours(pc, speed_bin, direction_bin, target_value)
            med_dist = np.nanmedian(mean_distances)
            bad_values = []
            for index,value in enumerate(mean_distances):
                if (value/med_dist) > value_filter:
                    bad_values.append(index)

            neighbours = np.ones(y).astype('bool')
            neighbours[bad_values] = False
            # print("{0}: {1}".format(speed_bin,bad_values))
            mpc = self.mean_power_curve(pc[:, neighbours,:])
            for value in bad_values:
                pc[speed_bin, value, target_value] = mpc[speed_bin, target_value]
        return pc

    def diff_filter(self,data,diff_limit=0.001):
        """
        appplies a filter to data that discards all values that differ less than diff_limit from the previous one
        :param data:
        :param diff_limit:
        :return:
        """
        data_diff = np.diff(data[:,self.pow_index]) # start with power
        data_diff = np.hstack((np.array(0), data_diff))
        mask = data_diff > diff_limit
        return data[mask,:]

    def bin_size_filter(self, pc, size_limit):
        """
        bin size based filtering for the power curve
        removes all data from the bin if not enough values available

        :param pc: power curve matrix
        :param size_limit: number of measurements required for the bin to be used
        :return: a boolean matrix that can be used to mark too small bin as empty
        """

        (x, y, z) = np.shape(pc)
        too_smalls = np.zeros(np.shape(pc)).astype('bool')
        for speed_bin in range(x):
            for direction_bin in range(y):
                if pc[speed_bin, direction_bin, 7] < size_limit:
                    too_smalls[speed_bin, direction_bin, 2] = True
                    too_smalls[speed_bin, direction_bin, 3] = True
                    too_smalls[speed_bin, direction_bin, 4] = True
                    too_smalls[speed_bin, direction_bin, 5] = True
                    too_smalls[speed_bin, direction_bin, 6] = True
                    too_smalls[speed_bin, direction_bin, 8] = True
                    too_smalls[speed_bin, direction_bin, 9] = True
        return too_smalls

    def theoretical_output_power(self, data, power_curves):
        """
        calculates the theoretical, expected output power based on power curve and measured wind speed

        :param data:
        :param power_curve:
        :return: rerference power, in structure [timestamp, interpolated reference power, actual measured output power]
        """
        reference = []
        time_limited_data = self.time_filter_data(data)
        for line in time_limited_data:
            dirbin = np.argmin(np.abs(self.direction_bins - line[self.wd_index]))
            int_pow = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 2])
            int_pow_p10 = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 3])
            int_pow_p90 = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 4])
            uncert_lower_lim = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 8])
            uncert_upper_lim = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 9])
            reference.append((line[self.ts_index], int_pow, line[self.pow_index], int_pow_p10, int_pow_p90, uncert_lower_lim, uncert_upper_lim))
        return np.array(reference)

    def calculate_production(self,data,index,delta=datetime.timedelta(seconds=10*60)):
        """
        calculates total production between from previous time stamp to current, assuming the difference is constant
        skips all occurrences where the difference between two adjacent timestamps is not constant

        NOTE: assumes timestamp is at index 0

        :param data: input data, containing the measured output
        :param index: index of the production measurement
        :param delta: difference between two timestamps defaults to ten minutes
        :return: structure containing [end timestep, production]
        """
        output_data = []
        for i in range(len(data)):
            if i != 0:
                # integrity check
                if ((data[i,0] - data[i-1,0]) > delta) or np.isnan(data[i,index]) or np.isnan(data[i-1,index]) or (data[i,index] <=0.0) or (data[i-1,index] <= 0.0):
                    prod = 0
                else:
                    dur = (data[i,0]-data[i-1,0]).total_seconds()/60.0/60.0 # length in hours
                    pow_at_start = data[i-1,index]
                    pow_at_stop = data[i,index]
                    prod = dur * ((pow_at_start+pow_at_stop) / 2.0)
                output_data.append((data[i,0],prod))
        output_datalen = len(output_data)
        return np.array(output_data)

    def count_power_curves(self, data):
        """
        Calculates a set of power curves from the input data
        bins the data according to wind speed and direction
        the binning and the column indexes of the data are defined in the class variables

        Power curves contain the power curve and the P10 limit for said curve separately
        for each wind direction defined in the wind direction binning.

        output is three dimensional array containing:

            * median wind speed
            * median wind direction
            * P10 value
            * bin size (number of measurements in this particular bin)

        for each speed and direction defined in self.wind_bins and self_direction bins

        missing data (empty bins) are marked as nan
        missing values can then be interpolated over so that there are no empty bins.

        Also possible to do other kinds of filtering to improve the end result and to reduce the
        impact of outliers in the data

        Method automatically filters the data according to elsewhere defined state variable filter
        (is this a good idea???)

        Only part of data where temperature is more than 3 degrees is used to make the power curves

        :param data: input data time series. can be unfiltered
        :param temperature_filter_level: temperature in degrees, all data with temperatures above this level are used to build the reference dataset
        :param lower_limit: percentile used as limit for power reduction (default 10)
        :param upper_limit: percentile used as limit for overproduction (default 90)
        :return pc: a numpy.ndarray that contains the power curves, warning limits and bin sizes for each bin,
                    sorted by wind speed and direction

        """
        # direction_bins = np.array([0])
        # st_data = self.state_filter_data(data, self.normal_state)
        # ref_data = self.temperature_filter_data(data, temperature_filter_level)
        pc = np.zeros((len(self.wind_bins), len(self.direction_bins), 10))
        dir_data = self.put_data_into_bins(data, self.direction_bins, self.wd_index,direction=True)
        binned_data = self.put_data_into_bins(dir_data, self.wind_bins, self.ws_index)
        wind_speed_index = 0
        wind_dir_index = 1
        power_index = 2
        low_limit_index = 3
        high_limit_index = 4
        bin_standard_dev_index = 5
        bin_uncertainty = 6
        bin_uncertainty_lower_lim_index = 8
        bin_uncertainty_upper_lim_index = 9
        bin_size_index = 7
        #print(binned_data)
        for speed_bin_index in range(len(self.wind_bins)):
            for direction_bin_index in range(len(self.direction_bins)):
                bin_contents = self.fetch_bin_contents_2d(binned_data, -1, speed_bin_index, -2, direction_bin_index)
                if bin_contents.size == 0:
                    pc[speed_bin_index, direction_bin_index, wind_speed_index] = self.wind_bins[speed_bin_index]
                    pc[speed_bin_index, direction_bin_index, wind_dir_index] = self.direction_bins[direction_bin_index]
                    # force power to be 0 at wind speed 0, helps with interpolation
                    # and other tricks used to cover missing data
                    if speed_bin_index == 0:
                        replacement = 0
                    else:
                        replacement = np.nan
                    pc[speed_bin_index, direction_bin_index, power_index] = replacement
                    pc[speed_bin_index, direction_bin_index, low_limit_index] = replacement
                    pc[speed_bin_index, direction_bin_index, high_limit_index] = replacement
                    pc[speed_bin_index, direction_bin_index, bin_standard_dev_index] = replacement
                    pc[speed_bin_index, direction_bin_index, bin_uncertainty] = replacement
                    pc[speed_bin_index, direction_bin_index, bin_uncertainty_lower_lim_index] = replacement
                    pc[speed_bin_index, direction_bin_index, bin_uncertainty_upper_lim_index] = replacement
                    pc[speed_bin_index, direction_bin_index, bin_size_index] = bin_contents.size
                else:
                    # suppress runtime errors caused by bins with nothing but nans
                    if np.isnan(bin_contents[:, self.ws_index].astype('float')).all():
                        pc[speed_bin_index, direction_bin_index, wind_speed_index] = np.nan
                    else:
                        pc[speed_bin_index, direction_bin_index, wind_speed_index] = np.nanmedian(bin_contents[:, self.ws_index].astype('float'))
                    if np.isnan(bin_contents[:, self.wd_index].astype('float')).all():
                        pc[speed_bin_index, direction_bin_index, wind_dir_index] = np.nan
                    else:
                        pc[speed_bin_index, direction_bin_index, wind_dir_index] = self.wind_dir_mean(bin_contents[:, self.wd_index].astype('float'))
                    if np.isnan(bin_contents[:, self.pow_index].astype('float')).all():
                        pc[speed_bin_index, direction_bin_index, power_index] = np.nan
                        pc[speed_bin_index, direction_bin_index, low_limit_index] = np.nan
                        pc[speed_bin_index, direction_bin_index, high_limit_index] = np.nan
                        pc[speed_bin_index, direction_bin_index, bin_standard_dev_index] = np.nan
                        pc[speed_bin_index, direction_bin_index, bin_uncertainty] = np.nan
                        pc[speed_bin_index, direction_bin_index, bin_uncertainty_lower_lim_index] = np.nan
                        pc[speed_bin_index, direction_bin_index, bin_uncertainty_upper_lim_index] = np.nan
                    else:
                        #pc[speed_bin_index, direction_bin_index, power_index] = np.nanmean(bin_contents[:, self.pow_index].astype('float'))
                        mean_power = np.nanmedian(bin_contents[:, self.pow_index].astype('float'))
                        power_std_dev = np.nanstd(bin_contents[:, self.pow_index].astype('float'))
                        pc[speed_bin_index, direction_bin_index, power_index] = mean_power
                        pc[speed_bin_index, direction_bin_index, low_limit_index] = ss.scoreatpercentile(bin_contents[:, self.pow_index], self.pc_low_limit)
                        pc[speed_bin_index, direction_bin_index, high_limit_index] = ss.scoreatpercentile(bin_contents[:, self.pow_index], self.pc_high_limit)
                        pc[speed_bin_index, direction_bin_index, bin_standard_dev_index] = power_std_dev
                        # divide by zero possible
                        if pc[speed_bin_index, direction_bin_index, power_index] != 0.0:
                            pc[speed_bin_index, direction_bin_index, bin_uncertainty] = power_std_dev / mean_power * 100.0
                        else:
                            pc[speed_bin_index, direction_bin_index, bin_uncertainty] = 0.0
                        # upper and lower limits needed for production uncertainty
                        pc[speed_bin_index, direction_bin_index, bin_uncertainty_lower_lim_index] = max(0.0, mean_power - power_std_dev)
                        # prevent upper liimt from going below lower limit
                        if mean_power > self.rated_power:
                            power_upper_limit = mean_power + power_std_dev
                        else:
                            power_upper_limit = min(mean_power + power_std_dev, self.rated_power)
                        pc[speed_bin_index, direction_bin_index, bin_uncertainty_upper_lim_index] = power_upper_limit
                    bin_rows, bin_columns = bin_contents.shape
                    pc[speed_bin_index, direction_bin_index, bin_size_index] = bin_rows

        #TODO:
            # make filtering optional, on by default

        too_smalls = self.bin_size_filter(pc, self.pc_binsize)
        pc[too_smalls] = np.nan
        # interpolate over missing data
        for dir_bin_index in range(len(self.direction_bins)):
            try:
                pc[:, dir_bin_index, power_index] = self.interpolate_over_nans(pc[:, dir_bin_index, power_index])
                pc[:, dir_bin_index, low_limit_index] = self.interpolate_over_nans(pc[:, dir_bin_index, low_limit_index])
                pc[:, dir_bin_index, high_limit_index] = self.interpolate_over_nans(pc[:, dir_bin_index, high_limit_index])
                pc[:, dir_bin_index, bin_standard_dev_index] = self.interpolate_over_nans(pc[:,dir_bin_index, bin_standard_dev_index])
                pc[:, dir_bin_index, bin_uncertainty] = self.interpolate_over_nans(pc[:, dir_bin_index, bin_uncertainty])
                pc[:, dir_bin_index, bin_uncertainty_lower_lim_index] = self.interpolate_over_nans(pc[:, dir_bin_index, bin_uncertainty_lower_lim_index])
                pc[:, dir_bin_index, bin_uncertainty_upper_lim_index] = self.interpolate_over_nans(pc[:, dir_bin_index, bin_uncertainty_upper_lim_index])
            except ValueError:
                # import ipdb;ipdb.set_trace()
                print('Error in power curve generation!!')
                print('Dir bin index: {}'.format(dir_bin_index))
                print(pc[:, dir_bin_index, :])
        # filter out obviously wrong values only usable if there is more than one direction bin
        [x,y,z] = np.shape(pc)
        if self.pc_dist_filter and (y > 1):
            pc = self.distance_filter(pc, power_index)
            pc = self.distance_filter(pc, low_limit_index)
            pc = self.distance_filter(pc, high_limit_index)
        return pc

    def mean_power_curve(self, pc):
        """
        calculates mean (direction independent power curve)

        :param pc:
        :return: mean power curve, averagesd accross direction bins
        """
        return np.nanmean(pc, 1)

    def prettyprint_power_curves(self, pc, index=2, print_result=False):
        """
        print matrix representations of different variables inside the power curve data structure
        returns a human readable matrix of wanted quantity

        :param pc: power curve array
        :param index: index in the power curve to be printed:

                2 : mean power
                3 : P90
                4 : P10
                5 : bin standard deviation
                6 : bin uncertainty (std_dev / mean)
                7 : bin size

        :param print_result: if True, prints the resulting array to stdout, defaults to False
        :return: sanitized matrix

        """
        power_curve_table = pc[:, :, index]
        # add headers
        power_curve_table = np.r_[np.reshape(self.direction_bins, (1, len(self.direction_bins))), power_curve_table]
        ws_column = np.r_[np.nan, self.wind_bins]
        power_curve_table = np.c_[ws_column, power_curve_table]
        field_width = 10
        precision = 1
        separator = '\t'
        output = []
        for line in power_curve_table:
            outputline = ''
            for index, item in enumerate(line):
                if np.isnan(item):
                    token = field_width * ' '
                else:
                    token = '{0:>{1}.{2}f}'.format(item, field_width, precision)
                if index == 0:
                    outputline += token
                else:
                    outputline += separator
                    outputline += token
            outputline += '\n'
            if print_result:
                print(outputline)
            output.append(outputline)
        return output

    def power_curve_uncertainty_average(self, pc, low_limit=4, high_limit=15):
        """
        Calculate a mean value for power curve uncertainty for the summary file
        use only wind speeds between low_limit and high_limit and return just one value

        :param pc: power curve structure
        :param low_limit: lowest applicable wind speed
        :param high_limit: highest applicable wind speed
        :return: one value to represent power curve uncertainty
        """
        # take direction bin wise mean of all power curves first
        mpc = self.mean_power_curve(pc)
        mask = (mpc[:,0]>= low_limit) & (mpc[:,0]<=high_limit)
        uncertainties = mpc[mask,6]
        return (np.nanmean(uncertainties))

    def timefilter_ice_alarms(self, data, window):
        """
        clean outliers from ice alarms, demand, that there is at least window number of consecutive alarms
        begin the icing event from the first switch from 0->1 end at the switch from 1->0

        :param data: time series of alarms created by the power_alarms function
        :param window: length of hte filtering window
        :return data: reformatted data, with individual events removed
        """
        max_index = len(data)-window
        data_index = 0
        while data_index < max_index:
            consecutive_alarms = 0
            try:
                while data[data_index + consecutive_alarms, 1] != 0:
                    consecutive_alarms += 1
            except IndexError:  # would raise error if this reaches the final index in the data, we can ignore this
                pass
            if consecutive_alarms > 0:
                if consecutive_alarms < window:
                    data[data_index:(data_index + consecutive_alarms), 1] = 0
                data_index += consecutive_alarms
            else:
                data_index += 1
        return data

    def power_alarms(self, data, power_curves, time_filter=True, over=False):
        """
        flag timestamps that match wanted power alarm criteria.

        For each measurement in data, search the proper value from the power curves
        If the power at any moment is below the previously calculated P10 value AND temperature is below a
        threshold, flag the timestamp.


        after all the data is processed do an additional time-based filtering step where all cases where there are not
        enough consecutive alarms are discarded.
        default idea is to demand that the power should remain below the P10 value for at least half an hour before
        the incident is considered a confirmed icing event

        Another considered ice class is cases where iced anemometer results in apparent overproduction.
        These cases are seen in the data as appearing above the P90 line. They are flagged in a similar way and
        same time filtering applies here as well

        The specification lists these as ice case A (production loss) and ice case C (overproduction)
        These are marked in the output as 1 for case A and 3 for case C in the alarm variable

        TODO:
            assumes ten minute data, should probably be a parameter


        :param data: input data
        :param power_curves: calculated power curves, binned based on wind speed and direction
        :param time_filter: if True, an additional time filter is applied to the data
        :param time_filter_length: number of consecutive values below the alarm limit required to trigger the icing alarm
        :param over: if True, flags the timestamps where the power is above P90 instead
        :return: an array of the format [timestamp, alarm, wind speed, reference power, temperature, power, limit]
        """
        pow_alarms = []
        timed = datetime.timedelta(seconds=601)
        for index,line in enumerate(data):
            # integrity check for the data
            if (index != 0) and (index != len(data)-1):
                continuous = (line[self.ts_index] - data[index-1,self.ts_index]) < timed and (data[index+1,self.ts_index] - line[self.ts_index]) < timed
            else:
                continuous = False
            # pick index of active direction bin
            dirbin = np.argmin(np.abs(line[self.wd_index]-self.direction_bins))
            # pick the active wind speed bin
            windbin = np.argmin(np.abs(line[self.ws_index]-self.wind_bins))
            #wind and power at active bin

            # interpolate the value from power and limit (P10) curve to matches the current wind speed
            # np.interp does piecewise linear interpolation that can be assumed to be good enough in this
            # case. The power curve is close to linear between any two bins
            if over:
                int_lim = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 4])
            else:
                int_lim = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 3])
            int_pow = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 2])

            if continuous:
                if over:
                    if (line[self.pow_index] >= int_lim) and (line[self.temp_index] <= self.icing_temperature_limit):
                        pow_alrm = 3.0
                    else:
                        pow_alrm = 0.0
                else:
                    if (line[self.pow_index] <= int_lim) and (line[self.temp_index] <= self.icing_temperature_limit):
                        pow_alrm = 1.0
                    else:
                        pow_alrm = 0.0
            else:
                pow_alrm = 0.0
            pow_alarms.append((line[self.ts_index], pow_alrm, line[self.ws_index], int_pow, line[self.temp_index], line[self.pow_index], int_lim))
        alarms = np.array(pow_alarms)
        if time_filter:
            filtered_alarms = self.timefilter_ice_alarms(alarms, self.icing_time)
            return filtered_alarms
        else:
            return alarms

    def power_loss_during_alarm(self, data, ips_alarm=False):
        """
        Collect the start and stop times of icing alarms and calculate the total
        power/production loss during the icing event

        counts the production loss by calculating the approximate area between
        the estimated production curve and the actual production curve as calculated by power_alarms

        :param data: data produced by the power_alarms function
        :param ips_alarm: set to True if alarm was caused by IPS system
        :return: a structure containing the starts and stops and losses formatted as [starttime stoptime powerloss]
        """

        datalen = np.shape(data)[0]
        alarm_stats = []
        if datalen > 0:
            # calculate the times when the alarm changes on and off
            # numpy.diff calculates array[n+1] - array[n]
            alarm_diff = np.diff(data[:, 1])
            # pad a zero to the beginning, unless data[0] is an alarm
            if data[0,1] != 0.0:
                alarm_diff = np.hstack((np.array(1), alarm_diff))
            else:
                alarm_diff = np.hstack((np.array(0), alarm_diff))


            # now icing starts at times when diff == 1 and stops when diff == -1
            starts = data[alarm_diff > 0, 0]
            stops = data[alarm_diff < 0, 0]

            num_starts = len(starts)
            num_stops = len(stops)

            max_index = min((num_starts, num_stops))
            index = 0

            # sort starts and stops into an array
            try:
                while (index < max_index) and (datalen > 0):
                    try:
                        starttime = starts[index]
                        stoptime = stops[index]
                        if starttime > stoptime:
                            raise TimingError(starttime,stoptime,index)

                        # pull thecorresponding start and stoptimes from real data
                        start_index = np.argmin(np.abs(data[:, 0]-starttime))
                        stop_index = np.argmin(np.abs(data[:, 0]-stoptime))

                        loss_sum = 0
                        ips_sum = 0
                        for i in range(start_index, stop_index, 1):
                            # step duration in hours
                            step_duration = (data[i+1, 0]-data[i, 0]).total_seconds()/60.0/60.0
                            loss_at_start = data[i, 3]-data[i, 5]
                            loss_at_stop = data[i+1, 3]-data[i+1, 5]
                            # if either of these is np.nan add a zero to the loss sum
                            if np.isnan(loss_at_start) or np.isnan(loss_at_stop):
                                loss_sum += 0.0
                                if ips_alarm:
                                    ips_sum += 0
                            else:
                                # integrate the losses using trapezoidal rule
                                loss_sum += step_duration * ((loss_at_start + loss_at_stop)/2.0)
                                if ips_alarm:
                                    ips_sum += step_duration * ((data[i,7] + data[i+1,7])/2.0)
                        mean_power_drop = np.nanmean(data[start_index:stop_index,3].astype(np.float32)-data[start_index:stop_index,5].astype(np.float32))
                        mean_power = np.nanmean(data[start_index:stop_index,5].astype(np.float32))
                        mean_reference_power = np.nanmean(data[start_index:stop_index,3].astype(np.float32))
                        mean_wind_speed = np.nanmean(data[start_index:stop_index,2].astype(np.float32))
                        mean_temperature = np.nanmean(data[start_index:stop_index,4].astype(np.float32))
                        event_length = (data[stop_index,0]- data[start_index,0]).total_seconds()/60.0/60.0
                        #alarm_stats.append((starttime, stoptime, loss_sum, event_length , mean_power_drop, mean_power, mean_reference_power, mean_wind_speed, mean_temperature))
                        if ips_alarm:
                            if self.heating_power_index < 0:
                                alarm_stats.append((starttime, stoptime, loss_sum, event_length , mean_power_drop, mean_power, mean_reference_power, mean_wind_speed, mean_temperature ,0.0))
                            else:
                                alarm_stats.append((starttime, stoptime, loss_sum, event_length , mean_power_drop, mean_power, mean_reference_power, mean_wind_speed, mean_temperature,ips_sum))
                        else:
                            alarm_stats.append((starttime, stoptime, loss_sum, event_length , mean_power_drop, mean_power, mean_reference_power, mean_wind_speed, mean_temperature))
                    except TimingError as e:
                        import pdb;pdb.set_trace()
                        print("Start after stop at index {0} in {1}".format(e.index, self.id))
                        print("start: {0}; stop: {1}".format(e.start.strftime(e.dateformat), e.stop.strftime(e.dateformat)))
                    index += 1
            except IndexError:
                print("out of bounds at index: {0}".format(index))
                print("num starts: {0}; num stops: {1}".format(num_starts, num_stops))


        return np.array(alarm_stats, dtype=object)

    def air_density_correction(self, data):
        """
        Calculate air density correction for wind speed according to specifications in the IEA document
        returns a new array with corrected wind speed in place of the measured one

        Corrected wind speed for the site can be calculated as:

        | ws_site = ws_std*((temp_site*P_std)/(temp_std*(101325*(1-2.2557e-5*h)^5.25588)))^(1/3)
        |
        | ws_site is the corrected wind speed for the site
        | ws_std is the measured nacelle wind speed
        | temp_site is the site temperature
        | P_std is the standard air pressure at sea level (101325 Pa)
        | temp_std is the standard temperature of 15 C (288.15 K)
        | h is site height in meters

        :param data:
        :return: corrected data
        """

        p_std = 101325
        temp_std = 288.15
        kelvin = 273.15
        new_data = []
        for i, line in enumerate(data):
            new_line = []
            for j, item in enumerate(line):
                if j != self.ws_index:
                    new_line.append(item)
                else:
                    # density_correction = ((line[self.temp_index]+kelvin)*p_std)/(temp_std*(p_std*((1-self.site_elevation*2.2557e-5)**5.25588)))
                    density_correction = (temp_std/(line[self.temp_index]+kelvin))*((1-self.site_elevation*2.2557e-5)**5.25588)
                    if np.isnan(density_correction):
                        ws_site = np.nan
                    else:
                        sign = np.sign(density_correction)
                        ws_site = line[self.ws_index] * sign * (np.abs(density_correction))**(1/3)
                    new_line.append(ws_site)
            new_data.append(new_line)
        return np.array(new_data)

    def count_availability(self, data):
        """
        Calculate availability number for data

        availability tells in % the amount of possible data available in the dataset
        checks if there is data available for each timestamp between first and last timestamp
        if there is, returns availability of 100 %

        does not check data integrity, only if there is some kind of data available. Available data could be garbage.

        :param data: data array of the time series
        :return: availability number
        """
        start_time = min(data[:, self.ts_index])
        stop_time = max(data[:, self.ts_index])
        # set timestep to smallest value found unless its 0
        timestep = np.min(np.diff(data[:,self.ts_index]))
        if timestep.total_seconds() == 0.0:
            timestep = data[1, self.ts_index] - data[0, self.ts_index]
        timelength = stop_time - start_time
        stepcount = timelength / timestep
        availability = len(data) / stepcount

        return availability



    def find_icing_related_stops(self, data, power_curve):
        """
        Finds timestamps from the data, when the turbine has stopped for whatever reason

        uses filtering requirements defined in the specification document: pwr_mean< 0.005*P_rated

        ToDo:
            Should we add minimum wind speed here, if turbine stops during an icing event it's either caused by icing or low wind
            Should we only mark the points here where wind speed is above cut-in

        :param data: timeseries data of output
        :param power_curve: power curve array used
        :return: filtered data with stops flagged
        """
        filtered_data = []
        stop_limit = self.stop_level * self.rated_power
        # [timestamp, alarm, wind speed, reference power, temperature, power]
        pow_alarms = self.power_alarms(data, power_curve, False) # do time filtering only once
        for index, line in enumerate(pow_alarms):
            # if (line[1] == 1) and (line[5] <= stop_limit) and (line[3] >= stop_limit):
            #     line[1] = 2.0
            # power level filter is here to avoid double classifying points to two different classes
            if (line[1] == 1) and (line[5] <= (self.rated_power * self.power_level_filter_limit)):
            # change this to look forward so tha tif the turbine will stop within a window of mark also the points where we
            # are above the stop limit to belonging into the stop
                stops = 0
                for i in range(index, min(len(pow_alarms), index+self.stop_time)):
                    templine = pow_alarms[i, :]
                    if (templine[5] <= stop_limit) and (templine[3] >= stop_limit):
                        stops += 1
                if stops > 0:
                    line[1] = 2.0
                else:
                    line[1] = 0
            else:
                line[1] = 0
            filtered_data.append(line)

        time_filtered_data = self.timefilter_ice_alarms(np.array(filtered_data), self.stop_time)
        return time_filtered_data

    def status_code_stops(self, data, power_curves, filter_type="stop"):
        """
        Flag the moments in data where the turbine status code indicates icing
        The statuscode is defined in self.stopcodes

        :param data: input data to be processed
        :return [timestamp, alarm, wind speed, reference power, temperature, power, limit]:
        """
        output = []
        for line in data:
            flag = False
            # for item in self.ice_stop_index:
            #     if line[item] in self.stopcodes:
            #         flag = True
            if filter_type == 'stop':
                # if (self.stop_filter_type == 2 and line[self.status_stop_index] not in self.stopcodes) or \
                #         (self.stop_filter_type == 1 and line[self.status_stop_index] in self.stopcodes):
                #     flag = True
                if self.stop_filter_type == 2:
                    flag = any([line[i] not in self.stopcodes for i in self.status_stop_index])
                elif self.stop_filter_type == 1:
                    flag = any([line[i] in self.stopcodes for i in self.status_stop_index])
                else:
                    pass
            elif filter_type == 'ips':
                # if (self.heating_status_type == 2 and line[self.heating_status_index] != self.heating_status_value) or \
                #         (self.heating_status_type == 1 and line[self.heating_status_index] == self.heating_status_value):
                #     flag=True
                if self.heating_status_type == 2:
                    flag = any([line[i] not in self.heating_status_value for i in self.heating_status_index])
                elif self.heating_status_type == 1:
                    flag = any([line[i] in self.heating_status_value for i in self.heating_status_index])
                else:
                    pass
            elif filter_type == 'icing':
                if line[self.ice_alarm_index] == self.ice_alarm_value:
                    flag = True
            output_line =[]
            output_line.append(line[self.ts_index]) # 0
            if flag:
                if filter_type == 'stop':
                    output_line.append(4.0)
                elif filter_type == 'ips':
                    output_line.append(5.0)
                elif filter_type == 'icing':
                    output_line.append(6.0)
            else:
                output_line.append(0.0) # 1
            output_line.append(line[self.ws_index]) # 2
            # pick index of active direction bin
            dirbin = np.argmin(np.abs(line[self.wd_index] - self.direction_bins))
            int_lim = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 3])
            int_pow = np.interp(line[self.ws_index], power_curves[:, dirbin, 0], power_curves[:, dirbin, 2])
            output_line.append(int_pow) # 3
            output_line.append(line[self.temp_index]) # 4
            output_line.append(line[self.pow_index]) # 5
            output_line.append(int_lim) # 6
            if filter_type == 'ips':
                if self.heating_power_index < 0:
                    output_line.append(0.0)
                else:
                    output_line.append(line[self.heating_power_index]) # 7
            output.append(np.array(output_line))
        return np.array(output)

    def combine_timeseries(self, pow_alms1,stops,pow_alms2):
        """
        combine all different types of alarms into one big timeseries

        Timeseries file combines the alarm files into one timeseries that classifies the ice cases according ot the naming convention in the documentation

        1 = power loss
        2 = stop
        3 = overproduction

        :param pow_alms1:
        :param stops:
        :param pow_alms2:
        :return:
        """

        # stops timeseries longer because it uses different source data

        common_indexes1 = [index1 for index1, line1 in enumerate(stops) if line1[0] in pow_alms1[:,0]]
        common_indexes2 = [index2 for index2, line2 in enumerate(stops) if line2[0] in pow_alms2[:,0]]
        combined_ts = stops
        combined_ts[common_indexes1,1] += pow_alms1[:,1]
        combined_ts[common_indexes2,1] += pow_alms2[:,1]
        return combined_ts


    def define_removable_indexes(self,data,timings):
        """
        calculate the start and stop indexes in data to remove all data defined in the array timings

        :param data: original dataset
        :param timings: array containg the incident starts and stops
        :return: indexes that can be used to filter the original data, a list of ranges
        """
        removed_indexes = []
        for event in timings:
            event_start = event[0]
            event_stop = event[1]
            event_start_index = np.fromiter(map(datetime.timedelta.total_seconds,np.abs(data[:,self.ts_index]-event_start)),dtype='float').argmin()
            event_stop_index = np.fromiter(map(datetime.timedelta.total_seconds,np.abs(data[:,self.ts_index]-event_stop)),dtype='float').argmin()
            removed_indexes.extend(list(range(event_start_index,event_stop_index,1)))
        return removed_indexes

    def increase_reference_dataset(self, data, stop_timings, alarm_timings, over_timings):
        """
        re-increase the size of reference dataset to include all the non-iced datapoints.

        :param data: original dataset
        :param stop_timings: stops calculated from the data
        :param alarm_timings: alarm incidents calculated from the data
        :param over_timigns: overproduction incidents from the data
        :return: new reference dataset
        """
        stop_removal = self.define_removable_indexes(data,stop_timings)
        alarm_removal = self.define_removable_indexes(data,alarm_timings)
        over_removal = self.define_removable_indexes(data,over_timings)
        removed_indexes = [*stop_removal,*alarm_removal,*over_removal]
        new_ref = []
        for index,line in enumerate(data):
            if index not in removed_indexes:
                new_ref.append(line)
        return np.array(new_ref)



    def one_year_month_sums(self, data, wanted_year, index):
        """
        Helper function, calculates the monthly sums of any timeseries data  for a given year
        :param data:
        :param wanted_year:
        :param index:
        :return:
        """
        months = np.arange(1, 13)
        monthly_sums = np.zeros(12)
        for line in data:
            if line[0].year == wanted_year:
                monthly_sums[line[0].month-1] += line[index]
        dated_sums = []
        for i, s in enumerate(monthly_sums):
            dated_sums.append((datetime.datetime(wanted_year, months[i], 1), s))
        return np.array(dated_sums)


    def calculate_production_stats(self, data, pc, ice_alarms, ice_stops, status_stops, ips_on, ice_detection):
        """
        Calculates month-by-month statistics from the data.

        :param data: input data used to asses production
        :param pc: power curve used to calculate theoretical production
        :param ice_alarms: time series of icing alarms
        :param ice_stops: time series of icing induced stops
        :param status_stops: time series of stops as indicated by a statuscode in the scada
        :param ips_on: toggle if IPS is available or not
        :param ice_detection: timeseries of icing events as detected by an ice detector
        :return:
        """

        power_reference = self.theoretical_output_power(data,pc)
        theoretical_production = self.calculate_production(power_reference,1)
        actual_production = self.calculate_production(power_reference,2)
        #pow_alarms.append((line[0], pow_alrm, line[self.ws_index], int_pow, line[self.temp_index], line[self.pow_index], int_lim))
        iced_power_drop_events = ice_alarms[ice_alarms[:,1] == 1.0, :]
        # iced_power_drops = np.hstack((iced_power_drop_events[:,0], iced_power_drop_events[:,3]-iced_power_drop_events[:,5]))
        iced_power_drops_power = np.c_[iced_power_drop_events[:,0], iced_power_drop_events[:,3]-iced_power_drop_events[:,5]]
        iced_power_drops = self.calculate_production(iced_power_drops_power,1)
        ice_stop_events = ice_stops[ice_stops[:,1] == 2.0]
        # iced_stops = np.hstack((ice_stop_events[:,0], ice_stop_events[:,3]-ice_stop_events[:,5]))
        iced_stops_power = np.c_[ice_stop_events[:,0], ice_stop_events[:,3]-ice_stop_events[:,5]]
        iced_stops = self.calculate_production(iced_stops_power,1)
        # status
        if status_stops is not None:
            status_stop_events = status_stops[status_stops[:, 1] == 4.0]
            # iced_stops = np.hstack((ice_stop_events[:,0], ice_stop_events[:,3]-ice_stop_events[:,5]))
            status_stops_power = np.c_[status_stop_events[:,0], status_stop_events[:,3]-status_stop_events[:,5]]
            status_stops_prod = self.calculate_production(status_stops_power,1)
        else:
            status_stop_events = None
            status_stops_power = None
            status_stops_prod = None

        ##############
        # IPS section
        ##############
        if ips_on is not None: # If there is no icing section IPS statistics are not calculated
            ips_stop_events = ips_on[ips_on[:, 1] == 5.0]
            # iced_stops = np.hstack((ice_stop_events[:,0], ice_stop_events[:,3]-ice_stop_events[:,5]))
            ips_on_power = np.c_[ips_stop_events[:,0], ips_stop_events[:,3]-ips_stop_events[:,5]]
            ips_on_prod = self.calculate_production(ips_on_power,1)
            ice_detection_events = ice_detection[ice_detection[:, 1] == 6.0]

            #ips consumption
            if self.heating_power_index < 0:
                ips_self_consumption = 0.0
            else:
                ips_self_consumption = self.calculate_production(data,self.heating_power_index)

            # iced_stops = np.hstack((ice_stop_events[:,0], ice_stop_events[:,3]-ice_stop_events[:,5]))
            ice_detection_power = np.c_[ice_detection_events[:, 0], ice_detection_events[:, 3] - ice_detection_events[:, 5]]
            ice_detection_prod = self.calculate_production(ice_detection_power, 1)

        # print(iced_power_drops)
        years = set([point[0].year for point in data])
        production_statistics = []
        for year in years:
            theoretical_production_sums = self.one_year_month_sums(theoretical_production,year,1)
            actual_production_sums = self.one_year_month_sums(actual_production,year,1)
            iced_power_sums = self.one_year_month_sums(iced_power_drops,year,1)
            ice_stop_sums = self.one_year_month_sums(iced_stops,year,1)
            if status_stops is not None:
                status_stop_sums = self.one_year_month_sums(status_stops_prod,year,1)
            else:
                status_stop_sums = np.copy(theoretical_production_sums)
                status_stop_sums[:, 1] = 0.0

            if ips_on is not None:
                ips_on_sums = self.one_year_month_sums(ips_on_prod,year,1)
                ice_detection_sums = self.one_year_month_sums(ice_detection_prod, year,1)
                ips_consumption_sums = self.one_year_month_sums(ips_self_consumption,year,1)
            else:
                print("Dummy IPS Values")
                ips_on_sums = np.copy(theoretical_production_sums)
                ips_on_sums[:,1] = 0.0
                ice_detection_sums = ips_on_sums
                ips_self_consumption = 0.0
            for index, stat_month in enumerate(theoretical_production_sums):
                # if theoretical_production_sums[index,0] == actual_production_sums[index,0]:
                ice_loss = iced_power_sums[index,1] + ice_stop_sums[index,1] + ips_on_sums[index,1] + ice_detection_sums[index,1]
                if theoretical_production_sums[index,1] == 0.0:
                    reldiff = 0.0
                    total_icediff = 0.0
                    icediff = 0.0
                    stopdiff = 0.0
                    statusdiff = 0.0
                    ipsdiff = 0.0
                    iddiff = 0.0
                else:
                    reldiff = (theoretical_production_sums[index, 1] - actual_production_sums[index,1])/theoretical_production_sums[index, 1]
                    icediff = (theoretical_production_sums[index, 1] - iced_power_sums[index,1])/theoretical_production_sums[index, 1]
                    stopdiff = (theoretical_production_sums[index, 1] - ice_stop_sums[index,1])/theoretical_production_sums[index, 1]
                    statusdiff = (theoretical_production_sums[index, 1] - status_stop_sums[index,1])/theoretical_production_sums[index, 1]
                    ipsdiff = (theoretical_production_sums[index, 1] - ips_on_sums[index,1])/theoretical_production_sums[index, 1]
                    iddiff = (theoretical_production_sums[index, 1] - ice_detection_sums[index,1])/theoretical_production_sums[index, 1]
                    total_icediff = (theoretical_production_sums[index, 1] - ice_loss)/theoretical_production_sums[index, 1]
                production_statistics.append(
                    [theoretical_production_sums[index, 0], theoretical_production_sums[index, 1],
                     actual_production_sums[index, 1],
                     theoretical_production_sums[index, 1] - actual_production_sums[index, 1], reldiff,
                     iced_power_sums[index, 1], icediff, ice_stop_sums[index, 1], stopdiff, status_stop_sums[index, 1],
                     statusdiff, ips_on_sums[index,1], ipsdiff, ice_detection_sums[index, 1], iddiff,ice_loss, total_icediff, ips_consumption_sums[index,1]])
        return np.array(production_statistics)

