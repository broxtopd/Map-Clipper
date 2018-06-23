# Takes an input raster and either creates an output raster that shows the extent 
# of a shapefile as a raster mask (eithe burn a single value, or burn multiple 
# values corresponding to a shapefile attribute), or make areas outside or inside 
# of a shape feature into NaNs or transparent
# USAGE: python clip_to_shape.py src clipsrc dst
# INPUTS: src - the raster to reproject
#         clipsrc - the shapefile used to burn the values
# OUTPUT: dst - the output raster
#
###############################################################################
# Copyright (c) 2018, Patrick Broxton
# 
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
# 
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
# 
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
###############################################################################

import sys,os
import glob
from osgeo import gdal,osr
from gdalconst import *
import subprocess
from osgeo import ogr

ot_list = ('', 'Byte','Int16','UInt16','Int32','UInt32','Float32','Float64','CInt16','CInt32','CFloat32','CFloat64')

# Optional parameters
def optparse_init():
    """Prepare the option parser for input (argv)"""

    from optparse import OptionParser, OptionGroup
    usage = 'Usage: %prog [options] input_file(s) [output]'
    p = OptionParser(usage)   
    p.add_option('-b', '--burn', dest='burn', default='',           # Burn a value into the a blank raster
                      help='Burn a value into a blank raster') 
    p.add_option('-t', '--attribute', dest='attribute', default='', # Burn a attribute value into a blank raster
                      help='Burn a attribute value into a blank raster')                         
    
    p.add_option('-n', '--dstnodata', dest='dstnodata', default='', # Make areas outside of a shapefile feature into nodata value (optionally specify nodatavalue)
                      help='# Make areas outside of a shapefile feature into nodata value')  
    p.add_option('-a', '--dstalpha', dest='dstalpha', action="store_true", default=False,   
                      help='Add alpha channel for cutline')         # Add alpha channel for cutline
    
    p.add_option('-c', '--crop_to_cutline', dest='crop_to_cutline', action="store_true", default=False,
                      help='Crop to shapefile extent')              # Crop the resulting raster to the shapefile's extent
    p.add_option('-i', '--invert', dest='invert', action="store_true", default=False,
                      help='invert to select areas outside of shapefile features')      # If specified, selects areas outside of shapefile features
    p.add_option('-w', '--where', dest='where', default='',
                      help='Where Statement')                       # Specify specific features in the shapefile to use
    p.add_option('-s', '--sql', dest='sql', default='', 
                      help='SQL Statement')                         # Do the same but with a SQL select statement
    p.add_option('-o', '--ot', dest='ot', default='', type='choice', choices=ot_list,
                    help='Output Type (%s)' % ','.join(ot_list))    # Specify the output data type of the resulting raster
    p.add_option('-v', '--overwrite', dest='overwrite', action='store_true', default=False, 
                    help='Overwrite existing files')                # Overwrite existing files without prompting
    return p
    
if __name__ == '__main__':

    # Parse the command line arguments      
    argv = gdal.GeneralCmdLineProcessor( sys.argv )
    parser = optparse_init()
    options,args = parser.parse_args(args=argv[1:])
    input_raster = args[0] 
    clipsrc = args[1]       
    output_raster = args[2]
    
    dstalpha = options.dstalpha
    dstnodata = options.dstnodata
    burn = options.burn
    attribute = options.attribute
    invert = options.invert
    crop_to_cutline = options.crop_to_cutline
    where = options.where
    sql = options.sql
    ot = options.ot
    overwrite = options.overwrite
    
    if os.path.exists(output_raster) and overwrite == False:
        (major,minor,micro,releaselevel,serial) = sys.version_info
        if major == 2:
            i = raw_input(output_raster + ' exists.  Do you want to continue (y/n)? ')
        elif major == 3:
            i = input(output_raster + ' exists.  Do you want to continue (y/n)? ')
        if i.lower() != 'y':
            sys.exit()
    
    init_value = '0'
    # If using a subset of shapefile features, make a temporary shapefile with the specified features
    if where != '' or sql != '':
        args = ''
        if where != '':
            args += ' -where "' + where + '"'
        if sql != '':
            args += ' -sql "' + sql + '"'
        cmd = 'ogr2ogr' + args + ' tmp_selectedfeatures.shp "' + clipsrc + '"'
        subprocess.call(cmd, shell=True) 
        clipsrc = 'tmp_selectedfeatures.shp'
    
    # Test if there is a problem opening the input data
    ds = gdal.Open(input_raster, GA_ReadOnly)
    if ds is None:
        print('Could not open ' + input_raster)
        sys.exit(1) 
    shape = ogr.Open(clipsrc)
    if shape is None:
        print('Could not open ' + clipsrc)
        sys.exit(1) 

    # Get the georeferencing information
    transform = ds.GetGeoTransform()
    wkt = ds.GetProjection()
    rows = ds.RasterYSize
    cols = ds.RasterXSize
    ulx = transform[0]
    uly = transform[3]
    pixelWidth = transform[1]
    pixelHeight = transform[5]
    lrx = ulx + (cols * pixelWidth)
    lry = uly + (rows * pixelHeight)
    
    # If specified, adjusting the bounding box to the extent of the shapefile features
    if crop_to_cutline:
        layer = shape.GetLayer()
        ulx_orig = ulx
        lrx_orig = lrx
        lry_orig = lry
       	uly_orig = uly
        ulx = 180
        uly = -90
        lrx = -180
        lry = 90
        for i in range(layer.GetFeatureCount()):
            feature = layer.GetFeature(i)
            geom = feature.GetGeometryRef()
            srs = geom.GetSpatialReference()
            wkt = srs.ExportToWkt()
            (ulx2, lrx2, lry2, uly2) = geom.GetEnvelope()
            ulx = min(ulx,ulx2)
            lrx = max(lrx,lrx2)
            lry = min(lry,lry2)
            uly = max(uly,uly2)

        ulx = max(ulx,ulx_orig)
        lrx = min(lrx,lrx_orig)
        lry = max(lry,lry_orig)
        uly = min(uly,uly_orig)

    # If inverting the shapefile features (selecting areas outside of the shape), 
    # Make a new shapefile with inverted polygon features
    if invert:
        # Create the polygon covering the raster/shapefile extent
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(ulx, uly)
        ring.AddPoint(lrx, uly)
        ring.AddPoint(lrx, lry)
        ring.AddPoint(ulx, lry)
        ring.AddPoint(ulx, uly)
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
    
        # Take the symetrical difference between the extent shapefile and the clip shapefile
        shape = ogr.Open(clipsrc)
        layer = shape.GetLayer()
        feature = layer.GetFeature(0)
        geom = feature.GetGeometryRef()
        while feature:
            newgeom = feature.GetGeometryRef()
            geom = geom.Union(newgeom)
            feature = layer.GetNextFeature() 
        
        simdiff = geom.SymmetricDifference(poly)
        shape.Destroy()

        # create a new shapefile
        driver = ogr.GetDriverByName("ESRI Shapefile")
        data_source = driver.CreateDataSource("tmp_symdiff.shp")
        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt)
        layer = data_source.CreateLayer("result",srs, ogr.wkbPolygon)
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(simdiff)
        layer.CreateFeature(feature)
        data_source.Destroy()
        
        clipsrc = "tmp_symdiff.shp"
    
    te = str(ulx) + ' ' + str(lry) + ' ' + str(lrx) + ' ' + str(uly)
    tr = str(pixelWidth) + ' ' + str(pixelHeight)

    # If burning a single value or an attribute value into a blank raster
    if burn != '' or attribute != '':
        args = ''
        if burn != '':
            args += ' -burn "' + burn + '"'
        if attribute != '':
            args += ' -a "' + attribute + '"'
            
        if where != '':
            args += ' -where "' + where + '"'
        if sql != '':
            args += ' -sql "' + sql + '"'
        if ot != '':
            args += ' -ot ' + ot
            
        cmd = 'gdal_rasterize' + args + ' -init ' + init_value + ' -te ' + te + ' -tr ' + str(pixelWidth) + ' ' + str(pixelHeight) + ' "' + clipsrc + '" "' + output_raster + '"'
        subprocess.call(cmd, shell=True) 
        src = 'tmp_raster.tif'

    # Else if setting data outside of features as nodata or transparent
    else:
        args = ''
        if dstalpha is True:
            args += ' -dstalpha'
        if dstnodata != '':
            args += ' -dstnodata "' + dstnodata + '"'
            
        if where != '':
            args += ' -cwhere ' + where + '"'
        if sql != '':
            args += ' -csql ' + sql + '"'
        if ot != '':
            args += ' -ot ' + ot + '"'

        cmd = 'gdalwarp --config GDALWARP_IGNORE_BAD_CUTLINE YES  -te ' + te + ' -tr ' + tr + ' ' + args + ' -cutline "' + clipsrc + '" -multi -overwrite "' + input_raster + '" "' + output_raster + '"'
        subprocess.call(cmd, shell=True) 

    # Remove temporary files
    if invert:
        for f in glob.glob('tmp_symdiff.*'):
            os.remove(f)   
    if where != '' or sql != '':
        for f in glob.glob('tmp_selectedfeatures.*'):
            os.remove(f)