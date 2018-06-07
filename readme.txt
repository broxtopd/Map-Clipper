# Map clipping tools for cutting maps using rasters or shapefiles.  
# Caution: These scripts automatically overwrite existing files
# Created by Patrick Broxton (broxtopd@gmail.com)
# Updated 2/2018

These functions require that GDAL and a python distribution with GDAL bindings are installed.  

# clip_to_raster.py
# Clips a selected input raster to have the exact same projection, extent, and resolution as another
# USAGE: python clip_to_raster.py src clipsrc dst
# INPUTS: src - the raster to reproject
#         clipsrc - the raster to match
# OUTPUT: dst - the output file
# Important: If the pixels in src and clipsrc do not line up exactly, the pixels in SRS will be resampled
# To preserve the extents, even if they have the exact same resolution
# Available Options:
# -r or --resample.............Specify resampling method
# -t or --tr...................Override output map resolution    
# -s or --ts...................Override output map size
# -d or --dstnodata.............Add nodata value
# -v or --overwrite.............Overwrite existing file without prompt

# clip_to_shape.py
# Takes an input raster and either creates an output raster that shows the extent 
# of a shapefile as a raster mask (eithe burn a single value, or burn multiple 
# values corresponding to a shapefile attribute), or make areas outside or inside 
# of a shape feature into NaNs or transparent
# USAGE: python clip_to_shape.py src clipsrc dst
# INPUTS: src - the raster to reproject
#         clipsrc - the shapefile used to burn the values
# OUTPUT: dst - the output raster
# Available options
# -b or --burn........................Burn a value into the a blank raster
# -t or --attribute <attribute_name>..Burn a attribute value into a blank raster
# -n or --dstnodata...................Make areas outside of a shapefile feature into nodata value (optionally specify nodatavalue)
# -a or --dstalpha....................Add alpha channel for cutline
# -c or --crop_to_cutline.............Crop the resulting raster to the shapefile's extent
# -i or --invert......................If specified, selects areas outside of shapefile features (instead of inside)
# -w or --where.......................Specify specific features in the shapefile to use
# -s or --sql.........................Do the same but with a SQL select statement
# -o or --ot..........................Specify the output data type of the resulting raster
# -v or --overwrite...................Overwrite existing file without prompt

# Examples:

# Clip Hillshade.tif to the match the extent and resolution of Geology.tif
python clip_to_raster.py DEMO/Hillshade.tif DEMO/Geology.tif Hillshade_sub.tif

# Clip Geology.tif with Boundary.shp such that the bounds are determined by the shapefile boundaries and 
# everything outside of a shape feature is transparent
python clip_to_shape.py --dstalpha --crop_to_cutline DEMO/Geology.tif DEMO/Boundary.shp Geology_clip.tif

# Clip Hillshade.tif with Boundary.shp such that the bounds are determined by the shapefile boundaries and 
# everything outside of a shape feature is nodata
python clip_to_shape.py --dstnodata --crop_to_cutline DEMO/Hillshade.tif DEMO/Boundary.shp Hillshade_clip.tif

# Create a mask (whose grid matches Geology.tif) with 1's inside of the features in Boundary.shp and 0's elsewhere
python clip_to_shape.py --burn 1 DEMO/Geology.tif DEMO/Boundary.shp Mask.tif
