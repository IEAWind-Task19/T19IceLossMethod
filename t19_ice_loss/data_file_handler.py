import matplotlib.pyplot as plt
import matplotlib
import datetime
import csv
import numpy as np
import json
import configparser



class CSVimporter:
    """
    sets up an importer that reads in a set of data from a predefined .csv file

    """
    def __init__(self,inputfilename = ''):
        """
        Initialize the input reader
        assumes that data is in a text file where the leftmost field is a timestamp

        There are some class parameters that need to be set:

        delim : set the delimiter character between columns
        quote_char : charcter used to indicate a text field " by default
                    if no quote character is used set this to None (note spelling)
        dt_format: formatting of the date, follows the convention of Python standard datetime formatting
                    see https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior

        also initialises headders and data structures to empty ones

        :param inputfilename: relative path of the datafile
        :return:
        """
        self.id = '' # data id used to id the data
        self.filename = inputfilename # path of the file
        self.delim = ','
        self.quote_char = None # if no quotechar is used set this to None
        self.dt_format = '%Y-%m-%d %H:%M:%S' # follows the standard python datetime formatting
        self.dt_extra_char = 0 # extra characters i.e. timezone identifier etc. at the end of timestamp
        self.headers = []
        self.full_data = []
        self.replace_faults = False # Data processing chokes on non-numeric values so textual fault codes need to be replaced
        self.fault_columns = []
        self.fault_dict = {}
        self.result_dir = '.'
        self.timestamp_index = 0
        self.summaryfile_write = True
        self.pc_plot_picture = True
        self.alarm_time_series_file_write = False
        self.filtered_raw_data_write = False
        self.icing_events_write = False
        self.power_curve_write = True

    def read_file_options_from_file(self,config_filename):
        """
        set file options from a config file see the documentation for full listing of options

        :param config_filename: name and full path of the config file

        
        """
        config = configparser.ConfigParser()
        config.read(config_filename)
        try:
            self.id = config.get('Source file','id')
            self.filename = config.get('Source file','filename')
            delimiter = config.get('Source file','delimiter', fallback=',')
            if delimiter == 'TAB':
                self.delim = '\t'
            else:
                self.delim = delimiter
            quot_char = config.get('Source file','quotechar', fallback=None)
            if (quot_char is None) or (quot_char.upper() == 'NONE'):
                self.quote_char = None
            else:
                self.quote_char = quot_char
            self.dt_format = config.get('Source file','datetime format',raw = True, fallback='%Y-%m-%d %H:%M:%S')
            self.dt_extra_char = int(config.get('Source file','datetime extra char', fallback=0))
            fault_column_string = config.get('Source file','fault columns')
            self.fault_columns = [int(column_index) for column_index in fault_column_string.split(',')]
            self.replace_faults = config.getboolean('Source file','replace fault codes',fallback=False)
            skip_column_string = config.get('Source file','Skip columns')
            if skip_column_string == "NONE":
                self.skip_columns = []
            else:
                self.skip_columns = [int(column_index) for column_index in skip_column_string.split(',')]
            self.result_dir = config.get('Output','result directory',fallback='.')
            self.summaryfile_write = config.getboolean('Output', 'summary', fallback=True)
            self.pc_plot_picture = config.getboolean('Output', 'plot', fallback=True)
            self.alarm_time_series_file_write = config.getboolean('Output', 'alarm time series', fallback=False)
            self.filtered_raw_data_write = config.getboolean('Output', 'filtered raw data', fallback=False)
            self.icing_events_write = config.getboolean('Output', 'icing events', fallback=False)
            self.power_curve_write = config.getboolean('Output', 'power curve', fallback=True)
            self.timestamp_index = int(config.get('Data Structure','timestamp index'))
        except configparser.NoOptionError as missing_value:
            print("missing config option: {0} in {1}".format(missing_value, config_filename))
        except ValueError as wrong_value:
            print("Wrong type of value in {0}: {1}".format(config_filename, wrong_value))

        

    def create_new_faultcodes(self, column_num, write_to_file = False, outfilename = ''):
        """
        Generate replacement faultcodes from the data in case faultcodes are in some kind of alphanumeric format i.e. not numbers
        
        column num is the column that contains all the fault codes.
        
        :param column_num: column index that contains the fault codes
        :param write_to_file: if True, resutls written to disk into file specified by _outfilename_
        :param outfilename: name of the output file
        :return: fault_dict a python dictionary containig all discovered fault codes (dictionary keys) and numbers to replace them with (dictionary values)
        
        """
        inputfile = open(self.filename,'r')
        file_reader = csv.reader(inputfile,delimiter = self.delim, quotechar = self.quote_char)
        textdata = []
        headers = next(file_reader)
        columns = len(headers)
        fault_codes = []
        while True:
            try:
                # data_row = (list(map(str.strip,next(file_reader))))
                data_row = next(file_reader)
                if data_row[column_num] not in fault_codes:
                    fault_codes.append(data_row[column_num].strip())
            except StopIteration:
                break
        inputfile.close()
        # rows=len(textdata)
        # ndata = np.array(textdata)
        # print(ndata[1])
        # fault_codes = np.unique(ndata[:,column_num])
        fault_dict = {}
        for index,code in enumerate(fault_codes):
            fault_dict[code] = index
        if write_to_file:
            self.write_fault_dict(outfilename, fault_dict)
        return fault_dict
        
    def read_fault_codes(self,infilename):
        """
        read fault codes from a previously generated .json file
        
        :param infilename: name of the input file
        :return: fault_dict a python dictionary containig all discovered fault codes (dictionary keys) and numbers to replace them with (dictionary values)
        
        """
        infile = open(infilename,'r')
        fault_dict = json.load(infile)
        infile.close() 
        return fault_dict
    
    def write_fault_dict(self,outfilename,fault_dict):
        """
        writes a fault dictionary on disk as a .json file
        
        :param outfilename: name of the output filename
        :param fault_dict: fault code dictionary
        
        """
        outfile = open(outfilename,'w')
        json.dump(fault_dict, outfile, indent=4, sort_keys= True)
        outfile.close()

        
    def update_fault_codes(self, column_num, infilename, write_to_file=False, outfilename=''):
        """
        updates an already saved list of fault codes from the inputfile
        
        :param column_num: column index of the fault variable
        :param infilename: name of the input file
        :param write_to file: toggles writing the updated fault dictionary to a file
        :param outfilename: nae of the output file
        :return: the updated fault dictionary
        
        """
        fault_dict = self.read_fault_codes(infilename)
        new_codes = self.create_new_faultcodes(column_num, write_to_file,outfilename)
        next_code = max(fault_dict.values()) + 1
        for item in new_codes:
            if item not in fault_dict.keys():
                fault_dict[item] = next_code
                next_code += 1
        if write_to_file:
            self.write_fault_dict(outfilename, fault_dict)
        return fault_dict
        

    def is_float(self,char_string):
        """
        checks whether or not a character string can be converted into a float
        
        :param char_string:
        :return: status of conversion
        
        """
        try:
            float(char_string)
            return True
        except ValueError:
            return False


    def create_faultfile(self):
        """
        Creates a filename for the fault file based on the name of the input file

        :return: filename of the fault dictionary

        """
        faultfilename = self.result_dir + self.id + '_faults.json'
        return faultfilename

    def process_fault_codes(self):
        """
        create a data structure that can be used to replace textual fault codes in the data that is read in for processing
        TODO: Currently, only acceptable values are those that are found in the file itself. This should be changed
                to allow seeding of the values that are set in the .ini file. You can't set a value for this
                that is not found in a file. i.e. if you have a fault indicator value "FAULT" and the data does not have any
                lines with that value, the code will crash.
                This can be changed ether here or at the point where fault_dict is accessed, you check if value exists,
                if not then you add it. Requires ability to manually add values to fault_dict.
        """
        fault_code_filename = self.create_faultfile()
        if len(self.fault_columns) == 1:
            self.fault_dict = self.create_new_faultcodes(self.fault_columns[0], True, fault_code_filename)
        else:
            for i,col in enumerate(self.fault_columns):
                if i == 0:
                    self.fault_dict = self.create_new_faultcodes(col, True, fault_code_filename)
                else:
                    self.fault_dict = self.update_fault_codes(col, fault_code_filename, True, fault_code_filename)


    def read_data(self):
        """
        read pre-specified .csv formatted datafile, return a numpy nparray of data in format:

        Specifications of the original file are defined as class variables.

        sets values of self.data and self.headers according to the contents of the file


        [timestamp, value, ...]
        """
        datafile = open(self.filename,'r')
        inputdata = csv.reader(datafile,delimiter = self.delim,quotechar=self.quote_char)
        # TODO:
            # currently assumes that the first row and only the first row of the file has
            # header information related to the file contents
            # needs to be fixed to be adjustable, files can contain 0..n rows of headers
        headers = next(inputdata)
        full_data = []
        line_number = 1
        dataline = []
        if self.replace_faults:
            self.process_fault_codes()
            # print(self.fault_dict)
        while True:
            try:
                dataline = next(inputdata)
                outputline = []                
                for i in range(0,len(dataline)):
                    if i in self.skip_columns:
                        outputline.append(np.nan)
                    elif i == self.timestamp_index:
                        ts_string = dataline[self.timestamp_index]
                        if self.dt_extra_char == 0:
                            ts = datetime.datetime.strptime(ts_string,self.dt_format)
                        else:
                            ts = datetime.datetime.strptime(ts_string[:-self.dt_extra_char],self.dt_format)
                        outputline.append(ts)
                    elif self.replace_faults and (i in self.fault_columns):
                        outputline.append(self.fault_dict[dataline[i].strip()])                    
                    elif self.is_float(dataline[i]):
                        outputline.append(float(dataline[i]))
                    else:
                        if self.is_float(dataline[i]):
                            outputline.append(float(dataline[i]))
                        else:
                            if 'FALSE' in dataline[i].upper():
                                outputline.append(False)
                            elif 'TRUE' in dataline[i].upper():
                                outputline.append(True)
                            else:
                                outputline.append(np.nan)
                full_data.append(outputline)
                line_number += 1
            except StopIteration:
                print("{0} : File {1} read".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),self.filename))
                break
            except csv.Error as e:
                print("{0} : Error {1} while reading file {2}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),e,self.filename))
            except ValueError as e:
                print("{0} : Error {1} while reading file {2}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),e,self.filename))
                print("Error on line: {0}".format(line_number))
                print(dataline)
        full_data_a = np.array(full_data)
        # remove duplicate timestamps
        # check for unique lines in timestamp column
        full_data_as = full_data_a[full_data_a[:,self.timestamp_index].argsort(),:]

        uts, inds,inve = np.unique(full_data_as[:, self.timestamp_index], return_index=True, return_inverse=True)
        # use only indexes of unique timestamps
        full_data_au = full_data_as[inds, :]
        # sort according to timestamp

        datafile.close()
        self.headers = headers
        self.full_data = full_data_au

class Result_file_writer():
    """
    sets up a writer to deal with results of the counter
    """
    def __init__(self):
        self.result_dir = './'
        self.summaryfile_write = True
        self.pc_plot_picture = True
        self.alarm_time_series_file_write = False
        self.filtered_raw_data_write = False
        self.icing_events_write = False
        self.power_curve_write = True


    def set_output_file_options(self, config_filename):
        """
        read the parameters set in .ini file for the Output section. These are used to select what outputs will be written and what not

        :param config_filename: Name of the config file used
        """
        config = configparser.ConfigParser()
        config.read(config_filename)
        try:
            self.result_dir = config.get('Output', 'result directory', fallback='./')
            self.summaryfile_write = config.getboolean('Output', 'summary', fallback=True)
            self.pc_plot_picture = config.getboolean('Output', 'plot', fallback=True)
            self.alarm_time_series_file_write = config.getboolean('Output', 'alarm time series', fallback=False)
            self.filtered_raw_data_write = config.getboolean('Output', 'filtered raw data', fallback=False)
            self.icing_events_write = config.getboolean('Output', 'icing events', fallback=False)
            self.power_curve_write = config.getboolean('Output', 'power curve', fallback=True)
            self.power_curve_plot_max = int(config.get('Data Structure', 'maximum wind speed', fallback='20'))
        except configparser.NoOptionError as missing_value:
            print("missing config option: {0} in {1}".format(missing_value, config_filename))
        except ValueError as wrong_value:
            print("Wrong type of value in {0}: {1}".format(config_filename, wrong_value))
    
    def write_alarm_file(self, result_filepath, array):
        """
        writes the alarm timeseries in a file in working directory
                
        :param result_filepath: full filename 
        :param array: data array
        :return: status of write operation, possible error message
        
        """
        fields = ['timestamp', 'alarm status', 'wind speed [m/s]', 'reference power [kW]', 'temperature [C]', 'power [kW]', 'P10 limit [kW]']
        try:
            with open(result_filepath, 'w', newline='') as result_file:
                writer = csv.writer(result_file, delimiter=';')
                writer.writerow(fields)
                writer.writerows(array)
            return True ,''
        except IOError as e:
            return False, e
    
    
    def write_time_series_file(self, result_filepath, array, headers,aepc,pc):
        """
        writes a data timeseries in a file in working directory
        
        :param result_filepath:          
        :param array:
        :param headers:
        :return: status of the writing, possible error        
        
        """        
        reference_power = aepc.theoretical_output_power(array,pc)
        out_array = []
        for i,line in enumerate(array):
            out_array.append(np.hstack((line, reference_power[i,1], reference_power[i,3], reference_power[i,4])))
        headers.append('Reference Power')
        headers.append('P10 Limit')
        headers.append('P90 Limit')
        out_array = np.array(out_array)
        try:
            with open(result_filepath, 'w', newline='') as result_file:
                writer = csv.writer(result_file, delimiter=';')
                writer.writerow(headers)
                writer.writerows(out_array)
            return True,''
        except IOError as e:
            return False, e
    
    
    def write_alarm_timings(self, result_filepath, array):
        """
        writes a data timeseries in a file in working directory
        
        :param result_filepath: path of result file
        :param array: data array
        :return:  status of writing, error
        
        """
        headers = ['start', 'stop', 'loss', 'duration', 'mean power drop', 'mean_power', 'mean_reference_power',
                  'mean wind speed', 'mean temperature']
        # headers = ['Event start', 'Event stop', 'loss [kWh]', 'duration [h]']
        try:
            with open(result_filepath, 'w', newline='') as result_file:
                writer = csv.writer(result_file, delimiter=';')
                writer.writerow(headers)
                writer.writerows(array)
            return True, ''
        except IOError as e:
            return False, e
        
    
    def summary_statistics(self, aepc, data, reference_data, pc, alarm_timings, stop_timings, over_timings, status_timings, ice_timings, ips_timings, data_sizes):
        """
        Calculate summary statistics for the dataset. contains:
            availability
            data loss due to filtering
            size of the reference dataset
            hour counts for different ice classes
            production losses due to different causes
            Theoretical maximum production
            observed production
            losses due to all reasons
            Written to a file
    
        :param aepc: the active aeoc object
        :param data: data used to calculate statistics
        :param reference_data: the reference dataset used to calculate power curve
        :param pc: power curve structure
        :param alarm_timings: reduced power incidents
        :param stop_timings: icing induced stops
        :param over_timings: overproduction incidents
        :param data_sizes: sizes after each filtering step
        :return: status of the write operation, full filename ,possible error
        
        """
        if aepc.starttimestamp == datetime.datetime.min:
            start_time = data[0,aepc.ts_index]
        else:
            start_time = aepc.starttimestamp
        if aepc.stoptimestamp == datetime.datetime.max:
            stop_time = data[-1,aepc.ts_index]
        else:
            stop_time = aepc.stoptimestamp
        data_period = (stop_time-start_time).total_seconds()/60.0/60.0
        reference_start = reference_data[0,aepc.ts_index]
        reference_stop = reference_data[-1,aepc.ts_index]
        reference_data_period = (reference_stop-reference_start).total_seconds()/60.0/60.0
        step_size = data[1, aepc.ts_index] - data[0, aepc.ts_index]
        #check for empty array (no stops)
        if np.shape(stop_timings) == (0,):
            stop_losses = 0.0
            stop_duration = 0.0
        else:
            stop_losses  = np.nansum(stop_timings[:, 2])
            stop_duration = np.nansum(stop_timings[:, 3])        
        # check for empty
        if np.shape(alarm_timings) == (0,):
            icing_loss_production = 0.0
            icing_duration = 0.0
        else:
            icing_loss_production = np.nansum(alarm_timings[:, 2])
            icing_duration = np.nansum(alarm_timings[:, 3])        
        # check for empty
        if np.shape(over_timings) == (0,):
            over_prod_duration = 0.0
        else:
            over_prod_duration = np.nansum(over_timings[:, 3])        
        # check for empty
        if (np.shape(status_timings) == (0,)) or (status_timings is None):
            status_stop_duration = 0.0
            status_stop_loss = 0.0
        else:
            status_stop_loss = np.nansum(status_timings[:, 2])
            status_stop_duration = np.nansum(status_timings[:, 3])
        if (np.shape(ice_timings) == (0,)) or (ice_timings is None):
            ice_detection_duration = 0.0
            ice_detection_loss = 0.0
        else:
            ice_detection_loss = np.nansum(ice_timings[:, 2])
            ice_detection_duration = np.nansum(ice_timings[:, 3])
        if (np.shape(ips_timings) == (0,)) or (ips_timings is None):
            ips_on_duration = 0.0
            ips_on_production_loss = 0.0
            ips_self_consumption = 0.0
        else:
            ips_on_production_loss = np.nansum(ips_timings[:,2])
            ips_on_duration = np.nansum(ips_timings[:,3])
            ips_self_consumption = np.nansum(ips_timings[:,4])

        uncertainty = aepc.power_curve_uncertainty_average(pc)
        
        tmax_power = aepc.theoretical_output_power(data, pc)
        if np.shape(tmax_power) == (0,):
            theoretical_production_sum = 0.0
            actual_production_sum = 0.0
            min_production_sum = 0.0
            max_production_sum = 0.0
            total_losses = 0.0
            energy_based_avail = 0.0
            icing_loss_perc = 0.0
            stop_loss_perc = 0.0
            icing_duration_perc = 0.0
            stop_duration_perc = 0.0
            over_prod_duration_perc = 0.0
            technical_availability = 0.0
            status_stop_loss_perc = 0.0
            ice_detection_duration_perc = 0.0
            ice_detection_loss_perc = 0.0
            ips_on_duration_perc = 0.0
            ips_on_loss_perc = 0.0
        else:
            theoretical_production = aepc.calculate_production(tmax_power, 1)
            actual_production = aepc.calculate_production(tmax_power, 2)
            production_p10 = aepc.calculate_production(tmax_power, 3)
            production_p90 = aepc.calculate_production(tmax_power, 4)
            min_production = aepc.calculate_production(tmax_power, 5)
            max_production = aepc.calculate_production(tmax_power, 6)
            theoretical_production_sum = np.nansum(theoretical_production[:, 1])
            actual_production_sum = np.nansum(actual_production[:, 1])
            min_production_sum = np.nansum(min_production[:, 1])
            max_production_sum = np.nansum(max_production[:, 1])
            production_sum_p10 = np.nansum(production_p10[:, 1])
            production_sum_p90 = np.nansum(production_p90[:, 1])
            production_upper_limit = max_production_sum / theoretical_production_sum * 100.0
            production_lower_limit = min_production_sum / theoretical_production_sum * 100.0
            production_p10_limit = production_sum_p10 / theoretical_production_sum * 100.0
            production_p90_limit = production_sum_p90 / theoretical_production_sum * 100.0
            total_losses = theoretical_production_sum - actual_production_sum
            energy_based_avail = 100.0 - ((total_losses/theoretical_production_sum) * 100.0)
            icing_loss_perc = (icing_loss_production/actual_production_sum) * 100.0
            stop_loss_perc = (stop_losses/actual_production_sum) * 100.0
            status_stop_loss_perc = (status_stop_loss/actual_production_sum) * 100.0
            icing_duration_perc = (icing_duration / data_period) * 100.0
            stop_duration_perc = (stop_duration / data_period) * 100.0
            over_prod_duration_perc = (over_prod_duration / data_period) * 100.0
            technical_availability = ((data_period - status_stop_duration) / data_period) * 100.0
            ice_detection_duration_perc = (ice_detection_duration / data_period) * 100.0
            ice_detection_loss_perc = (ice_detection_loss / actual_production_sum) * 100.0
            ips_on_duration_perc = (ips_on_duration / data_period) * 100.0
            ips_on_loss_perc = (ips_on_production_loss / actual_production_sum) * 100.0
            ips_self_consumption_perc = (ips_self_consumption / actual_production_sum) * 100.0
        # availability = aepc.count_availability(data) * 100.0
        availability = data_sizes[0] / ((stop_time - start_time) / step_size) * 100.0
    
        filtered_data_size = (data_sizes[1]/data_sizes[0]) * 100.0
        reference_data_size = (data_sizes[2]/data_sizes[0]) * 100.0
    
        filename_trunk = '_summary.txt'
        full_filename = aepc.result_dir + aepc.id + filename_trunk
        try:
            with open(full_filename,'w') as f:
                # f.write("Statistics from the dataset: {} \n".format(aepc.id))
                # f.write("\n")
                # f.write("[Generic statistics] \n")
                # f.write("Data start: {0}, stop {1}; total: {2:.1f} hours \n"
                        # .format(start_time.strftime("%Y-%m-%d %H:%M:%S"),stop_time.strftime("%Y-%m-%d %H:%M:%S"),data_period))
                # f.write("Data availability: {:.1f} % \n".format(availability))
                # f.write("Sample count in original data: {0}, after filtering: {1}, loss due to filtering: {2:.1f} % \n"
                        # .format(data_sizes[0],data_sizes[1], data_loss))
                # f.write("Sample count in reference data {0}, size of raw data {1:.1f} \n"
                        # .format(data_sizes[2],reference_loss))
                # f.write("\n")
                # f.write("[Production] \n")
                # f.write("Theoretical maximum production: {0:.1f}, observed power production: {1:.1f} \n"
                        # .format(theoretical_production_sum, actual_production_sum))
                # f.write("Total losses {0:.1f}, {1:.1f} % \n".format(total_losses, total_losses_perc))
                # f.write("\n")
                # f.write("[Icing] \n")
                # f.write("Icing during production: {0:.1f} hours, {1:.1f} % of total data \n"
                        # .format(icing_duration,icing_duration_perc))
                # f.write("Icing induced stops: {0:.1f} hours, {1:.1f} % of total data \n"
                        # .format(stop_duration,stop_duration_perc))
                # f.write("Overproduction: {0:.1f} hours, {1:.1f} % of total data \n"
                        # .format(over_prod_duration,over_prod_duration_perc))
                # f.write("Production losses due to icing: {0:.1f}, {1:.1f} % \n"
                        # .format(icing_loss_production, icing_loss_perc))
                # f.write("Production losses during icing induced stops: {0:.1f}, {1:.1f} % \n"
                             # .format(stop_losses, stop_loss_perc))
                f.write("{heading: <{fill1}}\t {value: >{fill2}} \t{unit}\n".format(heading='Field',fill1=50,value='Value', fill2=20, unit='unit'))
                f.write("{heading: <{fill1}}\t {value: >{fill2}} \t{unit}\n".format(heading='Dataset name',fill1=50,value=aepc.id, fill2=20, unit=' '))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Production losses due to icing',fill1=50, value=icing_loss_production, fill2=20, unit='kWh'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Relative production losses due to icing',fill1=50, value=icing_loss_perc, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Losses due to icing related stops',fill1=50, value=stop_losses, fill2=20, unit='kWh'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Relative losses due to icing related stops',fill1=50, value=stop_loss_perc, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Icing during production',fill1=50, value=icing_duration, fill2=20, unit='h'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Icing during production (% of total data)',fill1=50, value=icing_duration_perc, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Turbine stopped during production',fill1=50, value=stop_duration, fill2=20, unit='h'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Turbine stopped production (% of total data)',fill1=50, value=stop_duration_perc, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Over production hours',fill1=50, value=over_prod_duration, fill2=20, unit='h'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Over production hours (% of total)',fill1=50, value=over_prod_duration_perc, fill2=20, unit='%'))
                if aepc.heated_site:
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='IPS on hours', fill1=50, value=ips_on_duration,fill2=20, unit='h'))
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='IPS on hours (% of total)', fill1=50, value=ips_on_duration_perc, fill2=20,unit='%'))
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Losses during IPS operation', fill1=50, value=ips_on_production_loss,fill2=20, unit='kWh'))
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Relative losses during IPS operation', fill1=50, value=ips_on_loss_perc, fill2=20,unit='%'))
                if aepc.ice_detection:
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Ice detector icing hours',fill1=50, value=ice_detection_duration, fill2=20, unit='h'))
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Ice detector icing hours (% of total data)',fill1=50, value=ice_detection_duration_perc, fill2=20, unit='%'))
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Losses during ice detector alarms',fill1=50, value=ice_detection_loss, fill2=20, unit='h'))
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Relative losses during ice detector alarm (% of total data)',fill1=50, value=ice_detection_loss_perc, fill2=20, unit='h'))
                if aepc.heating_power_index >= 0:
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='IPS self consumption',fill1=50, value=ips_self_consumption, fill2=20, unit='kWh'))
                    f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='IPS self consumption (% of total)',fill1=50, value=ips_self_consumption_perc, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='SCADA forced stops',fill1=50, value=status_stop_duration, fill2=20, unit='h'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Time Based Availability (TBA)',fill1=50, value=technical_availability, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Loss during SCADA stops',fill1=50, value=status_stop_loss, fill2=20, unit='kWh'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Relative losses during SCADA stops (% of total)',fill1=50, value=status_stop_loss_perc, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Power curve uncertainty',fill1=50, value=uncertainty, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Production upper limit (std.dev)',fill1=50, value=production_upper_limit, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Production lower limit (std.dev)',fill1=50, value=production_lower_limit, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Production P90', fill1=50, value=production_p90_limit, fill2=20,unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Production P10', fill1=50, value=production_p10_limit, fill2=20,unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Theoretical mean production', fill1=50, value=theoretical_production_sum,fill2=20, unit='kWh'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Observed power production',fill1=50, value=actual_production_sum, fill2=20, unit='kWh'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Total Losses',fill1=50, value=total_losses, fill2=20, unit='kWh'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Energy Based Availability (EBA)',fill1=50, value=energy_based_avail, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}} \t{unit}\n".format(heading='Data start time',fill1=50, value=start_time.strftime("%Y-%m-%d %H:%M:%S"), fill2=20, unit=' '))
                f.write("{heading: <{fill1}}\t {value:>{fill2}} \t{unit}\n".format(heading='Data stop time',fill1=50, value=stop_time.strftime("%Y-%m-%d %H:%M:%S"), fill2=20, unit=' '))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Total amount of data',fill1=50, value=data_period, fill2=20, unit='h'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}} \t{unit}\n".format(heading='Reference data start time',fill1=50, value=reference_start.strftime("%Y-%m-%d %H:%M:%S"), fill2=20, unit=' '))
                f.write("{heading: <{fill1}}\t {value:>{fill2}} \t{unit}\n".format(heading='Reference data stop time',fill1=50, value=reference_stop.strftime("%Y-%m-%d %H:%M:%S"), fill2=20, unit=' '))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Total amount of data in reference dataset',fill1=50, value=reference_data_period, fill2=20, unit='h'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Data availability',fill1=50, value=availability, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}d} \t{unit}\n".format(heading='Sample count in original data',fill1=50, value=data_sizes[0], fill2=20, unit=' '))
                f.write("{heading: <{fill1}}\t {value:>{fill2}d} \t{unit}\n".format(heading='Sample count in after filtering',fill1=50, value=data_sizes[1], fill2=20, unit=' '))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Data size after filtering',fill1=50, value=filtered_data_size, fill2=20, unit='%'))
                f.write("{heading: <{fill1}}\t {value:>{fill2}d} \t{unit}\n".format(heading='Sample count in reference data',fill1=50, value=data_sizes[2], fill2=20, unit=' '))
                f.write("{heading: <{fill1}}\t {value:>{fill2}.1f} \t{unit}\n".format(heading='Reference dataset as % of original data',fill1=50, value=reference_data_size, fill2=20, unit='%'))
                f.write(" \t \t \n")
                f.write(" \t \t \n")
                
                
                
            return True, full_filename , ''
        except IOError as e:
            return False, full_filename, e
    
    
    
    def write_power_curve(self, aepc, pc, pc_id=''):
        """
        Write power curve, P10 and P90 into a file
    
        :param aepc: AEPCounter used to calculate the power curve
        :param pc: the actual power curve
        :return: status of the write operation, filename of the power curve file, possible error
        
        """
        powercurve = aepc.prettyprint_power_curves(pc, index=2)
        p10 = aepc.prettyprint_power_curves(pc, index=3)
        p90 = aepc.prettyprint_power_curves(pc, index=4)
        std_dev = aepc.prettyprint_power_curves(pc, index=5)
        uncertainty = aepc.prettyprint_power_curves(pc, index=6)
        bin_size = aepc.prettyprint_power_curves(pc, index=7)
        lower_lim = aepc.prettyprint_power_curves(pc, index=8)
        upper_lim = aepc.prettyprint_power_curves(pc, index=9)
        filename_trunk = '_powercurve.txt'
        filename = aepc.result_dir + aepc.id + pc_id + filename_trunk
        try:
            with open(filename,'w') as f:
                f.write('{name} Power Curve\n'.format(name=aepc.id))
                f.writelines(powercurve)
                f.write("\n")
                f.write('{name} P10 \n'.format(name=aepc.id))
                f.writelines(p10)
                f.write("\n")
                f.write('{name} P90 \n'.format(name=aepc.id))
                f.writelines(p90)
                f.write("\n")
                f.write('{name} Std.dev. \n'.format(name=aepc.id))
                f.writelines(std_dev)
                f.write("\n")
                f.write('{name} Uncertainty [%] \n'.format(name=aepc.id))
                f.writelines(uncertainty)
                f.write("\n")
                f.write('{name} Lower limit \n'.format(name=aepc.id))
                f.writelines(lower_lim)
                f.write("\n")
                f.write('{name} Upper limit \n'.format(name=aepc.id))
                f.writelines(upper_lim)
                f.write("\n")
                f.write('{name} Bin Size [n] \n'.format(name=aepc.id))
                f.writelines(bin_size)
                f.write("\n")
            return True, filename, ''
        except IOError as e:
            return False, filename, e
    
    def write_monthly_stats(self, data, pc, aepc, ice_events, ice_stops, status_stops, ips_on_flags, ice_detected):
        """
        write production loss statistics to file
        
        :param data: input data
        :param pc: calculated power curve
        :param aepc: aep counter used to calculate the stats
        :return: status of the write operation, filename, error
        """
        production_statistics = aepc.calculate_production_stats(data, pc,ice_events, ice_stops, status_stops, ips_on_flags, ice_detected)
        filename_trunk = '_production_stats.txt'
        filename = aepc.result_dir + aepc.id + filename_trunk
        headers = ['month', 'Theoretical production', 'Actual production', 'Total losses', 'Total losses (%)',
                   'Production losses due to icing', 'Relative icing production loss',
                   'Losses due to icing induced stops', 'Relative losses due to iced stops',
                   'Losses during SCADA stops', 'Relative losses during SCADA stops',
                   'Losses during IPS operation', 'Relative losses during IPS operation',
                   'Losses during ice detection', 'Relative losses during ice detection',
                   'Total icing losses', 'Relative icing losses', 'IPS consumption']
        try:
            with open(filename,'w') as f:
                for item in headers:
                    f.write(item)
                    f.write('\t')
                f.write('\n')
                for line in production_statistics:
                    for item in line:
                        if type(item) == datetime.datetime:
                            f.write(item.strftime('%Y-%m'))
                            f.write('\t')
                        else:
                            f.write(str(item))
                            f.write('\t')
                    f.write('\n')
            return True, filename, ''
        except IOError as e:
            return False, filename, e
        
        
    
    def insert_fault_codes(self, data,aepc,reader):
        """
        re-insert the textual fault codes into the data time series table
        
        :param data: input data
        :param aepc: aep counter object used
        :param reader: active CSVReader object
        :return: the filtered data as numpy.ndarray
        
        """
        for k,line in enumerate(data):
            for i,item in enumerate(line):
                if i in reader.fault_columns:
                    for code,val in reader.fault_dict.items():
                        if val == item:
                            data[k,i] = code
        return data
    
    def generate_standard_plots(self, data, pc, aepc, red_power, overprod, stops, data_sizes, alarm_timings, over_timings, stop_timings, ips_on_flags, write=False):
        """
        create two predefined plots from the time series data
        
        :param data: input data
        :param pc: power curve structure
        :param aepc: active AEP Counter object
        :param red_power: timeseries of reduced power
        :param overprod: timeseries of overproduction
        :param stops: timeseries of stops
        :param data_sizes: lengths of differently filtered datasets
        :param alarm_timings: statistics of reduced power incidents
        :param over_timings: statistics for over production
        :param stop timigns: statistics of icing induced stop events
        :param ips_on_flags: IPS stops, only valid for heated systems, will be None if not heated
        :param write: if True, write to disk, otherwise run matplotlib.pyplot.show()
         
        """
        # # calculate mean power curve (mean of power curves from different directions), useful for plotting
        mpc = aepc.mean_power_curve(pc)
        if aepc.starttimestamp == datetime.datetime.min:
            start_time = data[0,aepc.ts_index]
        else:
            start_time = aepc.starttimestamp
        if aepc.stoptimestamp == datetime.datetime.max:
            stop_time = data[-1,aepc.ts_index]
        else:
            stop_time = aepc.stoptimestamp
        data_period = (stop_time-start_time).total_seconds()/60.0/60.0
        reference_start = data[0,aepc.ts_index]
        reference_stop = data[-1,aepc.ts_index]
        reference_data_period = (reference_stop-reference_start).total_seconds()/60.0/60.0
        tmax_power = aepc.theoretical_output_power(data, pc)
        theoretical_production = aepc.calculate_production(tmax_power, 1)
        actual_production = aepc.calculate_production(tmax_power, 2)
        theoretical_production_sum = np.nansum(theoretical_production[:, 1])
        actual_production_sum = np.nansum(actual_production[:, 1])
        total_losses = theoretical_production_sum - actual_production_sum
        total_losses_perc = ((theoretical_production_sum - actual_production_sum)/theoretical_production_sum) * 100.0
        # check for empty
        if np.shape(alarm_timings) == (0,):
            icing_loss_production = 0.0
            icing_duration = 0.0
        else:
            icing_loss_production = np.nansum(alarm_timings[:, 2])
            icing_duration = np.nansum(alarm_timings[:, 3])
        icing_loss_perc = (icing_loss_production/actual_production_sum) * 100.0
        #check for empty array (no stops)
        if np.shape(stop_timings) == (0,):
            stop_losses = 0.0
            stop_duration = 0.0
        else:
            stop_losses  = np.nansum(stop_timings[:, 2])
            stop_duration = np.nansum(stop_timings[:, 3])
        stop_loss_perc = (stop_losses/actual_production_sum) * 100.0
        icing_duration_perc = (icing_duration / data_period) * 100.0
        stop_duration_perc = (stop_duration / data_period) * 100.0
        # check for empty
        if np.shape(over_timings) == (0,):
            over_prod_duration = 0.0
        else:
            over_prod_duration = np.nansum(over_timings[:, 3])
        over_prod_duration_perc = (over_prod_duration / data_period) * 100.0
        availability = aepc.count_availability(data) * 100.0
        
        data_loss = ((data_sizes[0]-data_sizes[1])/data_sizes[0]) * 100.0
        reference_loss = ((data_sizes[0]-data_sizes[2])/data_sizes[0]) * 100.0
        # few exmaple plots
        
        ## scatterplot the data overlay the power curve
        # plot wind speed on x-axis and power on y-axis
        production_loss_label = "Lost production due to icing: {0:.1f} %".format(icing_loss_perc)
        stop_label = "Stops due to icing: {0:.1f} %".format(stop_loss_perc)
        overprod_label = "Overproduction: {0:.1f} % of total time".format(over_prod_duration_perc)

        matplotlib.rcParams.update({'font.size': 22})
        # plt.style.use('bmh')
        fig0 = plt.figure(0)
        ax = fig0.gca()
        ax.plot(red_power[:, 2], red_power[:, 5], 'bo',label='standard production', alpha=0.5, markersize=6)
        # mark all cases where an alarm has been triggered with a red 'x'
        ax.plot(red_power[red_power[:,1] == 1.0, 2], red_power[red_power[:,1] == 1.0, 5], 'ro', label=production_loss_label, alpha=0.5, markersize=6)
        ax.plot(stops[stops[:,1] == 2.0, 2], stops[stops[:,1] == 2.0, 5], 'ko', label=stop_label, alpha=0.5, markersize=6)
        ax.plot(overprod[overprod[:,1] == 3.0, 2], overprod[overprod[:,1] == 3.0, 5], 'go', label=overprod_label, alpha=0.5, markersize=6)
        if ips_on_flags is not None:
            ips_label = "IPS ON"
            ax.plot(ips_on_flags[ips_on_flags[:, 1] != 0.0, 2], ips_on_flags[ips_on_flags[:, 1] != 0.0, 5], 'yo', label=ips_label, alpha=0.5, markersize=6)

        # plot a mean power curve and the P10 curve on top of the data
        ax.plot(mpc[:,0], mpc[:,2], 'c-', lw=4, label='Power curve') # linewidth 2
        ax.plot(mpc[:,0], mpc[:,3], 'c--', lw=4, label='P10')
        ax.plot(mpc[:,0], mpc[:,4], 'c-.', lw=4, label='P90')
        ax.set_title('Dataset: {0}\n start time: {1}, stop time: {2} \n data availability: {3:.1f}'
          .format(aepc.id,start_time.strftime("%Y-%m-%d %H:%M:%S"),stop_time.strftime("%Y-%m-%d %H:%M:%S"),availability))
        ax.set_xlabel('Wind speed [m/s]')
        ax.set_ylabel('Power [kW]')
        tick_size = 2
        ax.set_xticks((list(range(0, self.power_curve_plot_max + tick_size, tick_size))))
        ax.set_xlim((0, self.power_curve_plot_max))
        ax.legend(loc='upper left', framealpha=0.3)
        #     plt.show()
        # hide yaxis to obfuscate the true power values
        # ax = plt.gca()
        ax.axes.get_yaxis().set_visible(False)
        
        # # # plot the timeseries flag the ice cases
        # fig1 = plt.figure(1)
        # plt.title('Dataset: {0}, start time: {1}, stop time: {2}, data availability: {3:.1f}'
        #   .format(aepc.id,start_time.strftime("%Y-%m-%d %H:%M:%S"),stop_time.strftime("%Y-%m-%d %H:%M:%S"),availability))
        # # # plot the original timeseries on green
        # plt.plot_date(data[:, 0], data[:, aepc.pow_index], 'g-', label='observed power')
        # # # plot the reference data on black (this could also be red_power[:,3], its pretty much the same data)
        # plt.plot_date(stops[:, 0], stops[:, 3], 'k-', label='reference data')
        # # # mark all stops with red
        # plt.plot_date(stops[stops[:, 1] == 2.0, 0], stops[stops[:, 1] == 2.0, 5], 'r.', label='stops')
        # # # mark all cases where production has gone down with blue
        # plt.plot_date(red_power[red_power[:,1] == 1.0, 0], red_power[red_power[:,1] == 1.0, 5], 'b.', label='production loss')
        # plt.legend(loc='best')



        if write:
            pc_filename = aepc.result_dir +aepc.id + '_pc.png'
            fig0.set_size_inches(18.5, 10.5)
            fig0.savefig(pc_filename, bbox_inches='tight', dpi=300)
            # ts_filename = aepc.result_dir + aepc.id + '_ts.png'
            # fig1.set_size_inches(18.5, 10.5)
            # fig1.savefig(ts_filename, bbox_inches='tight', dpi=300)
            plt.close(0)
            # plt.close(1)
            print("{0} : Power curve plots written to : {1}"
                  .format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), pc_filename))
        else:
            plt.show()
        #==============================================================================
        #          # # plot all directional power curves in one figure
        #          plt.figure(2)
        #          for i in range(len(aepc.direction_bins)):
        #              lbl = "{0}".format(aepc.direction_bins[i])
        #              plt.plot(pc[:,i,0],pc[:,i,2],'-',label=lbl)
        #              plt.plot(pc[:,i,0],pc[:,i,3],'--',label=lbl)
        #          #     plt.plot(pc[:,i,0],pc[:,i,4],'.-',label=lbl)
        #          plt.legend()
        #          plt.show()
        #==============================================================================
    
    def read_powercurve_from_file(self,filename):
        """
        read powercurve from file produced by the program
                
        Some information is lost during the save process right now. real bin centers are not saved and neither are sample counts
        TODO: Needs to be updated, writing as well. Power curve now has a lot more information.
            might make sense to change the formatting of the power curve file to something a bit more structured
        :param filename: filename where the power curve sits
        :returns: power curve structure formatted in same way as earlier
        """
        pc_file = open(filename,'r')
        line = next(pc_file) # otsikko
        line = next(pc_file) # suuntabinit
        dir_bins = [float(item.strip()) for item in line.split('\t')[1:]]
        pc = []
        p10 = []
        p90 = []
        wind_bins = []
        line = next(pc_file) # eka rivi
        while 'P10' not in line:
            try:
                wind_bins.append(float(line.split('\t')[0].strip()))
                pc.append([float(item.strip()) for item in line.split('\t')[1:]])
                line = next(pc_file)
            except ValueError:
                break
        line = next(pc_file) # otsikko
        line = next(pc_file) # suuntabinit
        while 'P90' not in line:
            try:
                p10.append([float(item.strip()) for item in line.split('\t')[1:]])
                line = next(pc_file)
            except ValueError:
                break
        line = next(pc_file) # otsikko
        line = next(pc_file) # suuntabinit
        while True:
            try:
                p90.append([float(item.strip()) for item in line.split('\t')[1:]])
                line = next(pc_file)
            except StopIteration:
                break
            except ValueError:
                break
        
        full_pc = np.zeros((len(wind_bins),len(dir_bins),6))
        for i in range(len(wind_bins)): # rivit
            for j in range(len(dir_bins)): #sarakkeet
                full_pc[i,j,0] = wind_bins[i]
                full_pc[i,j,1] = dir_bins[j]
                full_pc[i,j,2] = pc[i][j]
                full_pc[i,j,3] = p10[i][j]
                full_pc[i,j,4] = p90[i][j]
        pc_file.close()
        return full_pc



