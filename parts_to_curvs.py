import bpy
import pprint
from itertools import islice

scene = bpy.context.scene


def take(n, iterable):
	"Return first n items of the iterable as a list"
	return list(islice(iterable, n))

def save(obj):
	settings = {}
	particle_systems = obj.particle_systems
	for ps in particle_systems:
		settings[ps] = (ps.settings.effector_weights.curve_guide, ps.settings.child_type)

	return settings

def set(settings):
	for ps, attrs in settings.items():
		curve_guide_val, child_type_val = settings[ps]

		ps.settings.effector_weights.curve_guide = curve_guide_val
		ps.settings.child_type = child_type_val

def apply_force(objs):
	for ob in objs:
		bpy.context.scene.objects.active = ob
		bpy.ops.object.forcefield_toggle()
		bpy.context.object.field.type = 'GUIDE'
		bpy.context.object.field.use_max_distance = True
		bpy.context.object.field.guide_minimum = 0.05
		bpy.context.object.field.distance_max = 0.15
		bpy.context.object.data.use_path = True
		bpy.context.object.field.falloff_power = 0
		bpy.context.object.field.guide_free = 0
		bpy.context.object.field.guide_clump_amount = .6


def find_modifier(ob, ps_name):
	for modifier in ob.modifiers:
		if modifier.type == 'PARTICLE_SYSTEM':
			if modifier.particle_system.name == ps_name:
				return modifier

#obj = bpy.context.selected_objects[0]
obj = bpy.context.active_object
restore = save(obj)

for ps, settings in restore.items(): #take(5, restore.items()):
	modifier = find_modifier(obj, ps.name)

	if not modifier.show_viewport:
		print('skipping %s' % ps.name)
		continue

	print( '+ Processing "{}"...'.format(ps.name) )

	cur_settings = { ps:(0.0, 'NONE') }
	set( cur_settings )

	prt, *rest = ps.name.split('.')
	crv_name = '.'.join(['crv', *rest])
	nul_name = '.'.join(['nul', *rest])
	grp_name = '.'.join(['grp', *rest])


	## bugfix: turn of bspline before the conversion
	use_hair_bspline = ps.settings.use_hair_bspline
	ps.settings.use_hair_bspline = False
	if use_hair_bspline:
		print( "+ Disabling bspline..." )

	bpy.context.scene.objects.active = obj
	scene.update()
	

	# create the curve
	bpy.ops.object.modifier_convert(modifier=modifier.name)
	new_obj = bpy.context.active_object
	new_obj.name = crv_name
	new_obj.data.name = crv_name

	# create the empty
	bpy.ops.object.empty_add(type='PLAIN_AXES')
	empty_obj = bpy.context.active_object
	empty_obj.name = nul_name

	new_obj.parent = empty_obj
	empty_obj.select = False
	new_obj.select = True
	bpy.context.scene.objects.active = new_obj

	bpy.ops.object.mode_set(mode='EDIT')
	bpy.ops.mesh.separate(type="LOOSE")
	bpy.ops.object.mode_set(mode='OBJECT')
	bpy.ops.object.convert(target='CURVE')

	apply_force(bpy.context.selected_objects)
	empty_obj.select = True
	bpy.context.scene.objects.active = empty_obj
	bpy.ops.group.create(name=grp_name)

	restore_settings = {ps:restore[ps]}
	set(restore_settings)

	## bugfix: re-enable bspline if it was disabled during the conversion
	ps.settings.use_hair_bspline = use_hair_bspline

	modifier.particle_system.settings.effector_weights.group = bpy.data.groups[grp_name]

	scene.update()
