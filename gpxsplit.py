#!/usr/bin/env python2.7
"""
Usage:
   gpxsplit.py [options] <input-file> <output-file>

Options:
    -b --batch=SIZE              Batch size [default: 500]
    -l --layer=LAYER             Input layer [default: tracks]
    -h --help                    Show Help
"""
import docopt

from osgeo import gdal
from osgeo import osr
from osgeo import ogr

def batch(iterable, batch_size=1):
    iterable_length = len(iterable)
    for n in xrange(0, iterable_length, batch_size):
        yield iterable[n:min(n + batch_size, iterable_length)]


def gpx_track(outLayer, name, points):
    # create geometry from points
    geometry = ogr.Geometry(ogr.wkbLineString)
    for p in points:
        geometry.AddPoint(*p)

    # create feature
    feature = ogr.Feature(outLayer.GetLayerDefn())
    feature.SetField('name', name)
    feature.SetGeometry(geometry)
    outLayer.CreateFeature(feature)
    feature.Destroy()

    print "Split track %s (%d points)" % (name, len(points))


def gpx_split(in_file, out_file, layer, batch_size):
    # enable exceptions
    gdal.UseExceptions()

    # open output file
    outDriver = ogr.GetDriverByName('GPX')
    outSource = outDriver.CreateDataSource(out_file)
    if outSource is None:
        raise Exception("Unable to open: %s" % out_file)

    outSRS = osr.SpatialReference()
    outSRS.ImportFromEPSG(4326)

    outLayer = outSource.CreateLayer("tracks", outSRS, ogr.wkbMultiLineString)
    outLayerNameField = ogr.FieldDefn('name', ogr.OFTString)
    outLayerNameField.SetWidth(64)
    outLayer.CreateField(outLayerNameField)

    # open input file
    inDriver = ogr.GetDriverByName('GPX')
    inSource = inDriver.Open(in_file)
    if inSource is None:
        raise Exception("Unable to open: %s" % in_file)

    # read input layer
    inLayer = inSource.GetLayer(layer)
    inLayerDef = inLayer.GetLayerDefn()
    for feature in inLayer:
        track_geometry = feature.GetGeometryRef()
        fields = {inLayerDef.GetFieldDefn(i).GetName(): feature.GetField(i) for i in range(inLayerDef.GetFieldCount())}
        if track_geometry is None:
            continue

        track_name = fields['name']

        # read track segments
        for s in range(track_geometry.GetGeometryCount()):
            segment_geometry = track_geometry.GetGeometryRef(s)
            segment_points = segment_geometry.GetPoints()

            # batch track segments
            for k, batched_points in enumerate(batch(segment_points, batch_size)):
                batched_name = '%s (%d)' % (track_name, s+k)

                # write batched track
                gpx_track(outLayer, batched_name, batched_points)

    # close files
    inSource.Destroy()
    outSource.Destroy()


if __name__ == '__main__':
    options = docopt.docopt(__doc__, version=0.1)

    gpx_split(options['<input-file>'],
              options['<output-file>'],
              layer=options['--layer'],
              batch_size=int(options['--batch']))
