# Working notes for MV Polar Bears project

## Gathering weather data for predictor

It seems to me a few variables may be of interest to people deciding if they
will attend polar bears on a given day:

1. Air temperature
2. Cloud cover
3. Precipitation
4. Water temperature
5. Wave height
6. Wind speed
7. Wind direction

For all of these, both the observed and the predicted values may have an
impact. Ideally, I would like to collect observed at the time of the event
(which is?) and predicted the night before and the morning of (just prior). It
may also be useful to include the previous day observed values in the
predictor.

For historical, I can get forecast data from the Dark Sky API, and observed
(probably) from NOAA or similar.

To drive a live predictor, I will need to collect predictions, etc, at the
right times.
