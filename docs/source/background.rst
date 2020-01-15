#######################
Task 19 Ice Loss Method
#######################

===========
Description
===========

This document describes a method to assess production losses due to icing based on standard SCADA data available from modern wind turbines. An open source Python code will be publically available based on the method presented in this guideline document. This method is formulated by `IEA Task 19 <https://community.ieawind.org/task19/home>`_ , an international expert group with an aim to increase and disseminate knowledge and information about cold climate wind energy related issues. Task 19 aims to contribute in lowering the costs and reducing the risks of wind energy deployment in cold climates.

==========
Motivation
==========


Currently production losses due to wind turbine rotor icing are calculated with different methods all resulting to different results. Task 19 has three main reasons on why a standardized production loss calculation method is needed:

1. There is a large need to compare different sites with each other with a systematic analysis method
2. To validate the IEA Ice Classification
3. Evaluate effectiveness of various blade heating systems

Current production loss methods usually use a constant -15% or -25% clean power curve drop as an indication of icing. Similarly standard deviation (or multiples of it) has been widely used to define iced turbine production losses. Both of these methods result to different results and are not necessarily representing the actual ice build-up and removal process to wind turbine blades reliably enough.

With the method described here, anyone with access to SCADA data from wind turbines can assess and calculate turbine specific production losses due to icing. The method uses existing standards and is developed in order to minimize the uncertainties related to production loss estimations from SCADA data. The method does not require icing measurements as input.

======
Method
======

Task 19 proposes a method that is robust, easily adaptable, filters outliers automatically and does not assume a normal distribution of the SCADA data for individual turbines and wind farms. The proposed method uses percentiles of the reference, non-iced power curve in combination with temperature measurements. Ice build-up on turbine blades gradually deteriorates the power output (or results to overproduction to to iced anemometer) so for increased accuracy the method uses three consecutive 10-minute data points for defining start-stop timestamps for icing events. In other words, the turbine rotor is used as an ice detector. Iced turbine power losses are defined by comparing the performance to the calculated power curve using heated anemometers from nacelle and the measured reference, expected power curve. Production losses are separated into 2 categories: operation and standstill losses due to icing.

On a general level, the method can be divided into 3 main steps:

1. Calculate reference, non-iced power curve
2. Calculate start-stop timestamps for different icing event classes
3. Calculate production losses due to icing

Below is a minimal list of signals used to calculate the icing losses


+-----------+----------------------------+-------+----------------+
| Signal    |  Description               | Unit  |    Value       |
+===========+============================+=======+================+
| ws        | Hub height wind speed      |  m/s  | 10-minute mean |
+-----------+----------------------------+-------+----------------+
| temp      | Ambient temperature        |  °C   | 10-minute mean |
|           |  (hub height)              |       |                |
+-----------+----------------------------+-------+----------------+
| pwr mean  | Turbine output power       |  kW   | 10-minute mean |
+-----------+----------------------------+-------+----------------+
| mode      | Turbine operational mode   |       | 10-minute mean |
+-----------+----------------------------+-------+----------------+

=================================================
Step 1: Calculate reference, non-iced power curve
=================================================

This is the first and very important step in defining the production losses due to icing as one always needs to compare iced rotor performance to reference, non-iced operational values. All iced turbine production losses (operational or stand-still related) will be compared to what the turbine could produce during (and after) icing events.

Air density is to be corrected to hub height according to ISO 2533 by scaling the wind speed and air pressure by taking site elevation above sea level. As air pressure measurements are typically missing from turbine SCADA, a static pressure according to site elevation above sea level is calculated [#f2]_. Site air density and air pressure are used to calibrate the nacelle wind speed as follows:

.. math::

  w_{site} = w_{std} \times  \left ( \frac{\rho_{std}}{\rho_{site}} \right )^{\frac{1}{3}} = w_{std} \times \left ( \frac{\frac{P_{std}}{T_{std}}}{\frac{P_{site}}{T_{site}}} \right )^{\frac{1}{3}} \\
  w_{site} = w_{std} \times \left ( \frac{T_{std}}{T_{site}}(1-2.25577 \times 10^{-5} \times h)^{5.25588} \right )^{\frac{1}{3}}

where w\ :sub:`site` is calibrated nacelle wind speed, w\ :sub:`std` measured nacelle wind speed, T\ :sub:`site` is nacelle
temperature [#f3]_ and T\ :sub:`std` is standard temperature of 15°C (288.15 K) resulting to air density of 1.225
kg/m3 at sea level P\ :sub:`std` = 101325 Pa ambient air pressure, h is site elevation in meters above sea
level [#f4]_.

The IEC 61400-12-1 “Power performance measurements” is applicable for very detailed power production calculations using a standard met mast wind measurements as input. However, the method for production loss calculation using SCADA data only results to using nacelle top wind measurements which are disturbed by the rotating rotor. The nacelle anemometer is thus less accurate and simplified binning of the reference data is proposed. As a first step, reference turbine data needs to be temperature and air pressure corrected and filtered according to production mode [#f5]_ as follows:

* air density and static air pressure correction with nacelle temperature and site elevation
* power production operating states only AND temperature [#f6]_ > +3°C

For power curve calculation the data is binned according to wind speed and optionally according to wind direction as well. Usefulness of wind direction-based binning depends on the site geography and is not always necessary. A separate power curve is then calculated for each wind direction bin.

The power curve calculation results in several for each wind speed bin:

1. Median output power in the bin
2. Standard deviation of power in the bin
3. 10th percentile of power in the bin
4. 90th percentile of power in the bin
5. Power curve uncertainty in the bin defined as [standard deviation] / [power]
6. Sample count in the bin

Sample count can be used to determine the appropriate binning resolution, it is recommended to have at least 6 hours of data in a bin to get a representative result.

The code will also try to interpolate over empty bins or bins that have too few samples in them. In these cases a linear interpolation between two closest bins is used.



=========================================================================
Step 2: Calculate start-stop timestamps for different icing event classes
=========================================================================

Once the reference has been established, next the exact time periods when ice is present on the turbine rotor are needed. As only SCADA data is used as input to define icing events, special care needs to take place in order to minimize false icing event alarms. False iced rotor alarms are minimized by assuming that ice is affecting the rotor for 30 minutes or more consecutively at below 0°C temperatures. The required output power reduction (or over production) uses a certain percentile of the reference data. This enables a robust yet simple threshold.

In total, there are three different icing event classes detected from the SCADA data:

1: Decreased production ,icing event class a), shortly IEa
2: Standstill icing event class b), IEb
3: Iced up heated anemometer ws or overproduction icing event class c), IEc)

In addition to these, if blade heating system is available, the moments when blade heating is on can be categorized separately and if ice detector is available, icing events detected by the ice detector can be categorized separately.



--------------------
Icing event class a)
--------------------

The start of a typical reduced power output icing event class a) [IEa] for an operational turbine is
defined as follows:

    If temp is below 0°C AND power is below 10th percentile of the respective reference (non-iced) wind bin for 30 minutes or more, THEN icing event class a) starts

An icing event class a) ends as follows:

    If power is above 10th percentile of the respective reference wind bin for 30-min or more, THEN icing event class a) ends

In the output files icing event class a is referenced as `Production losses due to icing`

--------------------
Icing event class b)
--------------------

Icing can cause the turbine to shut-down and cause the turbine to standstill for a number of reasons.
Standstill due to icing caused by icing event class b) [IEb] begins as follows:

    If temp is below 0°C AND power is below 10th percentile of the respective reference wind bin for 10-min resulting to a shutdown (power < 0.5 % of rated power of the turbine for at least 20-min, THEN standstill due to icing starts

Icing event b) ends as follows:

    If power is above 10th percentile of the respective reference wind bin for 30-min or more, THEN icing event class b) ends

-------------------------------------------
Manual analysis of shut-downs in wintertime
-------------------------------------------

Sometimes the turbine controller shuts down the turbine due to safety reasons during iced turbine operation even before power P10-P90 thresholds are exceeded. Different turbine types react very differently to icing of the rotor during operation. Some turbine types are very sensitive to rotor icing and thus shut-down very quickly after icing influences the rotor. Other turbine models are extremely robust and are able to operate with iced blades for long periods even under severe icing conditions. Manual analysis of standstill losses is recommended because standstill losses are typically larger than operational losses and analysing operational losses only underestimates production losses due to icing.

Typical shut -down controller error messages report excess tower side-to-side vibrations or that the nacelle wind speed does not correspond to output power. This type of behaviour can be considered to be caused by icing and is to be manually added when summing up all production losses.

It is possible to define certain SCADA status codes to represent a stopped turbine and calculate the losses caused by these stops separately from all other production losses. This can be useful in some cases to understand the distribution of production losses into different categories.

--------------------
Icing event class c)
--------------------

The heated anemometer ws may sometimes be influenced by ice resulting to overproduction.
The start of an overproduction (iced up anemometer) icing event class c) [IEc] for an operational turbine
is as follows:

    If temp is below 0°C AND power is above 90th percentile of the respective reference wind bin for 30-min or more, THEN icing event class c) starts

Icing event class c) ends as follows:

    If power is below 90th percentile of the respective reference wind bin for 30-min or more, THEN icing event class c) ends

For IEa and IEb, the production losses can be defined. However, if the measured output power is above expected wind speed (ie overproducing) in IEc, there is reason to expect the anemometer is influenced by ice and for this case, the production losses cannot be defined unless accurate wind speed are available from another source. If the number of hours with IEc is large, the estimated total production losses can be considered as minimum losses because all icing influences cannot be assessed.

------------------------------------------------
Step 3: Calculate production losses due to icing
------------------------------------------------

Once the icing events have been identified the difference in power between the reference and actual measured output power will be calulated for each time step during the icing events. In addition to this a production losses in kWh and as a percentage of total ar calculated for ice event classes IEa and IEb. For overproduction (class IEc) only the total duration is documented.

The output of the method and the formatting of the results are described in the usage section of the documentation


.. [#f2] Alternatively, detailed weather model air pressure values can used. Of course if air pressure is measured, that is the preferred alternative
.. [#f3] Warning: Some nacelle temperature sensors have shown a constant bias of +2...3 °C due to radiation heat of nacelle. Investigating this bias is recommended (compare to met mast, weather models etc)
.. [#f4] Engineering ToolBox, (2003). Altitude above Sea Level and Air Pressure. [online] Available at: https://www.engineeringtoolbox.com/air-altitude-pressure-d_462.html
.. [#f5] Alternatively, if controller mode is not available or known, use following filter criterias: IF P\ :sub:`min` > 0.005  P\ :sub:`rated` AND P\ :sub:`mean` > 0.05  P\ :sub:`rated` THEN Power production mode = normal
.. [#f6] This temperature limit needs to be set high enough to assume that turbine is not influenced by icing at these temperatures

