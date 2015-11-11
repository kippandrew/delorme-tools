# delorme-tools


### Convert GPX File to GPX1.1

```bash
gpsbabel -t -r -w -i GPX -f <INPUT.GPX> -x validate,debug -o GPX,gpxver=1.1 -F <OUTPUT.GPX>
```

### Example PCT Import
```
find pct/ca_state_gps -name '*tracks.gpx' -print | cut -d. -f1 | xargs -I % python gpxsplit.py %.gpx %_split.gpx

python delorme.py import pct/ca_state_gps/*split.gpx
```

