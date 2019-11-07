####################################
Using the Task 19 Power Loss Counter
####################################

The project contains sample code to calculate icing induced data losses for a single wind turbine according to the specification by IEA Wind Task 19.

************
Installation 
************

Code is written in Python 3 and it uses several libraries included in the Scipy stack. 

Needed libraries are: ::
    
    numpy, scipy, matplotlib, (sphinx)

Information on installing the scipy stack can be found from `the Scipy website <http://www.scipy.org/install.html>`_

Sphinx is needed to build the documentation. It's not mandatory, the release package includes a compiled documentation.

Note that you will need python 3 versions of the libraries.

Easiest way to get everything is to use a prepackaged installer such as `Anaconda <http://www.anaconda.com>`_

Anaconda installer contains all the required Python libraries and more and is provided as one easy to use installer. It is free and open source, available for Windows/Mac OS X/Linux and is self contained i.e. can be installed side by side with an existing python installation.

.. _use:

**************
Using the code
**************

The code can be used to calculate losses and it will output several kinds of statistics about your data for later analysis.

The production loss calculator is configured by setting up a config file. (see section The .ini file). Then calling the script ``t19_counter.py`` by giving the ini file as a command line parameter as ::

    python t19_counter.py site.ini

where ``site.ini`` contains the case definition relevant for your site.

**********
Input data
**********

The code is meant to calculate losses from one time series at a time. One time series in this case means one wind turbine. For multiple turbines you need to define a separate .ini file for each wind turbine and calculate losses separately. After this you have to use other tools to combine individual turbines to each other.

.. _input-data-example:

==================
Example input data
==================

Below is an example of what input data could look like. Notice the Status and fault code columns on the right. In this case there needs to be additional filtering to replace the status and fault codes with numerical values.

=================   ===============   ========   ===============   =========   ============   =========   =============
Time stamp (0)      Temperature (1)   RPM (2)     Wind Speed (3)   Power(4)    Direction(5)   Status(6)   Fault code(7)
=================   ===============   ========   ===============   =========   ============   =========   =============
2013-02-01 17:20    -3.14             10.2       7.5988            1277.235    133            Run         OK
2013-02-01 17:30    -3.80             10.8       7.6623            1235.741    132            Run         OK
2013-02-01 17:40    -3.23             10.9       7.5914            1297.725    134            Run         OK
2013-02-01 17:50    -3.57             10.5       7.9407            1227.176    130            Run         OK
2013-02-01 18:00    -3.79             10.9       7.8154            1256.481    132            Run         OK
2013-02-01 18:10    -3.73             10.9       7.6261            1274.133    132            Run         OK
2013-02-01 18:20    -3.63             10.8       7.3955            1249.529    136            Run         OK
2013-02-01 18:30    -3.87             10.9       7.691             1232.532    137            Run         OK
2013-02-01 18:40    -3.29             10.3       7.7816            1270.953    135            Run         OK
2013-02-01 18:50    -3.52             10.6       7.9739            1299.535    135            Run         OK
2013-02-01 19:00    -3.15             10.9       7.3878            1221.514    131            Run         OK
2013-02-01 19:10    -3.34             10.9       7.8072            1256.669    131            Run         OK
2013-02-01 19:20    -3.15             10.8       7.7349            1284.479    134            Run         OK
2013-02-01 19:30    -3.08             10.3       7.8621            1288.962    135            Run         OK
2013-02-01 19:40    -3.13             10.7       7.4672            1230.259    133            Run         OK
2013-02-01 19:50    -3.48             10.9       7.509             1279.426    138            Run         OK
2013-02-01 20:00    -3.34             10.5       7.9378            1239.045    139            Run         OK
2013-02-01 20:10    -3.02             10.3       7.1774            1273.976    132            Run         OK
2013-02-01 20:20    -3.50             10.5       7.3004            1254.343    136            Run         OK
2013-02-01 20:30    -3.47             10.7       7.7331            1278.701    131            Run         OK
2013-02-01 20:40    -3.53             10.7       7.6289            1269.522    134            Run         OK
2013-02-01 20:50    -3.04             10.1       7.0893            1296.482    135            Run         OK
2013-02-01 21:00    -3.31             10.7       7.8652            1278.775    133            Run         OK
2013-02-01 21:10    -3.44             10.7       7.6277            1232.615    134            Run         OK
2013-02-01 21:20    -3.46             10.5       7.9821            1219.4      135            Run         OK
2013-02-01 21:30    -3.80             10.7       7.5614            1280.438    132            Run         OK
2013-02-01 21:40    -3.26             10.7       7.2718            1253.659    136            Run         OK
2013-02-01 21:50    -3.75             10.5       7.6549            0           137            Fault       Fault code A
2013-02-01 22:00    -3.15             10.8       7.6856            0           133            Fault       Fault code A
2013-02-01 22:10    -3.89             10.7       7.8238            0           135            Fault       Fault code A
2013-02-01 22:20    -3.80             10.4       7.1408            0           133            Fault       Fault code A
2013-02-01 22:30    -3.86             10.4       7.1721            0           133            Fault       Fault code A
2013-02-01 22:40    -3.04             10.1       7.6194            0           136            Fault       Fault code A
=================   ===============   ========   ===============   =========   ============   =========   =============



*******
Outputs
*******

There are multiple different outputs available.

============
Summary file
============

Summary file that contains some statistics about the data. A useful tool to get an overview of the data and some statistics

Contains the following information.

.. tabularcolumns:: |\Y{0.2}|\Y{0.8}|

+------------------------------------------------+---------------------------------------------------------------------+
|Value Field name                                |  Purpose                                                            |
+================================================+=====================================================================+
|Dataset name                                    |  Data set name as defined in the config file                        |
+------------------------------------------------+---------------------------------------------------------------------+
|Production losses due to icing                  |  Production losses during operation, that are classified to be      |
|                                                |  icing related, in kWh                                              |
+------------------------------------------------+---------------------------------------------------------------------+
|Relative production losses due to icing         |  Previous line's losses as % of reference                           |
+------------------------------------------------+---------------------------------------------------------------------+
|Losses due to icing related stops               |  Losses due to stops during operation that are classified to be     |
|                                                |  icing related                                                      |
+------------------------------------------------+---------------------------------------------------------------------+
|Relative losses due to icing related stops      |  Previous line's losses as % of reference                           |
+------------------------------------------------+---------------------------------------------------------------------+
|Icing during production                         |  Icing time in hours during production.                             |
|                                                |  Same definition of icing as on row 2                               |
+------------------------------------------------+---------------------------------------------------------------------+
|Icing during production (% of total data)       |  Previous line's value as % of the entire dataset                   |
+------------------------------------------------+---------------------------------------------------------------------+
|Turbine stopped during production               |  Amount of time turbine is stopped due to icing. Same definition    |
|                                                |  of stop as "icing related stops" above                             |
+------------------------------------------------+---------------------------------------------------------------------+
|Turbine stopped production (% of total data)    |  Previous line's value as % of the entire dataset                   |
+------------------------------------------------+---------------------------------------------------------------------+
|Over production hours                           |  Amount of time in hours the production is above P90 curve          |
|                                                |  and temperature is below the alarm limit                           |
+------------------------------------------------+---------------------------------------------------------------------+
|Over production hours (% of total)              |  Previous line's value as % of the entire dataset                   |
+------------------------------------------------+---------------------------------------------------------------------+
|IPS on hours                                    |  Number of hours blade heating is on.                               |
|                                                |  (Will only appear in summary if the site in question has IPS)      |
+------------------------------------------------+---------------------------------------------------------------------+
|IPS on hours (% of total)                       |  Previous line's value as % of the entire dataset                   |
+------------------------------------------------+---------------------------------------------------------------------+
|Losses during IPS operation                     |  Sum of production losses during the times IPS is operating.        |
|                                                |  The loss here is difference between reference and actual value,    |
|                                                |  IPS self consumption is not taken into account.                    |
|                                                |  (Will only appear in summary if the site in question has IPS).     |
+------------------------------------------------+---------------------------------------------------------------------+
|Relative losses during IPS operation            |  Previous line's losses as % of reference                           |
+------------------------------------------------+---------------------------------------------------------------------+
|IPS self consumption                            |  If there is an IPS power consumption value in the source data,     |
|                                                |  IPS self consumption in kWh, will show up here                     |
+------------------------------------------------+---------------------------------------------------------------------+
|IPS self consumption (% of total)               |  Previous line's losses as % of reference                           |
+------------------------------------------------+---------------------------------------------------------------------+
|SCADA forced stops                              |  Number of hours the turbine is stopped due to some reason          |
|                                                |  as indicated by the SCADA status code                              |
+------------------------------------------------+---------------------------------------------------------------------+
|Time Based Availability (TBA)                   |  Percentage of the time the turbine is operating normally           |
+------------------------------------------------+---------------------------------------------------------------------+
|Loss during SCADA stops                         |  Production loss during the times turbine is not operating in kWh   |
+------------------------------------------------+---------------------------------------------------------------------+
|Relative losses during SCADA stops (% of total) |  Previous line's losses as % of reference                           |
+------------------------------------------------+---------------------------------------------------------------------+
|Power curve uncertainty                         |  Average of power curve uncertainty                                 |
|                                                |  (calculated only for bins between 4 m/s and 15 m/s)                |
+------------------------------------------------+---------------------------------------------------------------------+
|Production upper limit (std.dev)                |  Upper limit for the production using power curve uncertainty above |
+------------------------------------------------+---------------------------------------------------------------------+
|Production lower limit (std.dev)                |  Lower limit for the production using power curve uncertainty above |
+------------------------------------------------+---------------------------------------------------------------------+
|Production P90                                  |  Production estimate using the P90 power curve                      |
+------------------------------------------------+---------------------------------------------------------------------+
|Production P10                                  |  Production estimate using the P10 power curve                      |
+------------------------------------------------+---------------------------------------------------------------------+
|Theoretical mean production                     |  Production assuming the reference power curve,                     |
|                                                |  using the wind speed measurement in file,                          |
|                                                |  not taking turbine state into account                              |
+------------------------------------------------+---------------------------------------------------------------------+
|Observed power production                       |  Total production calculated from the output power column           |
+------------------------------------------------+---------------------------------------------------------------------+
|Total Losses                                    |  Observed power - Theoretical mean power                            |
+------------------------------------------------+---------------------------------------------------------------------+
|Energy Based Availability (EBA)                 |  Observed Power / Theoretical mean power as %                       |
+------------------------------------------------+---------------------------------------------------------------------+
|Data start time                                 |  First time stamp used for analysis                                 |
+------------------------------------------------+---------------------------------------------------------------------+
|Data stop time                                  |  Last time stamp used for analysis                                  |
+------------------------------------------------+---------------------------------------------------------------------+
|Total amount of data                            |  difference between start and stop time in hours                    |
+------------------------------------------------+---------------------------------------------------------------------+
|Reference data start time                       |  First time stamp in data                                           |
+------------------------------------------------+---------------------------------------------------------------------+
|Reference data stop time                        |  Last time stamp in data                                            |
+------------------------------------------------+---------------------------------------------------------------------+
|Total amount of data in reference dataset       |  difference between start and stop time in reference data hours     |
+------------------------------------------------+---------------------------------------------------------------------+
|Data availability                               |  % of data available between first and last timestamp               |
+------------------------------------------------+---------------------------------------------------------------------+
|Sample count in original data                   |  Sample count in the dataset that is read in at first stage         |
+------------------------------------------------+---------------------------------------------------------------------+
|Sample count in after filtering                 |  Sample count after all filtering steps                             |
+------------------------------------------------+---------------------------------------------------------------------+
|Data loss due to filtering                      |  Amount of data lost during filtering                               |
+------------------------------------------------+---------------------------------------------------------------------+
|Sample count in reference data                  |  Sample count in reference data,                                    |
|                                                |  used to build the reference power curve                            |
+------------------------------------------------+---------------------------------------------------------------------+
|Reference dataset as % of original data         |  reference dataset size as % of original                            |
+------------------------------------------------+---------------------------------------------------------------------+


================
data time series
================

Prints a time series data as a .csv file that can be used for further analysis. Data is formatted as columns

    timestamp, alarm, wind speed, reference power, temperature, power, limit

Here **alarm** indicates possible icing events. Alarm codes in this data are

0. no alarm
1. icing during production. Reduced power output
2. Turbine stopped due to icing
3. Overproduction. The turbine output is above the power curve.

**reference power** is power calculated from the power curve. Limit is the P10 limit used to identify reduced power output. Timestamp, wind speed and output power are drawn from the source data.

===========
Power curve
===========

Produces one file, that contains individual power curves for each wind direction bin.

The power curve is output as a table in a text file where different wind speed bins are in each row of the table and different columns indicate different wind direction bins. The row and column headers contain the center points of all bins.

The file contains the following variables binned for wind speed and direction:

* Mean power in the bin
* P10 value of the bin
* P90 value of the bin
* Bin power standard deviation
* Power curve uncertainty in the bin
* Power curve upper and lower limits (mean power +- uncertainty)
* Sample count in the bin

====
plot
====

Creates two interactive plots that can be used to look at the data. One contains full time series of the data with icing events marked on the timeline. Other contains the power curve and a scatter plot of the full time series with icing events marked on the data.


================
icing event list
================

It is possible to output a collected summary of icing events. This is output into two separate files. One that contains a list of all cases where the power output was reduced according to the set conditions and a another one listing all the icing induced stops. both files are text .csv files that containing the fields:

     =========  ========  ========  ============
     starttime  stoptime  loss_sum  event_length
     =========  ========  ========  ============

Here ``loss_sum`` is the total losses during the event in kilowatt hours and ``event_length`` is the total length of said individual event in hours. 

====================
filtered time series
====================

Produces the raw time series that is used after initial filtering to perform all calculations. Can be used for further analysis to get a common starting point.




*************
The .ini file
*************

All configuration is done in the .ini file.

Options are denoted in the file as::

    name of option = value

File is divided into sections, section headers are enclosed in square brackets \[\].

Capitalization of sections and options is important, they need to be spelled the same way as in the example file.

Not all options are needed. Some variables have a preset default value that does not need to be set. A minimal .inifile is included with the release



********************
Config file sections
********************


The file is divided into Five logical sections that set certain parameters that will change from site to site and between runs.

Contents of each section are listed below and the purpose of all options is explained briefly.


====================
Section: Source File
====================

--
id
--

Identifier for the data set. This can be for example the name of the site or a combinations of site name and turbine identifier. **id** is used for example in naming the output files. **id** needs to be unique, if output files with the same identifier exist in the result directory the script will overwrite them.
**id** is a mandatory value.


--------
filename
--------

the source data filename and path. The source data needs to be in a ``.csv`` file. Or any other kind of text file.

---------
delimiter
---------

field delimiter in the source file. If data is tab-delimited write ``TAB`` here. Default value is ``,``.

---------
quotechar
---------

Character used to indicate text fields in the source file. If no special quote character is used write ``none``. ``none`` is also the default.

.. _datetime-format:

---------------
datetime format
---------------

Formatting of timestamps. Uses same notation as Python ``datetime`` class function. See documentation at python.org `here <https://docs.python.org/3.5/library/datetime.html#strftime-strptime-behavior>`_

Example: timestamp ``2019-09-13 16:09:10`` corresponds to format string ``%Y-%m-%d %H:%M:%S``

Defaults to ISO 8601 format ``%Y-%m-%d %H:%M:%S``


-------------------
datetime extra char
-------------------

number of extra character at the end of the timestamp. Sometimes there are some characters add to timestamps e.g. to indicate timezone. The numbers of these need to be defined even if zero. Default value is 0.

-------------
fault columns
-------------

data file columns that contain the turbine status or fault code. **Zero based** i.e. leftmost column in source file is column 0. If information about the turbine state is contained in multiple places add all of these columns here separated by commas e.g.::

    fault columns = 8,9,10

In the :ref:`input-data-example` you would put 6 and 7 here. Because both of those columns can then be used to filter the data based on status information.

This is mandatory value

-------------------
replace fault codes
-------------------

filtering option needed in case the source file contains status/fault codes that are not numbers. Non-numeric data in the data set cause issues for the analysis code, so the fault codes need to filtered first. In case the fault/status codes in the source data are text, set::

    replace fault codes = True

if the replacement is not needed set this to ``False``. In the example earlier :ref:`input-data-example`. This filtering is needed. in some cases the output fault codes are already numeric, so in those cases it can be false.

Defaults to ``False``

===============
Section: Output
===============

This section defines the output produced by the power loss counter script. 

The script allows the user to set what kind of outputs are needed. All data is output into text files in a results directory. All output files are named us the `id` identifier.

If a certain output is needed set the value of the corresponding key to ``True``

For example producing the alarm time series is relatively slow. Setting unneeded parts to ``False`` can make calculations faster. 

By default all outputs are set to ``True`` and the results are written to the local directory of the script.

----------------
result directory
----------------

directory where the results will be written to


-------
summary
-------

Prints a summary statistics file containing overall information about the original data. 

----------------
data time series
----------------

sets time series saving on or off. **NOTE** constructing the time series can take a long time depending on the size of the data set. When doing preliminary analysis, unless absolutely required, it is recommended to keep this set as False

-----------
power curve
-----------

Prints a file that contains the power curve calculated from the data.

----
plot
----

sets plotting on or off. Script makes a power curve plot with icing events highlighted. The plots are saved in to the results directory as ``.png``

----------------
icing event list
----------------

set the icing event list saving on or off

-----------------
filtered raw data
-----------------

switch the raw data saving on or off

-----------------
Alarm time series
-----------------

Print a time series file of the icing alarms. The file will be a .csv file with the following columns:

    =========  ==================  ==========  ===============  ===========  =====  =================
    Timestamp  Alarm signal value  Wind Speed  Reference Power  Temperature  Power  Power limit (P10)
    =========  ==================  ==========  ===============  ===========  =====  =================

Here ``Alarm signal value`` indicates the icing status. Values of the alarm signal are listed in the table below

==================  ==============
Alarm signal value  Interpretation
==================  ==============
0                   No alarm     
1                   Icing alarm, reduced production
2                   Icing alarm, stop during operation
3                   Overproduction
==================  ==============

=======================
Section: Data Structure
=======================

This section defines the format of the source data. Note that the leftmost column in your source data is column 0.

All of these are always required.

---------------
timestamp index
---------------

index of the timestamps in the original data.

----------------
wind speed index
----------------

index of wind speed

--------------------
wind direction index
--------------------

index of wind direction

-----------------
temperature index
-----------------

index of temperature measurements. Temperature needs to be in degrees Celsius.

-----------
power index
-----------

Index of output power measurement in source data. (Preferably in kilowatts, the units are assumed in some places when formatting output files.)

Note: if source data uses relative values of output power the ice detection methods in the scripts do still work. The overall values for lost production might not make sense, but the timing of the icing events can still be calculated.

-----------
rated power
-----------

rated power of the turbine.

-----------
state index
-----------

indexes of state values or status codes used in data filtering. These can be found in multiple columns, just put everything here separated by commas i.e.::

    state index = 8,9,10

------------
normal state
------------

The value of the state variable in so called normal state, used for filtering the data. This can be text or a number just use the same format as in the source data. Also you can specify multiple values here, just write them all on one line separated by commas.

set these in same order as the state index above. If you want to include multiple valid values for one state variable add the appropriate index into state index once for each required value.

Note: if the actual code contains a comma, the code will interpret that as two separate values and will crash.

--------------
site elevation
--------------

site elevation in meters above sea level, used for correcting the wind measurements.

------------
status index
------------

Index of the status signal. Used for collecting statistics of known stops

----------------------
status code stop value
----------------------

Value of the status code that indicates that the turbine has stopped. 

==============
Section: Icing
==============

If the turbines on the site have ice detection or some kind of ice prevention system (anti- or de-icing) the code can take this into account and produce statistics of the Ice prevention system operation.

This section is not mandatory, if there is no ice detector or no blade heating available. If ``Icing`` as a section is included, then all of these need to be defined as well.

-------------
Ice detection
-------------

Set this to ``True`` if there is an ice detection signal in the data. Leave the value to ``False`` if not. Used for collecting production statistics. This only cares about the presence of an explicit ice detection signal, sometimes a heated site might not have a visible ice detection signal in the data.

----------------
icing alarm code
----------------

Code in the data that corresponds to icing alarm.

-----------------
icing alarm index
-----------------

Zero-based index of the icing alarm code

-------
heating
-------

Set to ``True`` if site has blade heating.

---------------
ips status code
---------------

The code in the data that indicates that blade heating is on.

----------------
ips status index
----------------

Zero-based index of the ips status code

---------------
ips status type
---------------

Sets the type of the ips status code. Set to 1 if the ips status code value defined in ``ips status code`` indicates that ips is on and the blade heating is active. If this is set to 2 the code interprets all other values except the value  in ``ips status code`` as blade heating being on.

---------------------------
ips power consumption index
---------------------------

If ips power measurement exists in the data, use this to give the index of the power consumption signal (zero-based). If there is no power consumption signal in the data, set this value to -1.


================
Section: Binning
================

Sets the binning options for the power curve calculations.

This is not required.

------------------
minimum wind speed
------------------

minimum wind speed, all values below this will be sorted in the firs bin. Usually set to 0. Defaults to 0, if not set.

------------------
maximum wind speed
------------------

Maximum wind speed for the power curve, all values above this will end up in the last bin. Default value 20.

-------------------
wind speed bin size
-------------------


Wind speed bin size in meters per second. Default value 1.

-----------------------
wind direction bin size
-----------------------

Wind direction bin size in degrees.

**NOTE:** If you do not want to use wind direction based binning set the bin size to 360 degrees.

Default is set 360 i.e. no direction-based binning is used by default.

==================
Section: Filtering
==================

Data is filtered prior to analysis. The options for the filter are set in this section.

----------------
power drop limit
----------------

Lower limit for the power curve, defaults to `10` meaning using the P10 value to indicate the lower limit value used for ice detection.

--------------------
overproduction limit
--------------------

upper limit for normal operation. Used to mark overproduction in the data, defaults to `90` corresponding to top 90 percentile.

-----------------
icing time filter
-----------------

Number of continuous samples required to be under the lower limit in order to indicate an icing event has started.

Note: this is number of samples, so for ten-minute data use 3 for 30 minutes and so on. Default value is 3.

----------------
stop filter type
----------------

Sets the source of what is counted as an icing induced turbine stop when calculating icing events. Stop filter here refers to an extra filtering step that can be used to remove turbine stops from the data if there is status code information that indicates that the turbine was stopped for reasons other than icing.
Can have three different values:

0. Power level based filter (default).  No extra filtering.
1. Status code stop. If the value of ``stop filter type`` is `1` filter out the bits where the status code in column set by ``status index`` is set to value defined by ``status code stop value``
2. Status code normal operational state. If the value of ``stop filter type`` is `2`, keep only the parts of data where ``status index`` is set to value defined by ``status code stop value``

In case `2` ``status code stop value`` refers to turbine normal state.


----------------
stop time filter
----------------

Time filter used in stop detection. This is also the number of consecutive samples. Default value 6.


----------------
statefilter type
----------------


sets the filtering rule used to filter the data according to the state variable set earlier. State filter has four options

1. inclusive: Default value, keep only the part of the data where the state variable matches the defined normal state
2. exclusive: remove all data where state variable matches the defined normal state
3. greater than: keep only lines of data where state filter value greater than or equal to the value set
4. less than: keep only values where ste filter value is less than or equal to the value set

The name ``normal state`` for the filtering variable can be misleading due to option 2 here.
In the :ref:`input-data-example` you could filter based on column 6 using option 1 setting the normal value to ``OK``.


------------------
power level filter
------------------

Filter limit to remove stoppages from data. A power multiplier, defaults to 0.01. Power level filtering is used in order to remove times when turbine is stopped from the data. Useful if for example no turbine state information is known. This is applied to data

---------------------
reference temperature
---------------------

Initial reference data set is created by filtering out all measurements where temperature is below this limit. Defaults to 3 degrees Celsius.


------------------
temperature filter
------------------

Temperature limit for ice detection. If production is below the limit set in ``power drop limit`` **and** temperature is below the value set here,  events are classified as icing. Default value is 1.

----------
icing time
----------

Minimum time needed to trigger an icing event. If production is below the designated level for at least the **number of samples** defined here and temperature is below the limit set with ``temperature filter``, an icing alarm is triggered.

----------------
stop time filter
----------------

When calculating stops from production, the production needs to be below the value defined in ``stop limit multiplier`` for at least the **number of samples** defined here in order to declare the samples as an icing induced stop. Default value is 3.


---------------------
stop limit multiplier
---------------------

Multiplier to define the lower limit for power. If output power is below this times nominal power the turbines is determined to have stopped. Defaults to 0.005


------------
min bin size
------------

Minimum sample count in a single bin when creating power curves. Defaults to 36.


---------------
distance filter
---------------

set this to ``True`` to add an additional filtering step to power curve calculation. This can improve results in most cases, on by default. Can be removed by setting ``distance filter = False``

----------
start time
----------

If you want to calculate icing events and their losses to a period other than the whole data set, you can specify a different start time for your analysis. This uses same formatting that is specified in Section: Source file under :ref:`datetime-format`.

If you want to use the data set from the beginning write ``NONE`` here in all caps. Set to ``NONE`` by default.

---------
stop time
---------

If you want to calculate icing events and their losses to a period other than the whole data set, you can specify a different stop time for your analysis. This uses same formatting that is specified in Section: Source file under :ref:`datetime-format`.

If you want to use the data set till the end write ``NONE`` here in all caps. Set to ``NONE`` by default.

================
Mandatory values
================

The following values need to be set for every dataset.

* Section: Source file:

  * id
  * filename
  * fault columns

* Section: Data Structure:

  * timestamp index
  * wind speed index
  * wind direction index
  * temperature index
  * power index
  * rated power
  * state index
  * normal state
  * site elevation
  * status index
  * status code stop value



==============
Default values
==============

Set defaults are listed below:

* Section 'Source file':

  * delimiter: ','
  * quotechar: 'NONE'
  * datetime format: '%Y-%m-%d %H:%M:%S'
  * datetime extra char: '0'
  * replace fault codes': 'False'

* Section 'Output':

  * result directory: '.'
  * summary: 'True',
  * plot: 'True',
  * alarm time series: 'True',
  * filtered raw data: 'True',
  * icing events: 'True'
  * power curve: 'True'

* Section 'Binning':

  * minimum wind speed: '0',
  * maximum wind speed: '20',
  * wind speed bin size: '1',
  * wind direction bin size: '360'

* Section: 'Filtering':

  * power drop limit: '10',
  * overproduction limit: '90',
  * power level filter: '0.01',
  * temperature filter: '1',
  * reference temperature: '3',
  * icing time: '3',
  * stop filter type: '0',
  * stop limit multiplier: '0.005',
  * stop time filter: '6',
  * statefilter type: '1',
  * min bin size: '36',
  * distance filter: 'True',
  * start time: 'None',
  * stop time: 'None'




******************
Wind park analysis
******************

The script by itself only operates on one time series (one turbine) at a time. If you are dealing with a data set that contains more than one turbine, using this scrip requires that you write a separate .ini file for each turbine. After this it is possible to write a small script or a batch file that runs the script for each turbine separately. One such example is included in the release .zip as ``multifile_t19_example.py`` 

This script also combines the summary files into one for easier comparison between the turbines.


