---
layout: post
title:  "MV Polar Bears Attendence Data Exploration and Forecasting"
date:   2018-07-19 10:20:24 -0400
categories: jekyll update
published: true 
---

For the past several years, the wonderful MV Polar Bears group has recorded how
many people attend each day. This post provides some basic visualizations of
the dataset and an attempt to build a predicitive model to forecast the
expected number of attendees. My big takeaways were:

1. The MV Polar Bears are reaching an amazing number of people - wow!
1. The bears are *very* unpredictable.

## Attendence Over Time

The next plot shows the number of new and returning attendees over the
past few years. There is a clear annual pattern, and always more old
friends than new ones.

{{ daily_bar_div | safe }}

Polar bears are slowly creeping towards work domination! The plot below
shows the cumulative number of attendees (blue) and new polar bear
members (green) over time. The numbers are big and growing.

{{ cumul_div | safe }}

## What Drives Attendence?

Two features are related if knowing the value of one feature tells you
something about the other. For example, the new and returning attendence
number are closely correlated -- when the group is bigger there are more
"newbies". Temperature and attendence show a different relation. Polar
bears don't sweat cold weather up to a point, and then attendence falls
off a cliff. Take a look and see what else you can find.

{% for scatter_div in scatter_divs %}
{{ scatter_div | safe }}
{% endfor %}

## Forecast Model

Polar bears are hard to predict! You may notice from the plots above that
attendence varies wildly from day-to-day, and the magnitude of this
variation changes over time as well. These features make make building a
predictor tricky. Moreover, I had hoped that the weather and water
conditions might help to predict attendence, but it seems that Polar
Bears aren'y much bothered by cold, wind, or rain. 
      
After a bit of experimentation, I landed on a timeseries forecasting
model that predicts changes in the mean and volitility (specifically a
GARCH model with an ARX mean). The plot below shows retrospecitve
predictions for the attendence dataset (top), as well as the prediction
errors (bottom).

You may notice that the prediction is often *really* wrong. Like I
said, it is hard to predict polar bears! The volitility prediction works
better -- the true number is usually within the (1-sigma) margin of
error. 

{{ forecast_div | safe }}

<link href="https://cdn.pydata.org/bokeh/release/bokeh-0.12.15.min.css" rel="stylesheet" type="text/css">
<link href="https://cdn.pydata.org/bokeh/release/bokeh-widgets-0.12.15.min.css" rel="stylesheet" type="text/css">
<link href="https://cdn.pydata.org/bokeh/release/bokeh-tables-0.12.15.min.css" rel="stylesheet" type="text/css">

<script src="https://cdn.pydata.org/bokeh/release/bokeh-0.12.15.min.js"></script>
<script src="https://cdn.pydata.org/bokeh/release/bokeh-widgets-0.12.15.min.js"></script>
<script src="https://cdn.pydata.org/bokeh/release/bokeh-tables-0.12.15.min.js"></script>

{{ recent_bar_script | safe }}
{{ daily_bar_script | safe }}
{{ cumul_script | safe }}
{% for scatter_script in scatter_scripts %}
{{ scatter_script | safe }}
{% endfor %}
{{ forecast_script | safe }}
