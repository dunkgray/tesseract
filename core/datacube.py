import numpy as np
from collections import OrderedDict, namedtuple
from tile import Tile
from utils import get_geo_dim
# import only for test plotting
#from matplotlib.ticker import LinearLocator, FormatStrFormatter
import matplotlib.pyplot as plt
#from matplotlib import cm
from mpl_toolkits.mplot3d.axes3d import Axes3D

TileID = namedtuple('TileID', ['prod', 'lat_start', 'lat_extent', 'lon_start', 'lon_extent', 'pixel_size', 'time'])

def load_data(prod, min_lat, max_lat, min_lon, max_lon):

    import pymongo
    from pymongo import Connection

    conn = Connection('128.199.74.80', 27017)
    db = conn["datacube"]

    cursor = db.index2.find({"product": prod, "lat_start": {"$gte": min_lat, "$lte": max_lat}, "lon_start": {"$gte": min_lon, "$lte": max_lon}})
    arrays = {}
    for item in cursor:
        arrays[TileID(item[u'product'], item[u'lat_start'], item[u'lat_start']+item[u'lat_extent'], item[u'lon_start'],
                      item[u'lon_start']+item[u'lon_extent'], item[u'pixel_size'], np.datetime64(item[u'time']))] = \
            Tile(item[u'lat_start'], item[u'lat_extent'], item[u'lon_start'], item[u'lon_extent'], item[u'pixel_size'],
                 bands= 6, array=None)

    return DataCube(arrays)

 
class DataCube(object):
    
    def __init__(self, arrays={}):
        self._dims = None 
        self._arrays = arrays
        self._attrs = None
        self._dims_init()

    def _dims_init(self):
        dims = OrderedDict()
        tile_ids = self._arrays.keys()

        products = np.unique(np.sort(np.array([tile_id.prod for tile_id in tile_ids])))
        dims["product"] = products

        max_pixel = max([tile_id.pixel_size for tile_id in tile_ids])
        
        min_lat = min([tile_id.lat_start for tile_id in tile_ids])
        max_lat = max([tile_id.lat_start+tile_id.lat_extent for tile_id in tile_ids])
        latitudes = get_geo_dim(min_lat, max_lat-min_lat, max_pixel)
        dims["latitude"] = latitudes
        
        min_lon = min([tile_id.lon_start for tile_id in tile_ids])
        max_lon = max([tile_id.lon_start+tile_id.lon_extent for tile_id in tile_ids])
        longitudes = get_geo_dim(min_lon, max_lon-min_lon, max_pixel)
        dims["longitude"] = longitudes
       
        times = np.unique(np.sort(np.array([tile_id.time for tile_id in tile_ids])))
        dims["time"] = times
        
        self._dims = dims        

    def __getitem__(self, index):
        if len(index) == 4:
            new_arrays = {}
            for key, value in self._arrays.iteritems():
                # First check if within bounds
                #prod_bounds = key.prod in index[0]
                prod_bounds = True
                lat_bounds = key.lat_start <= index[1].start <= key.lat_start+key.lat_extent or key.lat_start <= index[1].stop <= key.lat_start+key.lat_extent
                lon_bounds = key.lon_start <= index[2].start <= key.lon_start+key.lon_extent or key.lon_start <= index[2].stop <= key.lon_start+key.lon_extent                
                #time_bounds = index[3].start <= key.time <= key.lon_end
                time_bounds = True
                
                bounds = (prod_bounds, lat_bounds, lon_bounds, time_bounds)
                if bounds.count(True) == len(bounds):

                    lat_start = max(key.lat_start, index[1].start)
                    lat_end = min(key.lat_start+key.lat_extent, index[1].stop)

                    lon_start = max(key.lon_start, index[2].start)
                    lon_end = min(key.lon_start+key.lon_extent, index[2].stop)

                    """
                    tile_lat_dim = np.arange(key.lat_start, key.lat_start+key.lat_extent, key.pixel_size)
                    lat_i1 = np.abs(tile_lat_dim - index[1].start).argmin()
                    lat_i2 = np.abs(tile_lat_dim - index[1].stop).argmin()
                    
                    tile_lon_dim = np.arange(key.lon_start, key.lon_start+key.lon_extent, key.pixel_size)
                    lon_i1 = np.abs(tile_lon_dim - index[2].start).argmin()
                    lon_i2 = np.abs(tile_lon_dim - index[2].stop).argmin()
                    """
                        
                    new_arrays[TileID(key.prod, lat_start, lat_end-lat_start, lon_start, lon_end-lon_start, key.pixel_size, key.time)] = value[lat_start:lat_end, lon_start:lon_end]
            
            return DataCube(new_arrays)
                
                    
    """    
    if type(index) is tuple and len(index) == 4:
        new_index = (index[0], _translate_index(index, 2), _translate_index(index, 3), index[4])
    """   
            
    """
    def _translate_index(self, index, pos):
        if pos == 1:
            if type(index[pos]) is slice:
                start = np.abs(self._dims["latitude"]-index.start).argmin()               
                stop = np.abs(self._dims["latitude"]-index.stop).argmin()
                print start, stop 
                return slice(start, stop)
        
            elif isinstance(index[pos], int) or isinstance(index[pos], float):
                print np.abs(self._dims["latitude"]-index).argmin()               
                return np.abs(self._dims["latitude"]-index).argmin()               
        
        elif pos == 2:
            if type(index) is slice:
                start = np.abs(self._dims["longitude"]-index.start).argmin()               
                stop = np.abs(self._dims["longitude"]-index.stop).argmin()               
                return slice(start, stop)
            
        elif isinstance(index[pos], int) or isinstance(index[pos], float):
                print np.abs(self._dims["longitude"]-index).argmin()               
                return np.abs(self._dims["longitude"]-index).argmin()               
    """
    
    @property
    def shape(self):
        """Mapping from dimension names to lengths.
        This dictionary cannot be modified directly, but is updated when adding
        new variables.
        """
        return "({}, {}, {}, {})".format(self._dims["product"].shape[0], self._dims["latitude"].shape[0],
                                         self._dims["longitude"].shape[0], self._dims["time"].shape[0])

    @property
    def dims(self):
        """Mapping from dimension names to lengths.
        This dictionary cannot be modified directly, but is updated when adding
        new variables.
        """
        return self._dims


    def plot_datacube(self):
        fig = plt.figure()
        ax = fig.gca(projection='3d')

        times_conv = {}
        min_time = np.inf
        max_time = -np.inf
        for key, value in self._arrays.iteritems():
            times_conv[key.time] = np.float32(key.time)
            if np.float32(key.time) < min_time:
                min_time = np.float32(key.time)
            if np.float32(key.time) > max_time:
                max_time = np.float32(key.time)

        for key, value in self._arrays.iteritems():
            times_conv[key.time] = times_conv[key.time] - min_time

        min_z = np.inf
        max_z = -np.inf
        for key, value in self._arrays.iteritems():
            lons = get_geo_dim(key.lon_start, key.lon_extent, key.pixel_size)
            lats = get_geo_dim(key.lat_start, key.lat_extent, key.pixel_size)
            x, y = np.meshgrid(lons, lats)
            z = times_conv[key.time]
            surf = ax.plot_wireframe(x, y, z, rstride=1, cstride=1)

            if z < min_z:
                min_z = z
            if z > max_z:
                max_z = z

        ax.set_zlim(min_z-1.0, max_z+1.0)

        #ax.zaxis.set_major_locator(LinearLocator(10))
        #ax.zaxis.set_major_formatter(FormatStrFormatter('%.02f'))


        return plt


    """
    def add_tile(self, tile):
        
        self.data[(tile.prod, tile.lat, tile.lon, tile.time)] = tile
        
        if self.x_span is None:
            self.x_span = np.arange(tile.lon, tile.lon+1, 1/tile.x_span)
        else:
            self.x_span = np.arange(min(self.x_span, tile.lon), max(self.x_span, tile.lon+1), 1/tile.x_span)
        
        if self.y_span is None:
            self.y_span = np.arange(tile.lat, tile.lat+1, 1/tile.y_span)
        else:
            self.y_span = np.arange(min(self.y_span, tile.lat), max(self.y_span, tile.lat+1), 1/tile.y_span)
            
        self.time_span.append(tile.time).sort()
    """
            
    
if __name__ == "__main__":

    arrays = {}
    arrays[TileID("NBAR", 43.0, 1.0, 112.0, 1.0, 0.0025, np.datetime64('2007-07-13T03:45:23.475923Z'))] = Tile(43.0, 1.0, 112.0, 1.0, 0.0025, 6, np.random.randint(255, size=(4000, 4000, 6)))
    arrays[TileID("NBAR", 44.0, 1.0, 112.0, 1.0, 0.0025, np.datetime64('2006-01-13T23:28:19.489248Z'))] = Tile(44.0, 1.0, 112.0, 1.0, 0.0025, 6, np.random.randint(255, size=(4000, 4000, 6)))
    arrays[TileID("PQA", 43.0, 1.0, 112.0, 1.0, 0.0025, np.datetime64('2010-08-13T04:56:37.452752Z'))] = Tile(43.0, 1.0, 112.0, 1.0, 0.0025, 6, np.random.randint(255, size=(4000, 4000, 6)))
        
    dc = DataCube(arrays)
    print dc.shape
    dc = dc["", 43.0:44.0, 112.0:113.0, 4]
    print dc.shape
    dc.plot_datacube()
    dc = dc["", 43.5:44.0, 112.6:112.8, 4]
    print dc.shape
    #
    #print dc["", 2, 4, 4]
    #print dc.dims["product"]
    #print dc.dims["time"]

    #dc = load_data("NBAR", -35, -33, 125, 127)
    #print dc.shape
