import os, sys
from imp import reload

path = '/Users/kiki/Dropbox/skeletal_studios/clients/tangent/tools/crowd/dev/'
if not path in sys.path:
	sys.path.insert( 0, path )

import bpy

from crowd_tools import cache_sculpt
reload( cache_sculpt )

ob = bpy.context.scene.objects['GEO-vincent_body']

cache_sculpt.clear_shape_keys( ob )

export_path = '/Users/kiki/Dropbox/skeletal_studios/clients/tangent/tools/crowd/data/body'
cache_sculpt.bake_to_shape_keys( ob, export_path=export_path )
