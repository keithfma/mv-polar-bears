#!/bin/bash 
# 
# Update the data sheet and website, then publish to the web
# #

source /home/keith/venv/mv-polar-bears/bin/activate
cd /home/keith/prj/mv-polar-bears
branch_name=`git rev-parse --abbrev-ref HEAD`
git checkout master
python mvpb_data.py /home/keith/.mv-polar-bears/google_secret.json /home/keith/.mv-polar-bears/darksky_secret.json --log_level info
python mvpb_site.py /home/keith/.mv-polar-bears/google_secret.json /home/keith/.mv-polar-bears/darksky_secret.json --log_level info
git add docs/index.html docs/style.css
git commit -m "Automatic update"
git push
git checkout $branch_name
