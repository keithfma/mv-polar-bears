# Martha's Vineyard Polar Bears Data Analysis & Visualization

Exploration of attendence data from the MV Polar Bears group.

The attendence data is hosted as a Google Sheet at https://drive.google.com/open?id=16i007HPiYsQKEZyrYn3KAIrSgf_ZPg63mdJh9uplH4 .
The sheet is publically readable but only editable to a select few. 

This repo generates two products:

1. A blog post, created once and hosted at http://www.allnans.com/jekyll/update/2018/07/19/mv-polar-bears.html
1. A dashboard, refreshed regularly and hosted at https://mvpolarbears.allnans.com

To update the dashboard site, run `mvpb_data.py` to refresh the data, and
`mvpd_site.py` to regenerate the site. Both have command-line options
accessible with the `--help` flag.

The dashboard can also be added to a Facebook Page as a a "Page Tab". To do
this, simply visit the URL below, and select the page you wish to add it to. 

https://www.facebook.com/dialog/pagetab?app_id=1885448688215245&redirect_uri=https://mvpolarbears.allnans.com

Note that this only works for organizational pages, for some crazy reason you
cannot add a tab to a personal page. 


