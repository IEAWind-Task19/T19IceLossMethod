import os
from t19_ice_loss import aep_counter as aep
from t19_ice_loss import data_file_handler as dfh
import sys
import configparser
import datetime as dt
import numpy as np




def main(configfile_name):
    """
    Process the data and write the outputfiles.

    Outputfiles are named based on the dataset id.

    """
    # # # get the configfile as a command-line parameter
    #configfile_name = sys.argv[1]
    # first read the configfile in
    config = configparser.ConfigParser()
    config.read(configfile_name)
    print("{0} : Processing dataset {1}".format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), config.get('Source file', 'id')))

    # first read the data in
    reader = dfh.CSVimporter()
    # read generic settings from the ini file
    # configfile_name = 'test.ini'
    # configfile_name = 'C11.ini'


    reader.read_file_options_from_file(configfile_name)
    if not os.path.exists(reader.result_dir):
        os.makedirs(reader.result_dir)
    #reader.fault_columns = [8,9,10]
    #reader.replace_faults = True
    # set filename separately
    #reader.filename = '../data/full_mean_dataset.csv'
    #read data
    reader.read_data()
    data = reader.full_data
    headers = reader.headers

    # print(headers)
    # create a new instance of the AEP loss counter
    aepc = aep.AEPcounter()

    # TODO:
    # figure out a netter way for this.
    if reader.replace_faults:
        aepc.fault_dict = reader.fault_dict
    # read data structure from file
    aepc.set_data_options_from_file(configfile_name)
    # read binning options from file
    aepc.set_binning_options_from_file(configfile_name)
    # read filter settings from file
    aepc.set_filtering_options_from_file(configfile_name)
    # read options related to IPS, if the "Icing" section does not exist, set IPS to False
    aepc.set_ips_options_from_file(configfile_name)
    # aepc.starttimestamp = dt.datetime(2015, 1, 1, 0, 0, 0)
    # aepc.stoptimestamp = dt.datetime(2015, 10, 1, 0, 0, 0)
    # calculate air density correction based on site height using the formula from the spec
    temperature_corrected_data = aepc.air_density_correction(data)
    # temperature_corrected_data = data.copy()
    # filter the corrected data based on state variable values
    #state_filtered_data = aepc.state_filter_data(temperature_corrected_data)
    time_limited_data = aepc.time_filter_data(temperature_corrected_data)
    state_filtered_data = aepc.state_filter_data(time_limited_data)

    # filter the data based on power level,
    # remove datapoints where output power is below 0.01 * aepc.rated_power
    #power_level_filtered_data = aepc.power_level_filter(state_filtered_data, 0.01)
    power_level_filtered_data = aepc.power_level_filter(state_filtered_data)
    # create power curves. This bins the data according to wind speed and direction and does some
    # filtering and interpolation to fill over gaps on source data.

    # only use the part of data where temperature is above 3 degrees celsius for the power curve
    # use the full dataset for refernce use time limited for loss calculation
    s_reference_data = aepc.state_filter_data(temperature_corrected_data)
    d_reference_data = aepc.temperature_filter_data(s_reference_data)
    reference_data = aepc.power_level_filter(d_reference_data)
    #reference_data = aepc.diff_filter(pd_reference_data)
    pc = aepc.count_power_curves(reference_data)
    # rfw.write_power_curve_file('../results/power_curve.txt', pc, aepc)
    # save data sizes into a list in order, original, filtered, reference
    data_sizes = [len(data), len(state_filtered_data), len(reference_data)]

    # find stoppages as defined in the specification
    # find power drops and flag them
    if aepc.stop_filter_type == 0:
        stops = aepc.find_icing_related_stops(state_filtered_data, pc)
        pow_alms1 = aepc.power_alarms(power_level_filtered_data, pc)
        status_timings = None
        status_stops = None
    elif (aepc.stop_filter_type == 2) or (aepc.stop_filter_type == 1):
        status_stops = aepc.status_code_stops(time_limited_data, pc)
        stops = aepc.find_icing_related_stops(state_filtered_data, pc)
        pow_alms1 = aepc.power_alarms(power_level_filtered_data, pc)
        status_timings = aepc.power_loss_during_alarm(status_stops)
    else:
        stops = None
        status_stops = None
        status_timings = None
        pow_alms1 = aepc.power_alarms(power_level_filtered_data, pc)
    if aepc.heated_site:
        ips_on_flags = aepc.status_code_stops(time_limited_data, pc, filter_type='ips')
        ips_timings = aepc.power_loss_during_alarm(ips_on_flags, ips_alarm=True)
    else:
        ips_on_flags = None
        ips_timings = None
    if aepc.ice_detection:
        ice_detected = aepc.status_code_stops(time_limited_data, pc, filter_type='icing')
        ice_timings = aepc.power_loss_during_alarm(ice_detected)
    else:
        ice_detected = None
        ice_timings = None
    # find over production incidents and flag them
    pow_alms2 = aepc.power_alarms(power_level_filtered_data, pc, over=True)
    # find start and stop times of alarms in the structure containing the power drop flags
    alarm_timings = aepc.power_loss_during_alarm(pow_alms1)
    stop_timings = aepc.power_loss_during_alarm(stops)
    over_timings = aepc.power_loss_during_alarm(pow_alms2)

    # re-do the reference dataset
    #new_ref = aepc.increase_reference_dataset(time_limited_data, stop_timings, alarm_timings, over_timings)
    #new_pc = aepc.count_power_curves(new_ref)

    rfw = dfh.Result_file_writer()
    rfw.set_output_file_options(configfile_name)

    if rfw.summaryfile_write:
        summary_status, summary_filename, summary_error = rfw.summary_statistics(aepc, time_limited_data, reference_data, pc, alarm_timings, stop_timings, over_timings, status_timings, ice_timings, ips_timings, data_sizes)
        if summary_status:
            print("{0} : Summary written successfully into: {1}".format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary_filename))
        else:
            print("{0} : Problem writing summary: {1}".format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary_error))

    if rfw.power_curve_write:
        power_curve_status, pc_filename, pc_error = rfw.write_power_curve(aepc,pc)
        if power_curve_status:
            print('{0} : Power curve written successfully into: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), pc_filename))
        else:
            print('{0} : Problem writing power curve: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), pc_error))

    if rfw.icing_events_write:
        # TODO: write these to one file
        prod_loss_trunk = '_losses.csv'
        stops_trunk = '_stops.csv'
        status_trunk = '_status.csv'
        ips_trunk = '_ips.csv'
        icing_trunk = '_ice_det.csv'
        losses_filename = aepc.result_dir + aepc.id + prod_loss_trunk
        stops_filename = aepc.result_dir + aepc.id + stops_trunk
        status_filename = aepc.result_dir + aepc.id + status_trunk
        ips_filename = aepc.result_dir + aepc.id + ips_trunk
        icing_filename = aepc.result_dir + aepc.id + icing_trunk
        loss_status, loss_write_error = rfw.write_alarm_timings(losses_filename, alarm_timings)
        if loss_status:
            print('{0} : Icing loss statistics written successfully into: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), losses_filename))
        else:
            print('{0} : Error writing icing loss statistics: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), loss_write_error))
        stop_status, stop_write_error = rfw.write_alarm_timings(stops_filename, stop_timings)
        if stop_status:
            print('{0} : Icing stops statistics written successfully into: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), stops_filename))
        else:
            print('{0} : Error writing icing stop statistics: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), stop_write_error))
        if aepc.status_stop_index[0] > 0:
            status_status, status_write_error = rfw.write_alarm_timings(status_filename, status_timings)
            if status_status:
                print('{0} : Status Code statistics written successfully into: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), status_filename))
            else:
                print('{0} : Error writing Status Code statistics: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), status_write_error))
        if aepc.heated_site:
            ips_status, ips_write_error = rfw.write_alarm_timings(ips_filename, ips_timings)
            if ips_status:
                print('{0} : Status Code statistics written successfully into: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ips_filename))
            else:
                print('{0} : Error writing Status Code statistics: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ips_write_error))
        if aepc.ice_detection:
            icing_status, icing_write_error = rfw.write_alarm_timings(icing_filename, ice_timings)
            if icing_status:
                print('{0} : Status Code statistics written successfully into: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), icing_filename))
            else:
                print('{0} : Error writing Status Code statistics: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), icing_write_error))

        #TODO: make ice detector and IPS OPTIONAL, Now the code inserts dummy values for IPS. Not a clean solution
        monthly_stat_status, stat_filename, stat_write_error = rfw.write_monthly_stats(time_limited_data, pc, aepc, pow_alms1, stops, status_stops, ips_on_flags, ice_detected)
        if monthly_stat_status:
            print('{0} : Monthly icing loss timeseries written into: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), stat_filename))
        else:
            print('{0} : Error writing loss timeseries: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), stat_write_error))

    if rfw.alarm_time_series_file_write:
        # write out the results
        combined_ts = aepc.combine_timeseries(pow_alms1,stops,pow_alms2)
        alarm_timeseries_filename = aepc.result_dir + aepc.id + '_alarms.csv'
        ts_write_status, ts_write_error = rfw.write_alarm_file(alarm_timeseries_filename, combined_ts)
        if ts_write_status:
            print('{0} : Time series written successfully into: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), alarm_timeseries_filename))
        else:
            print('{0} : Error writing time series file: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ts_write_error))

    if rfw.filtered_raw_data_write:
        filtered_data_filename = aepc.result_dir + aepc.id + '_filtered.csv'
        new_data = rfw.insert_fault_codes(aepc.time_filter_data(temperature_corrected_data), aepc, reader)
        raw_write_status, raw_write_error = rfw.write_time_series_file(filtered_data_filename, new_data, headers,aepc,pc)
        if raw_write_status:
            print('{0} : Filtered data written succesfully to: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),filtered_data_filename))
        else:
            print('{0} : Error writeing raw data: {1}'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),raw_write_error))

    if rfw.pc_plot_picture:
        if aepc.heated_site:
            rfw.generate_standard_plots(temperature_corrected_data, pc, aepc, pow_alms1, pow_alms2, stops, data_sizes,
                                        alarm_timings, over_timings, stop_timings, ips_on_flags, True)
        else:
            rfw.generate_standard_plots(temperature_corrected_data, pc, aepc, pow_alms1, pow_alms2, stops, data_sizes,
                                        alarm_timings, over_timings, stop_timings, None, True)



if __name__ == '__main__':
    main(sys.argv[1])
